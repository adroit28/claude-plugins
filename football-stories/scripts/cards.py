#!/usr/bin/env python3
"""Render every scene state of a story to graphics/v<N>/<scene>_<step>.png (1080x1920) with headless Chrome.

  cards.py <story.vN.json> [scene ...] [--force] [--allow-doubtful]
  cards.py --demo <out_dir>             render every template with sample props (layout test)

Each scene names a template and props; step k shows the first k reveals. States whose HTML is
unchanged since the last run, or identical to an earlier version's card, are copied instead of
rendered, so a revision re-renders only the cards it touched and earlier versions stay intact.
Graphics stay inside x 80-930, y 250-1180; the caption band (centred at 1330) and the Shorts UI
(bottom 450, right 150) stay clear. A labelled contact sheet with the safe zone drawn goes to
graphics/v<N>/sheet.png: Read it before composing.

Prop text is HTML-escaped. "\\n" breaks a line and **x** marks an emphasis span (gold, unless the
template styles it differently). Colours are theme tokens (ink muted line gold red green cfc
claret sky card) or any CSS colour.
"""
import argparse, html, json, pathlib, re, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import CHROME, H, W, Story, shorts_dir

TOKENS = {"ink", "muted", "line", "gold", "red", "green", "cfc", "claret", "sky", "card"}

CSS = """
@font-face{font-family:Anton;src:url('file://%(f)s/Anton-Regular.ttf')}
@font-face{font-family:Barlow;font-weight:600;src:url('file://%(f)s/BarlowCondensed-SemiBold.ttf')}
@font-face{font-family:Barlow;font-weight:800;src:url('file://%(f)s/BarlowCondensed-ExtraBold.ttf')}
:root{--ink:#F4F6FB;--muted:#8E9AB8;--line:#26314F;--gold:#FFD400;--red:#FF4545;--green:#2FD980;
      --cfc:#2D6BE0;--claret:#8C1D4F;--sky:#8FD3F0;--card:#111A30}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden}
body{background:radial-gradient(120%% 70%% at 50%% 38%%,#15213F 0%%,#0A1022 55%%,#05070F 100%%);color:var(--ink);
     font-family:Barlow,sans-serif;position:relative}
.pitch{position:absolute;inset:0;opacity:.10}
.box{position:absolute;left:80px;width:850px}
.kicker{font:600 40px/1 Barlow;letter-spacing:.18em;color:var(--muted);text-transform:uppercase}
.pill{display:inline-block;font:800 40px/1 Barlow;letter-spacing:.12em;padding:16px 26px;border-radius:8px;text-transform:uppercase}
.anton{font-family:Anton;font-weight:400;line-height:.95;text-transform:uppercase}
.card{background:var(--card);border:3px solid var(--line);border-radius:22px;display:flex;align-items:center;gap:34px;padding:26px 30px}
.cal{width:190px;height:190px;border-radius:16px;overflow:hidden;flex:none;background:#EDF0F7;color:#0A1022;text-align:center}
.cal .m{font:800 44px/62px Barlow;letter-spacing:.12em;color:#fff}
.cal .y{font:400 92px/128px Anton}
.slot{border:4px dashed var(--line);background:transparent}
.big{font-family:Anton;text-transform:uppercase;line-height:1}
.stamp{position:absolute;font:400 84px/1 Anton;color:var(--red);border:8px solid var(--red);border-radius:14px;
       padding:14px 26px 10px;transform:rotate(-8deg);letter-spacing:.04em;background:rgba(10,16,34,.85)}
.stat{width:170px;flex:none;text-align:center}
.stat b{display:block;font:400 120px/1 Anton}
.stat i{display:block;font:800 30px/1 Barlow;letter-spacing:.14em;color:var(--muted);font-style:normal;margin-top:6px}
.t1{font:400 58px/1.02 Anton;text-transform:uppercase}
.t2{font:600 38px/1.1 Barlow;color:var(--muted);margin-top:12px;letter-spacing:.04em}
.em{color:var(--gold);font-weight:inherit}
"""

