#!/usr/bin/env python3
"""Generate one image with the Gemini API and save it to an explicit path.

Usage:
  python3 gen.py "prompt text" --out /abs/path/name.jpg [--ratio 4:5] [--size 1K] [--model gemini-3.1-flash-image]
  python3 gen.py --prompt-file prompts.md --section photo --out /abs/path/name.jpg   # uses a saved prompt block
  python3 gen.py "make the skin a deeper tan, change nothing else" --ref "a.jpg" --out /abs/path/edit.jpg
  python3 gen.py "compose: image 1 is ..., image 2 is ..." --ref a.jpg --ref b.jpg --out ...   # refs numbered in order

--out is required: the caller decides where every image goes. Refuses to overwrite
an existing file unless --force is given. The API returns JPEG only.

API key lookup, first hit wins: $GEMINI_API_KEY, the file in $GEMINI_IMAGE_ENV,
~/.config/gemini-image/.env (line GEMINI_API_KEY=...). Standard library only.
"""
import argparse, base64, json, os, pathlib, re, sys, urllib.request, urllib.error

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_ENV = pathlib.Path.home() / ".config" / "gemini-image" / ".env"

def load_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    candidates = [pathlib.Path(p).expanduser() for p in [os.environ.get("GEMINI_IMAGE_ENV")] if p]
    candidates.append(DEFAULT_ENV)
    for env in candidates:
        if key:
            break
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit(f"No GEMINI_API_KEY found. Put GEMINI_API_KEY=... in {DEFAULT_ENV}")
    return key

def prompt_from_file(path, section):
    """Pull the first blockquote after a heading containing `section` (case-insensitive)."""
    text = pathlib.Path(path).read_text()
    m = re.search(r"^#+ .*" + re.escape(section) + r".*?$", text, re.I | re.M)
    if not m:
        sys.exit(f"No heading containing '{section}' in {path}")
    rest = text[m.end():]
    q = re.search(r"((?:^> .*\n?)+)", rest, re.M)
    if not q:
        sys.exit("No blockquote found under that heading")
    return " ".join(l[2:].strip() for l in q.group(1).splitlines())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--prompt-file"); ap.add_argument("--section", default="photo")
    ap.add_argument("--out", required=True, help="full path of the image to write (.jpg)")
    ap.add_argument("--force", action="store_true", help="overwrite --out if it exists")
    ap.add_argument("--ratio", default="4:5")
    ap.add_argument("--size", default="1K", help="512px, 1K, 2K, 4K (uppercase K)")
    ap.add_argument("--model", default="gemini-3.1-flash-image")
    ap.add_argument("--ref", action="append", default=[],
                    help="reference image (jpg/png); repeat the flag for several. Refer to them in the prompt as image 1, image 2, ... in the order given")
    a = ap.parse_args()

    out = pathlib.Path(a.out).expanduser().resolve()
    if out.suffix.lower() not in (".jpg", ".jpeg"):
        out = out.with_suffix(".jpg")
    if out.exists() and not a.force:
        sys.exit(f"{out} already exists; pick another name or pass --force")
    if not out.parent.is_dir():
        sys.exit(f"folder does not exist: {out.parent}")

    prompt = a.prompt or (prompt_from_file(a.prompt_file, a.section) if a.prompt_file else None)
    if not prompt:
        sys.exit("Give a prompt or --prompt-file")

    parts = []
    for ref in a.ref:
        rp = pathlib.Path(ref).expanduser()
        if not rp.exists():
            sys.exit(f"reference image not found: {rp}")
        mime = "image/png" if rp.suffix.lower() == ".png" else "image/jpeg"
        parts.append({"type": "image", "mime_type": mime,
                      "data": base64.b64encode(rp.read_bytes()).decode()})
    parts.append({"type": "text", "text": prompt})
    body = {
        "model": a.model,
        "input": parts,
        "response_format": {"type": "image", "mime_type": "image/jpeg",
                            "aspect_ratio": a.ratio, "image_size": a.size},
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
        headers={"x-goog-api-key": load_key(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:2000]}")

    images, texts = [], []
    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "image" and o.get("data"):
                images.append(o["data"])
            elif o.get("type") == "text" and o.get("text"):
                texts.append(o["text"])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(resp)

    if not images:
        dump = out.parent / "last-response.json"
        dump.write_text(json.dumps(resp, indent=2))
        sys.exit("No image returned. Model said: " + (" | ".join(texts) or "(nothing)") +
                 f"\nFull response saved to {dump}")
    out.write_bytes(base64.b64decode(images[-1]))
    print(f"saved {out} ({out.stat().st_size//1024} KB)")
    if texts: print("model note:", " | ".join(texts)[:500])

if __name__ == "__main__":
    main()
