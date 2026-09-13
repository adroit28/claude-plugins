#!/usr/bin/env python3
"""Render a YouTube Shorts thumbnail at exactly 1080x1920 (9:16).

Text-only, or text over a frame you supply (an image, or a video plus a
timestamp). Rendered with headless Chrome so emoji and fonts look like the
real thing, then verified with Pillow: exact size, under 2 MB, plus a
216x384 preview at channel-grid size so legibility can be checked.

Examples
  thumbnail.py --project-dir P --slug chelsea-hull --headline "CHELSEA DEFENDING|vs HULL" --sub "is a CRIME" --style roast --emoji "💀😭"
  thumbnail.py --project-dir P --slug yamal --headline "YAMAL|DANCE MOVES" --sub "should be ILLEGAL" --style hype --image frame.jpg
  thumbnail.py --project-dir P --slug kane --headline "KANE FROM 30 YARDS" --video clip.mp4 --at 12.5 --style hype
  thumbnail.py --project-dir P --slug me-sad --headline "ME AFTER|90 MINUTES" --photo me.jpg --photo-shape cutout --style sad

Use | in --headline for a manual line break. Nothing is written to YouTube;
upload the PNG yourself (Shorts thumbnails are set in the mobile app).
"""
import argparse, base64, html, json, mimetypes, os, re, shutil, subprocess, sys, tempfile
from datetime import date
from pathlib import Path

W, H = 1080, 1920
MAX_BYTES = 2 * 1024 * 1024
GRID = (216, 384)          # channel Shorts grid tile, for the legibility preview
CACHE_DIR = os.environ.get("YT_INSIGHTS_CACHE", os.path.join(tempfile.gettempdir(), "yt-insights"))

CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "chromium", "chromium-browser", "chrome",
]

STYLES = {
    # bg gradient stops, accent (sub-line + rule), default emoji
    "roast":   dict(bg1="#160406", bg2="#5a0d14", bg3="#a3141f", accent="#ffd000", emoji="💀😭"),
    "hype":    dict(bg1="#041640", bg2="#034694", bg3="#1d74c9", accent="#ffd000", emoji="🔥"),
    "sad":     dict(bg1="#0b1220", bg2="#1c2a44", bg3="#2f4a73", accent="#9fb7d9", emoji="😭"),
    "neutral": dict(bg1="#0a0a0a", bg2="#1e1e1e", bg3="#333333", accent="#ffd000", emoji=""),
}


def find_chrome(explicit=None):
    for c in ([explicit] if explicit else []) + CHROME_CANDIDATES:
        if not c:
            continue
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
        w = shutil.which(c)
        if w:
            return w
    sys.exit("Chrome/Chromium not found. Install Google Chrome or pass --chrome /path/to/binary.")


def chrome_shot(chrome, html_path, out_png, extra=(), scale=1):
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--force-device-scale-factor={scale}", f"--window-size={W},{H}",
           "--virtual-time-budget=3000", f"--screenshot={out_png}", *extra,
           Path(html_path).resolve().as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(out_png):
        sys.exit(f"Chrome did not write a screenshot.\n{r.stderr[-800:]}")


def extract_frame(video, at, chrome, workdir):
    """Frame at `at` seconds. ffmpeg if present, else a headless-Chrome <video> seek."""
    out = os.path.join(workdir, "frame.png")
    ff = shutil.which("ffmpeg")
    if ff:
        subprocess.run([ff, "-y", "-ss", str(at), "-i", video, "-frames:v", "1", "-q:v", "2", out],
                       check=True, capture_output=True)
        return out
    page = os.path.join(workdir, "frame.html")
    Path(page).write_text(
        f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;width:{W}px;height:{H}px;'
        f'overflow:hidden;background:#000}}video{{width:{W}px;height:{H}px;object-fit:cover;display:block}}</style>'
        f'<video src="{Path(video).resolve().as_uri()}#t={at}" muted autoplay playsinline preload="auto"></video>')
    chrome_shot(chrome, page, out, extra=("--autoplay-policy=no-user-gesture-required",))
    from PIL import Image, ImageStat
    if ImageStat.Stat(Image.open(out).convert("L")).mean[0] < 4:
        sys.exit("Frame came out black: headless Chrome could not seek this video. "
                 "Install ffmpeg (brew install ffmpeg) or pass a screenshot with --image.")
    return out


