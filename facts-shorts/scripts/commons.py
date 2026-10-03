#!/usr/bin/env python3
"""Public-domain / CC photos from Wikimedia Commons: search (metadata only), then download one file on a yes.

  commons.py search "Alexander Fleming" [--limit 8] [--any]  licence, author, size, page per file (no download)
  commons.py get <story.vN.json> "File:Name.jpg" --as fleming.jpg --yes [--rotate 1|2|3] [--width 1600]
  commons.py strip <story.vN.json>                           contact strip of src/ images -> build/check/src_strip.jpg

search keeps to images (filetype:bitmap|drawing) so scanned PDF/DjVu books don't crowd the results;
--any lifts that. It reads the Commons API (prop=imageinfo with extmetadata: LicenseShortName, Artist, Credit,
DateTimeOriginal) and prints a rights guess: pd / cc / doubtful / unusable (NC or ND licences are
unusable in a monetised Short; CC BY / BY-SA need the attribution line in the description).
Descriptions on Commons can mislead (e.g. a famous name used for a different group or year): read
the page title and date before picking.

get needs --yes, which stands for the user's explicit yes to this download. It saves the
iiurlwidth thumbnail (default 1600 px) to <edit>/src/<as>, applies --rotate with ffmpeg transpose
(1 = 90° clockwise, 2 = 90° counter-clockwise, 3 = 180°) when the file comes out sideways, and logs
title, page, licence, author, attribution, url and date to src/sources.json. Always look at
`commons.py strip` before using a file. Stdlib + ffmpeg.
"""
import argparse, datetime as dt, html, json, pathlib, re, subprocess, sys, urllib.parse, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

API = "https://commons.wikimedia.org/w/api.php?"
UA = {"User-Agent": "facts-shorts/0.1 (personal YouTube Shorts tool; contact via github.com/adroit28/claude-plugins)"}
strip_tags = lambda s: re.sub(r"<[^>]+>", "", html.unescape(s or "")).strip()


def api(params):
    q = urllib.parse.urlencode({"format": "json", **params})
    return json.load(urllib.request.urlopen(urllib.request.Request(API + q, headers=UA), timeout=40))


def info(ii, title):
    m = ii.get("extmetadata", {})
    lic = strip_tags(m.get("LicenseShortName", {}).get("value")); artist = strip_tags(m.get("Artist", {}).get("value"))
    credit = strip_tags(m.get("Credit", {}).get("value")); date = re.sub(r"date QS.*", "", strip_tags(m.get("DateTimeOriginal", {}).get("value"))).strip()
    flags = []
    if re.search(r"public domain|^PD|CC0", lic, re.I): cls = "pd"
    elif re.search(r"^CC", lic): cls = "cc"
    else: cls, flags = "doubtful", ["licence %r: check the file page" % lic]
    if re.search(r"\bNC\b|\bND\b|-NC|-ND", lic): cls, flags = "unusable", ["NC/ND licence: not usable in a monetised Short"]
    if lic.upper().startswith("CC0") and not re.search(r"own work", credit, re.I):
        cls, flags = "doubtful", flags + ["CC0 without an own-work credit: check who made it"]
    return {"title": title, "page": ii.get("descriptionurl"), "licence": lic, "author": artist[:120], "credit": credit[:160],
            "date": date[:40], "size": "%sx%s" % (ii.get("width"), ii.get("height")), "rights": cls, "flags": flags,
            "attribution": "%s, %s, via Wikimedia Commons" % (artist or "Unknown author", lic) if cls == "cc" else None}


def search(q, limit, any_type=False):
    if not any_type and "filetype:" not in q: q += " filetype:bitmap|drawing"
    d = api({"action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": q, "gsrlimit": limit,
             "prop": "imageinfo", "iiprop": "extmetadata|url|size",
             "iiextmetadatafilter": "LicenseShortName|Artist|Credit|DateTimeOriginal"})
    pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for p in pages:
        r = info((p.get("imageinfo") or [{}])[0], p.get("title"))
        print("%-9s %-24s %-11s %s\n          %s | date %s | %s%s" % (r["rights"], r["licence"][:24], r["size"], r["title"],
              r["author"][:60] or "?", r["date"] or "?", r["page"], ("\n          ! " + "; ".join(r["flags"])) if r["flags"] else ""))
    print("(%d results; metadata only, nothing downloaded)" % len(pages))