PITCH = """<svg class="pitch" viewBox="0 0 1080 1920" fill="none" stroke="#fff" stroke-width="4">
<rect x="-40" y="120" width="1160" height="1680"/><line x1="-40" y1="960" x2="1120" y2="960"/>
<circle cx="540" cy="960" r="230"/><rect x="250" y="120" width="580" height="300"/><rect x="250" y="1500" width="580" height="300"/></svg>"""


def c(v, default="ink"):
    v = v or default
    return "var(--%s)" % v if v in TOKENS else v

def t(s):
    """Prop text -> safe HTML: escape, \\n -> <br>, **x** -> emphasis span."""
    s = html.escape(str(s), quote=False).replace("\n", "<br>")
    return re.sub(r"\*\*(.+?)\*\*", r'<b class="em">\1</b>', s)


class Ctx:
    def __init__(self, fonts, photo_uri=None):
        self.fonts, self.photo = fonts, photo_uri

    def page(self, inner, extra_css="", bg=""):
        return "<html><head><meta charset='utf-8'><style>%s%s</style></head><body>%s%s</body></html>" % (
            CSS % {"f": self.fonts}, extra_css, PITCH, bg + inner)

    def photo_bg(self, top=120, height=980, opacity=.42):
        if not self.photo: return ""
        return ("""<div style="position:absolute;left:0;top:%dpx;width:1080px;height:%dpx;background:url('%s') center 20%%/cover;opacity:%s"></div>
          <div style="position:absolute;left:0;top:%dpx;width:1080px;height:420px;background:linear-gradient(transparent,#0A1022)"></div>"""
                % (top, height, self.photo, opacity, top + height - 400))


# =====================================================================================  templates
# Each takes (ctx, props, step) and returns a full HTML page. STEPS[name](props) = number of states.

def calendar_gap(x, p, step):
    """Two dated cards joined by a gap line. step 1: start card + empty slot; 2: gap label + stamp; 3: end card.
    props: kicker, start{month,year,label,sub,color,title_color}, end{...}, gap_label, stamp"""
    def cal_card(d, filled=True):
        if not filled:
            return """<div class="card slot" style="height:250px;justify-content:center">
          <span class="big" style="font-size:150px;color:var(--line)">?</span></div>"""
        return """<div class="card" style="height:250px">
      <div class="cal"><div class="m" style="background:%s">%s</div><div class="y">%s</div></div>
      <div><div class="t1" style="font-size:66px;color:%s">%s</div><div class="t2">%s</div></div></div>""" % (
            c(d.get("color"), "cfc"), t(d["month"]), t(d["year"]), c(d.get("title_color") or d.get("color"), "cfc"), t(d["label"]), t(d.get("sub", "")))
    gap_line = "var(--red)" if step >= 2 else "var(--line)"
    dash = "solid" if step >= 2 else "dashed"
    middle = ""
    if step >= 2:
        middle = """<div style="position:absolute;left:300px;top:90px" class="pill"
                     ><span style="font:400 64px/1 Anton;color:var(--ink)">%s</span></div>""" % t(p.get("gap_label", ""))
        if p.get("stamp"):
            middle += """
                   <div class="stamp" style="left:250px;top:200px">%s</div>""" % t(p["stamp"])
    return x.page("""
    <div class="box" style="top:280px"><div class="kicker">%s</div></div>
    <div class="box" style="top:350px">%s</div>
    <div class="box" style="top:600px;height:360px">
      <div style="position:absolute;left:124px;top:0;height:360px;border-left:10px %s %s"></div>%s</div>
    <div class="box" style="top:960px">%s</div>""" % (
        t(p.get("kicker", "")), cal_card(p["start"]), dash, gap_line, middle, cal_card(p["end"], filled=step >= 3)), bg=x.photo_bg())