def cutout(photo, workdir):
    """Background removal: rembg if installed, else Apple Vision via swift (macOS 14+). Returns RGBA PNG path or None."""
    os.makedirs(workdir, exist_ok=True)
    out = os.path.join(workdir, "cutout.png")
    try:
        from rembg import remove  # optional heavy dependency
        from PIL import Image
        remove(Image.open(photo)).save(out)
        return out
    except ImportError:
        pass
    swiftc = shutil.which("swiftc")
    script = Path(__file__).with_name("cutout.swift")
    if swiftc and script.exists() and sys.platform == "darwin":
        # compile once (about 30 s), then reuse the binary; rebuild if the script changed
        binary = Path(CACHE_DIR) / "cutout"
        if not binary.exists() or binary.stat().st_mtime < script.stat().st_mtime:
            binary.parent.mkdir(parents=True, exist_ok=True)
            b = subprocess.run([swiftc, "-O", str(script), "-o", str(binary)], capture_output=True, text=True)
            if b.returncode != 0:
                print(f"cutout compile failed ({b.stderr.strip()[-200:]}); using card shape", file=sys.stderr)
                return None
        r = subprocess.run([str(binary), photo, out], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out):
            return out
        print(f"cutout failed ({r.stderr.strip()[-200:] or 'no output'}); using card shape", file=sys.stderr)
    else:
        print("no background remover (install rembg, or run on macOS 14+ with the Swift toolchain); using card shape",
              file=sys.stderr)
    return None