def get(st, title, name, width, rotate):
    if not title.startswith("File:"): title = "File:" + title
    d = api({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "extmetadata|url|size", "iiurlwidth": width,
             "iiextmetadatafilter": "LicenseShortName|Artist|Credit|DateTimeOriginal"})
    p = next(iter(d["query"]["pages"].values()))
    if "imageinfo" not in p: sys.exit("not found on Commons: %s" % title)
    ii = p["imageinfo"][0]; r = info(ii, p["title"])
    if r["rights"] in ("unusable", "doubtful"):
        sys.exit("refusing %s: rights %s (%s)" % (title, r["rights"], "; ".join(r["flags"])))
    url = ii.get("thumburl") or ii["url"]
    src = st.dir / "src"; src.mkdir(exist_ok=True); out = src / name
    if out.exists(): sys.exit("%s exists: pick another --as name (files are never overwritten)" % out)
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
    tmp = out.with_name("_dl_" + name); tmp.write_bytes(data)
    vf = ["transpose=%d" % rotate] if rotate in (1, 2) else (["transpose=1,transpose=1"] if rotate == 3 else [])
    if vf or tmp.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp)] + (["-vf", vf[0]] if vf else []) + ["-q:v", "2", str(out)], check=True)
        tmp.unlink()
    else:
        tmp.rename(out)
    log = src / "sources.json"
    j = json.loads(log.read_text()) if log.exists() else {}
    j[name] = {**{k: r[k] for k in ("title", "page", "licence", "author", "date", "rights", "attribution")},
               "url": url, "rotate": rotate or None, "downloaded": dt.date.today().isoformat()}
    log.write_text(json.dumps(j, indent=1, ensure_ascii=False))
    print("saved %s (%s, %s) and logged it in src/sources.json" % (out, r["licence"], r["size"]))


def strip(st):
    src = st.dir / "src"; ims = sorted(p for p in src.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if not ims: sys.exit("no images in %s" % src)
    out = st.build / "check" / "src_strip.jpg"; out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in ims: cmd += ["-i", str(p)]
    fc = ";".join("[%d:v]scale=-2:420,setsar=1[v%d]" % (i, i) for i in range(len(ims)))
    fc += ";" + "".join("[v%d]" % i for i in range(len(ims))) + ("hstack=inputs=%d[out]" % len(ims) if len(ims) > 1 else "null[out]")
    cmd += ["-filter_complex", fc, "-map", "[out]"]
    subprocess.run(cmd + ["-frames:v", "1", str(out)], check=True)
    print("strip: %s, left to right: %s (Read it; check orientation and what each photo shows)" % (out, ", ".join(p.name for p in ims)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["search", "get", "strip"]); ap.add_argument("args", nargs="+")
    ap.add_argument("--limit", type=int, default=8); ap.add_argument("--as", dest="name"); ap.add_argument("--yes", action="store_true")
    ap.add_argument("--any", action="store_true", help="search: include PDFs, DjVu, audio and video")
    ap.add_argument("--width", type=int, default=1600); ap.add_argument("--rotate", type=int, choices=[1, 2, 3])
    a = ap.parse_args()
    if a.cmd == "search":
        return search(" ".join(a.args), a.limit, a.any)
    from common import Story
    st = Story(a.args[0])
    if a.cmd == "strip":
        return strip(st)
    if len(a.args) < 2 or not a.name: sys.exit('usage: commons.py get <story> "File:Name.jpg" --as name.jpg --yes')
    if not a.yes: sys.exit("downloads need the user's explicit yes: list the files for them first, then pass --yes")
    get(st, a.args[1], a.name, a.width, a.rotate)


if __name__ == "__main__":
    main()