def name_plate(x, p, step):
    """Big two-line name. step 1: name; 2: flag + country. props: kicker, first, last, flag, country, country_color"""
    flag = """<div style="margin-top:34px;display:flex;align-items:center;gap:24px">
                <span style="font-size:96px;line-height:1">%s</span>
                <span class="big" style="font-size:84px;color:%s">%s</span></div>""" % (
        p.get("flag", ""), c(p.get("country_color"), "sky"), t(p.get("country", ""))) if step >= 2 else ""
    if x.photo:
        return x.page("""<div style="position:absolute;left:0;top:150px;width:1080px;height:760px;background:url('%s') center 20%%/cover"></div>
          <div style="position:absolute;left:0;top:600px;width:1080px;height:320px;background:linear-gradient(transparent,#0A1022)"></div>
          <div class="box" style="top:870px"><div class="big" style="font-size:120px">%s</div>
          <div class="big" style="font-size:150px;color:var(--gold)">%s</div>%s</div>""" % (x.photo, t(p["first"]), t(p["last"]), flag))
    return x.page("""<div class="box" style="top:430px">
      <div class="kicker" style="margin-bottom:30px">%s</div>
      <div class="big" style="font-size:190px">%s</div>
      <div class="big" style="font-size:218px;color:var(--gold)">%s</div>%s</div>""" % (t(p.get("kicker", "")), t(p["first"]), t(p["last"]), flag))


def rule_card(x, p, step):
    """A rule in a red-bordered card. step 1: the rule; 2: footer line (icon + text).
    props: pill, title, big, unit, note, footer{icon,text}"""
    f = p.get("footer") or {}
    waited = """<div class="box" style="top:1000px;display:flex;align-items:center;gap:26px">
        <span style="font-size:110px;line-height:1">%s</span>
        <span class="big" style="font-size:110px;color:var(--gold)">%s</span></div>""" % (f.get("icon", ""), t(f.get("text", ""))) if step >= 2 and f else ""
    return x.page("""
    <div class="box" style="top:300px"><span class="pill" style="background:var(--gold);color:#0A1022">%s</span></div>
    <div class="box" style="top:420px">
      <div class="card" style="display:block;padding:40px 44px 34px;border-color:var(--red)">
        <div class="t1" style="font-size:84px">%s</div>
        <div style="display:flex;align-items:flex-end;gap:26px;margin-top:10px">
          <span class="big" style="font-size:290px;color:var(--red);line-height:.9">%s</span>
          <span class="t2" style="font-size:46px;margin-bottom:26px">%s</span></div>
        <div class="t2" style="font-size:32px;margin-top:18px">%s</div></div></div>%s""" % (
        t(p.get("pill", "")), t(p.get("title", "")), t(p.get("big", "")), t(p.get("unit", "")), t(p.get("note", "")), waited), bg=x.photo_bg())


def stat_stack(x, p, step):
    """Heading plus up to 4 stat cards added one per step. step 1: heading only.
    props: heading, items[{stat, unit, title, sub, gold}]"""
    items = p["items"]; n = len(items)
    pitch, hgt = (262, 236) if n <= 3 else (195, 175)
    def ach(it):
        gold = it.get("gold")
        border = "border-color:var(--gold);background:#1D1A08" if gold else ""
        return """<div class="card" style="height:%dpx;%s"><div class="stat"><b style="color:%s">%s</b><i>%s</i></div>
      <div><div class="t1">%s</div><div class="t2">%s</div></div></div>""" % (
            hgt, border, "var(--gold)" if gold else "var(--ink)", t(it["stat"]), t(it.get("unit", "")), t(it["title"]), t(it.get("sub", "")))
    body = "".join('<div class="box" style="top:%dpx">%s</div>' % (400 + i * pitch, ach(r)) for i, r in enumerate(items[:step - 1]))
    return x.page("""<div class="box" style="top:285px"><div class="big" style="font-size:84px;color:var(--gold)">%s</div></div>""" % t(p.get("heading", "")) + body,
                  bg=x.photo_bg())