def finish_cutout(path, css_filter):
    """Trim a cutout to its visible pixels and bake grayscale/saturate/brightness/contrast into the pixels.
    Chrome tints the transparent area when a CSS filter is applied to an RGBA image, so filters are applied here instead."""
    from PIL import Image, ImageEnhance
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").getbbox()
    if box:
        im = im.crop(box)
    rgb, alpha = im.convert("RGB"), im.getchannel("A")
    for fn, val in re.findall(r"(grayscale|saturate|brightness|contrast)\(\s*([0-9.]+)%?\s*\)", css_filter or ""):
        v = float(val) / (100 if "%" in css_filter else 1) if float(val) > 3 else float(val)
        if fn == "grayscale":
            rgb = ImageEnhance.Color(rgb).enhance(1 - v)
        elif fn == "saturate":
            rgb = ImageEnhance.Color(rgb).enhance(v)
        elif fn == "brightness":
            rgb = ImageEnhance.Brightness(rgb).enhance(v)
        elif fn == "contrast":
            rgb = ImageEnhance.Contrast(rgb).enhance(v)
    out = Image.merge("RGBA", (*rgb.split(), alpha))
    out.save(path)
    return path


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def build_html(a, style, image_uri):
    lines = [html.escape(l.strip()) for l in a.headline.replace("\\n", "|").split("|") if l.strip()]
    sub = html.escape(a.sub or "")
    emoji = a.emoji if a.emoji is not None else style["emoji"]
    pos = a.text_pos or ("top" if a.photo_uri else "bottom" if image_uri else "middle")
    # vertical anchor of the text block; keeps clear of the bottom 260 px (view-count overlay) and top 160 px
    anchor = {"top": "top:180px", "middle": "top:50%;transform:translateY(-52%)", "bottom": "bottom:380px"}[pos]
    bg = (f'<img class="frame" src="{image_uri}"><div class="shade"></div>' if image_uri else
          '<div class="bg"></div><svg class="pitch" viewBox="0 0 1900 2280" fill="none" stroke="#fff" stroke-width="8">'
          '<rect x="4" y="4" width="1892" height="2272"/><line x1="4" y1="1140" x2="1896" y2="1140"/>'
          '<circle cx="950" cy="1140" r="300"/><rect x="428" y="4" width="1044" height="380"/>'
          '<rect x="428" y="1896" width="1044" height="380"/></svg><div class="vig"></div>')
    brand = "" if a.no_brand else '<div class="brand">THE FOOTBALL ADDA</div>'
    photo_html = ""
    if a.photo_uri and getattr(a, "photo2_uri", None):
        photo_html = (f'<div class="photo cutout duo-l"><img src="{a.photo_uri}"></div>'
                      f'<div class="photo cutout duo-r"><img src="{a.photo2_uri}"></div>')
    elif a.photo_uri:
        photo_html = f'<div class="photo {a.photo_shape}"><img src="{a.photo_uri}"></div>'
    head_html = "".join(f'<div class="h">{l}</div>' for l in lines)
    sub_html = f'<div class="s">{sub}</div>' if sub else ""
    emo_html = f'<div class="e">{emoji}</div>' if emoji else ""
    return f"""<!doctype html><meta charset="utf-8"><title>{html.escape(a.slug)}</title>
<style>
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:{style['bg1']};font-family:Impact,"Arial Narrow","Helvetica Neue",Arial,sans-serif}}
.bg{{position:absolute;inset:0;background:radial-gradient(ellipse 80% 50% at 50% 40%,rgba(255,255,255,.14),transparent 70%),linear-gradient(160deg,{style['bg1']} 0%,{style['bg2']} 50%,{style['bg3']} 100%)}}
svg.pitch{{position:absolute;left:-410px;top:-180px;width:1900px;height:2280px;opacity:.14}}
.vig{{position:absolute;inset:0;background:radial-gradient(ellipse 90% 80% at 50% 50%,transparent 50%,rgba(0,0,0,.7) 100%)}}
img.frame{{position:absolute;inset:0;width:{W}px;height:{H}px;object-fit:cover;object-position:{a.focus}}}
.shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25) 0%,rgba(0,0,0,0) 30%,rgba(0,0,0,.35) 55%,rgba(0,0,0,.88) 100%)}}
.block{{position:absolute;left:60px;right:60px;{anchor};display:flex;flex-direction:column;align-items:center;text-align:center}}
.h{{color:#fff;font-size:{a.size}px;line-height:.92;letter-spacing:.005em;white-space:nowrap;transform:skewX(-8deg);
    text-shadow:0 0 18px rgba(0,0,0,.6),0 10px 0 rgba(0,0,0,.35),0 14px 30px rgba(0,0,0,.6);
    -webkit-text-stroke:5px rgba(0,0,0,.55);paint-order:stroke fill}}
.s{{margin-top:26px;color:{style['accent']};font-size:{int(a.size*0.62)}px;line-height:1;white-space:nowrap;
    text-shadow:0 0 14px rgba(0,0,0,.6),0 8px 24px rgba(0,0,0,.6);-webkit-text-stroke:3px rgba(0,0,0,.5);paint-order:stroke fill}}
.e{{margin-top:36px;font-size:{a.emoji_size}px;line-height:1;filter:drop-shadow(0 12px 22px rgba(0,0,0,.55))}}
.photo{{position:absolute;left:50%;transform:translateX(-50%);filter:drop-shadow(0 24px 40px rgba(0,0,0,.6))}}
.photo img{{display:block;width:100%;height:100%;object-fit:cover;object-position:{a.photo_focus};filter:{a.photo_filter or "none"}}}
.photo.circle{{top:{a.photo_top}px;width:780px;height:780px;border-radius:50%;overflow:hidden;border:16px solid {style['accent']};box-shadow:0 0 0 10px rgba(0,0,0,.35)}}
.photo.card{{top:{a.photo_top}px;width:820px;height:840px;border-radius:44px;overflow:hidden;border:14px solid #fff;transform:translateX(-50%) rotate(-3deg)}}
.photo.cutout{{top:auto;bottom:250px;width:auto;height:{a.photo_height}px}}
.photo.cutout img{{width:auto;max-width:960px;height:100%;object-fit:contain;object-position:50% 100%;filter:drop-shadow(0 0 2px rgba(255,255,255,.35))}}
.photo.duo-l{{left:4%;transform:none;height:{int(a.photo_height*0.9)}px}}
.photo.duo-r{{left:auto;right:4%;transform:none;height:{int(a.photo_height*0.9)}px}}
.photo.duo-l img,.photo.duo-r img{{max-width:500px}}
.brand{{position:absolute;left:0;right:0;bottom:200px;text-align:center;color:#fff;opacity:.9;font-size:44px;letter-spacing:.14em;
    font-family:"Helvetica Neue",Arial,sans-serif;font-weight:700;text-shadow:0 2px 10px rgba(0,0,0,.7)}}
.brand::before{{content:"";display:block;width:220px;height:6px;border-radius:3px;background:{style['accent']};margin:0 auto 18px}}
</style>
{bg}
{photo_html}
<div class="block">{head_html}{sub_html}{emo_html}</div>
{brand}
<script>
// shrink any line that overflows the 960 px text column
for (const el of document.querySelectorAll('.h,.s')) {{
  let s = parseFloat(getComputedStyle(el).fontSize);
  while (el.scrollWidth > 960 && s > 60) {{ s -= 4; el.style.fontSize = s + 'px'; }}
}}
</script>"""


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project-dir", required=True)
    p.add_argument("--slug", required=True, help="file name stem, e.g. chelsea-hull-roast")
    p.add_argument("--headline", required=True, help="big white text; use | for line breaks, 1-3 words per line")
    p.add_argument("--sub", default="", help="smaller accent-coloured line under the headline")
    p.add_argument("--emoji", default=None, help="emoji row under the text; default comes from --style; '' for none")
    p.add_argument("--style", choices=sorted(STYLES), default="hype")
    p.add_argument("--image", help="background frame (jpg/png); covers the full 9:16 canvas")
    p.add_argument("--video", help="pull the background frame from this video (needs --at)")
    p.add_argument("--at", type=float, default=0.0, help="seconds into --video")
    p.add_argument("--photo", help="a person to feature (your face, a player): composited on the background as a panel")
    p.add_argument("--photo-filter", default="",
                   help="CSS filter applied to the person photo(s), e.g. 'grayscale(.6) contrast(1.1)' for a gloomy look")
    p.add_argument("--photo2", help="second person; both become cutouts, --photo on the left, --photo2 on the right")
    p.add_argument("--photo-shape", choices=["circle", "card", "cutout"], default="circle",
                   help="circle = round frame; card = tilted polaroid; cutout = background removed (rembg or macOS Vision)")
    p.add_argument("--photo-focus", default="50% 20%", help="CSS object-position inside the circle/card, keep the face in view")
    p.add_argument("--photo-top", type=int, default=None, help="y of the circle/card panel (default 760, or 920 with an emoji row); text sits above it")
    p.add_argument("--photo-height", type=int, default=1000, help="cutout height in px; it stands on the wordmark line")
    p.add_argument("--focus", default="50% 30%", help="CSS object-position for the frame, e.g. '50%% 20%%' to keep heads in view")
    p.add_argument("--text-pos", choices=["top", "middle", "bottom"], help="default: middle (no image) or bottom (image)")
    p.add_argument("--size", type=int, default=200, help="headline font size in px before auto-shrink")
    p.add_argument("--emoji-size", type=int, default=230)
    p.add_argument("--no-brand", action="store_true", help="drop the channel wordmark")
    p.add_argument("--hd", action="store_true",
                   help="render 2160x3840 (YouTube's recommended Shorts thumbnail size) instead of 1080x1920 (video-frame size)")
    p.add_argument("--chrome", help="path to a Chrome/Chromium binary")
    p.add_argument("--out", help="output PNG path; default yt-insights/thumbnails/<slug>-<date>.png")
    a = p.parse_args()
    if a.photo and a.emoji is None:
        a.emoji = ""                                   # the photo is the reaction; no default emoji on top of it
    if a.photo_top is None:
        a.photo_top = 920 if (a.photo and a.emoji) else 760
    if a.photo and a.emoji and a.photo_height == 1000:
        a.photo_height = 860                           # keep the cutout clear of the emoji row

    from PIL import Image

    global CACHE_DIR
    CACHE_DIR = os.path.join(a.project_dir, "yt-insights", ".cache")
    outdir = Path(a.project_dir) / "yt-insights" / "thumbnails"
    outdir.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else outdir / f"{a.slug}-{date.today().isoformat()}.png"
    chrome = find_chrome(a.chrome)
    style = STYLES[a.style]
    scale = 2 if a.hd else 1
    TW, TH = W * scale, H * scale

    with tempfile.TemporaryDirectory() as tmp:
        frame = a.image
        if a.video:
            frame = extract_frame(a.video, a.at, chrome, tmp)
        image_uri = data_uri(frame) if frame else None
        a.photo_uri = None
        if a.photo:
            src = a.photo
            if a.photo_shape == "cutout":
                cut = cutout(a.photo, tmp)
                if cut:
                    finish_cutout(cut, a.photo_filter)
                if cut:
                    src = cut
                else:
                    a.photo_shape = "card"
            a.photo_uri = data_uri(src)
            a.photo2_uri = None
            if a.photo2:
                cut2 = cutout(a.photo2, os.path.join(tmp, "second"))
                if cut2:
                    finish_cutout(cut2, a.photo_filter)
                a.photo2_uri = data_uri(cut2 or a.photo2)
                if not cut2:
                    print("second photo could not be cut out; placed as-is", file=sys.stderr)
        page = build_html(a, style, image_uri)
        html_path = out.with_suffix(".html")
        html_path.write_text(page)
        raw = os.path.join(tmp, "shot.png")
        chrome_shot(chrome, html_path, raw, scale=scale)

        im = Image.open(raw).convert("RGB")
        if im.size != (TW, TH):                     # never trust the window size blindly
            im = im.resize((TW, TH), Image.LANCZOS)
        im.save(out, "PNG", optimize=True)
        final = out
        if out.stat().st_size > MAX_BYTES:          # YouTube's 2 MB cap: fall back to JPEG
            final = out.with_suffix(".jpg")
            for q in (92, 88, 84, 80):
                im.save(final, "JPEG", quality=q, optimize=True)
                if final.stat().st_size <= MAX_BYTES:
                    break
            out.unlink()
        grid = final.with_name(final.stem + "-grid.png")
        im.resize(GRID, Image.LANCZOS).save(grid, "PNG")

    chk = Image.open(final)
    ok = chk.size == (TW, TH) and final.stat().st_size <= MAX_BYTES
    print(json.dumps({"thumbnail": str(final), "size": list(chk.size), "bytes": final.stat().st_size,
                      "grid_preview": str(grid), "html_source": str(html_path), "ok": ok}, indent=2))
    if not ok:
        sys.exit("Output failed the size check; see above.")


if __name__ == "__main__":
    main()