def transfer_path(x, p, step):
    """Milestone, then a club card, then an arrow to a second club card (loan, sale, return).
    step 1: top line; 2: first club; 3: arrow + second club.
    props: top{pill, pill_color, text, tick}, first{kicker, club, line, bg, border, text_color, kicker_color},
           arrow, second{...}"""
    tp = p.get("top") or {}
    pc = tp.get("pill_color", "green")
    tick = ' <span style="color:%s">✓</span>' % c(pc) if tp.get("tick") else ""
    top = """<div class="box" style="top:290px;display:flex;align-items:center;gap:22px">
      <span class="pill" style="background:%s;color:#06210F">%s</span>
      <span class="big" style="font-size:84px">%s%s</span></div>""" % (c(pc), t(tp.get("pill", "")), t(tp.get("text", "")), tick)
    def club(d, top_px):
        return """<div class="box" style="top:%dpx"><div class="card club" style="display:block;height:300px;background:%s;border-color:%s;padding:36px 40px">
      <div class="kicker" style="color:%s">%s</div><div class="big" style="font-size:120px;margin-top:10px">%s</div>
      <div class="t2" style="color:%s;font-size:44px">%s</div></div></div>""" % (
            top_px, d.get("bg", "#0E2A66"), c(d.get("border"), "cfc"), c(d.get("kicker_color"), "#A9C3FF"), t(d.get("kicker", "")),
            t(d["club"]), c(d.get("text_color"), "#D7E3FF"), t(d.get("line", "")))
    first = club(p["first"], 430) if step >= 2 else ""
    second = ""
    if step >= 3:
        second = """<div class="box" style="top:752px;text-align:center"><span class="big" style="font-size:70px;color:var(--gold)">%s</span></div>
      """ % t(p.get("arrow", "↓")) + club(p["second"], 850)
    return x.page(top + first + second, extra_css=".club .em{font:400 50px Anton;color:#fff}", bg=x.photo_bg())


def headline_card(x, p, step):
    """Closing line, optionally with flag + name. One state. props: lines[], flag, name, name_color"""
    lines = "".join('<div class="big" style="font-size:150px">%s</div>' % t(l) for l in p.get("lines", []))
    name = ""
    if p.get("name"):
        flag = '<span style="font-size:110px;line-height:1">%s</span>\n      ' % p["flag"] if p.get("flag") else ""
        name = """
      <div style="display:flex;align-items:center;gap:26px;margin-top:40px">%s<span class="big" style="font-size:170px;color:%s">%s</span></div>""" % (
            flag, c(p.get("name_color"), "gold"), t(p["name"]))
    return x.page("""<div class="box" style="top:520px">
      %s%s</div>""" % (lines, name), bg=x.photo_bg())


def stat_compare(x, p, step):
    """Two numbers side by side, then a verdict. step 1: header + left; 2: right; 3: verdict.
    props: kicker, title, left{value, label, color}, right{...}, verdict, sub"""
    def col(d, show):
        if not show:
            return '<div style="flex:1;height:420px;border:4px dashed var(--line);border-radius:22px"></div>'
        return """<div class="card" style="flex:1;height:420px;display:block;text-align:center;padding:40px 20px;border-color:%s">
          <div class="big" style="font-size:230px;color:%s">%s</div><div class="t2" style="font-size:44px;margin-top:22px">%s</div></div>""" % (
            c(d.get("color"), "line"), c(d.get("color"), "ink"), t(d["value"]), t(d.get("label", "")))
    verdict = """<div class="box" style="top:1010px;text-align:center"><div class="big" style="font-size:110px;color:var(--gold)">%s</div>
      <div class="t2" style="font-size:40px">%s</div></div>""" % (t(p.get("verdict", "")), t(p.get("sub", ""))) if step >= 3 else ""
    return x.page("""<div class="box" style="top:290px"><div class="kicker">%s</div>
      <div class="big" style="font-size:96px;margin-top:18px">%s</div></div>
      <div class="box" style="top:540px;display:flex;gap:30px">%s%s</div>%s""" % (
        t(p.get("kicker", "")), t(p.get("title", "")), col(p["left"], True), col(p["right"], step >= 2), verdict), bg=x.photo_bg())


def timeline(x, p, step):
    """Vertical dated timeline, one event per step (max 4). props: kicker, events[{date, title, sub, color}]"""
    ev = p["events"][:4]; gap = 820 // max(len(ev), 1)
    rows = ""
    for i, e in enumerate(ev[:step]):
        y = 380 + i * gap
        rows += """<div style="position:absolute;left:80px;top:%dpx;width:850px;display:flex;gap:40px;align-items:flex-start">
          <div style="width:64px;flex:none;display:flex;justify-content:center"><div style="width:44px;height:44px;border-radius:50%%;background:%s;border:6px solid #0A1022;margin-top:18px"></div></div>
          <div><div class="pill" style="background:%s;color:#0A1022;font-size:34px;padding:10px 18px">%s</div>
          <div class="t1" style="font-size:66px;margin-top:14px">%s</div><div class="t2">%s</div></div></div>""" % (
            y, c(e.get("color"), "gold"), c(e.get("color"), "gold"), t(e["date"]), t(e["title"]), t(e.get("sub", "")))
    spine = '<div style="position:absolute;left:108px;top:400px;height:%dpx;border-left:8px solid var(--line)"></div>' % (gap * (len(ev) - 1) + 20)
    return x.page("""<div class="box" style="top:285px"><div class="kicker">%s</div></div>%s%s""" % (t(p.get("kicker", "")), spine, rows), bg=x.photo_bg())


def quote_card(x, p, step):
    """A sourced quote. step 1: quote; 2: speaker + date + source. props: kicker, quote, speaker, role, date, source"""
    who = ""
    if step >= 2:
        who = """<div class="box" style="top:1010px;display:flex;align-items:center;gap:26px">
          <div style="width:12px;height:120px;background:var(--gold);border-radius:6px"></div>
          <div><div class="big" style="font-size:78px">%s</div><div class="t2" style="margin-top:6px">%s</div>
          <div class="t2" style="font-size:30px;margin-top:6px">%s</div></div></div>""" % (
            t(p.get("speaker", "")), t(" · ".join(v for v in (p.get("role"), p.get("date")) if v)), t(p.get("source", "")))
    q = t(p["quote"]); size = 104 if len(p["quote"]) <= 50 else 84 if len(p["quote"]) <= 80 else 68
    return x.page("""<div class="box" style="top:290px"><span class="pill" style="background:var(--gold);color:#0A1022">%s</span></div>
      <div class="box" style="top:420px"><div class="card" style="display:block;padding:40px 46px 50px;min-height:520px">
        <div class="big" style="font-size:200px;color:var(--gold);height:120px;line-height:1">&ldquo;</div>
        <div class="big" style="font-size:%dpx;line-height:1.05;text-transform:none">%s</div></div></div>%s""" % (
        t(p.get("kicker", "")), size, q, who), bg=x.photo_bg())


TEMPLATES = {"calendar_gap": (calendar_gap, lambda p: 3), "name_plate": (name_plate, lambda p: 2),
             "rule_card": (rule_card, lambda p: 2 if p.get("footer") else 1),
             "stat_stack": (stat_stack, lambda p: len(p["items"]) + 1), "transfer_path": (transfer_path, lambda p: 3),
             "headline_card": (headline_card, lambda p: 1), "stat_compare": (stat_compare, lambda p: 3),
             "timeline": (timeline, lambda p: len(p["events"][:4])), "quote_card": (quote_card, lambda p: 2)}


# =====================================================================================  rendering
def shoot(html_text, html_path, png, force=False, reuse=()):
    """Write the HTML and screenshot it, unless the same HTML was already rendered here or in an
    earlier version's folder (then the PNG is copied)."""
    if not force and png.exists() and html_path.exists() and html_path.read_text() == html_text:
        return False
    html_path.write_text(html_text)
    for d in ([] if force else reuse):
        old = d / png.name
        if old.exists() and old.with_suffix(".html").exists() and old.with_suffix(".html").read_text() == html_text:
            shutil.copyfile(old, png); return False
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--allow-file-access-from-files", "--window-size=%d,%d" % (W, H), "--virtual-time-budget=1500",
                    "--screenshot=%s" % png, html_path.as_uri()], check=True, capture_output=True)
    return True

def sheet(pngs, out, cols=6, scale=0.25):
    from PIL import Image, ImageDraw
    tw, th = int(W * scale), int(H * scale); rows = (len(pngs) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 30)), "#222"); d = ImageDraw.Draw(im)
    for k, p in enumerate(pngs):
        x0, y0 = (k % cols) * tw, (k // cols) * (th + 30)
        im.paste(Image.open(p).convert("RGB").resize((tw, th)), (x0, y0 + 30))
        s = lambda v: int(v * scale)
        d.rectangle([x0 + s(80), y0 + 30 + s(250), x0 + s(930), y0 + 30 + s(1180)], outline="#00E0FF")   # graphics safe zone
        d.rectangle([x0 + s(80), y0 + 30 + s(1250), x0 + s(930), y0 + 30 + s(1420)], outline="#FF00C8")  # caption band
        d.text((x0 + 6, y0 + 8), p.stem, fill="white")
    im.save(out)

def states(scene):
    fn, n = TEMPLATES[scene["template"]]
    k = len(scene.get("steps") or [None]); return fn, max(1, min(k, n(scene["props"])))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", nargs="?"); ap.add_argument("scenes", nargs="*")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--allow-doubtful", action="store_true")
    ap.add_argument("--demo", help="render every template with sample props into this folder")
    a = ap.parse_args()

    if a.demo:
        out = pathlib.Path(a.demo).resolve(); out.mkdir(parents=True, exist_ok=True)
        demo = json.loads((pathlib.Path(__file__).resolve().parent.parent / "skills/build/references/template-demo.json").read_text())
        x = Ctx(shorts_dir(out) / "fonts"); pngs = []
        for sc in demo["scenes"]:
            fn, n = TEMPLATES[sc["template"]]
            for k in range(1, n(sc["props"]) + 1):
                png = out / ("%s_%d.png" % (sc["template"], k)); shoot(fn(x, sc["props"], k), png.with_suffix(".html"), png, a.force); pngs.append(png)
        sheet(pngs, out / "sheet.png"); print("demo sheet:", out / "sheet.png"); return

    st = Story(a.story); gdir = st.out("graphics/v%d/x" % st.version).parent
    earlier = sorted((d for d in (st.dir / "graphics").glob("v*") if d.is_dir() and d != gdir),
                     key=lambda d: -int(d.name[1:]) if d.name[1:].isdigit() else 0)
    assets = st.data.get("assets", {})
    for sc in st.data["scenes"]:                      # check everything before rendering anything
        if sc["template"] not in TEMPLATES:
            sys.exit("scene %s: unknown template %r (have: %s)" % (sc["id"], sc["template"], ", ".join(TEMPLATES)))
        if sc.get("photo"):
            asset = assets.get(sc["photo"]) or sys.exit("scene %s: unknown asset %r" % (sc["id"], sc["photo"]))
            cls = asset.get("rights", {}).get("class", "unknown")
            if cls in ("doubtful", "unknown") and not a.allow_doubtful:
                sys.exit("scene %s uses %s, rights class %r. Drop the photo, or pass --allow-doubtful and flag it in the hand-over." % (sc["id"], sc["photo"], cls))
    pngs, made = [], 0
    for sc in st.data["scenes"]:
        photo = st.p(assets[sc["photo"]]["path"]).as_uri() if sc.get("photo") else None
        x = Ctx(st.fonts, photo)
        fn, n = states(sc)
        for k in range(1, n + 1):
            png = gdir / ("%s_%d.png" % (sc["id"], k)); pngs.append(png)
            if a.scenes and sc["id"] not in a.scenes: continue
            if shoot(fn(x, sc["props"], k), png.with_suffix(".html"), png, a.force, earlier):
                made += 1; print("ok", png.name)
    sheet(pngs, gdir / "sheet.png")
    print("%d rendered, %d unchanged; sheet: %s" % (made, len(pngs) - made, gdir / "sheet.png"))


if __name__ == "__main__":
    main()
