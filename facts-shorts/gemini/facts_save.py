#!/usr/bin/env python3
"""Clipboard text from the Gemini app -> verify.md or story.v1.json (called by facts.sh save).

  pbpaste | facts_save.py verify|quick|story <slug folder> <slug>
"""
import concurrent.futures as cf, json, os, pathlib, re, shutil, sys, urllib.error, urllib.parse, urllib.request

BANNED = ["aakash.ac.in", "byjus.com", "testbook.com", "adda247.com", "vedantu.com", "toppr.com", "shiksha.com",
          "medium.com", "quora.com", "reddit.com", "lookupaplate.com", "brainly"]
SECTIONS = ["## Popular myths", "## Do not use", "## Compact table", "## Images"]


def link(url):
    """'ok', 'dead (404)' or 'unchecked (403)': a GET with a browser user agent, first bytes only."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/126 Safari/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r: r.read(1); return "ok"
    except urllib.error.HTTPError as e:
        return "dead (%d)" % e.code if e.code in (404, 410) else "unchecked (%d)" % e.code
    except urllib.error.URLError as e:
        return "dead (%s)" % e.reason if "nodename" in str(e.reason) or "Name or service" in str(e.reason) else "unchecked (%s)" % e.reason
    except Exception as e:
        return "unchecked (%s)" % type(e).__name__


def audit(md):
    """Red flags from the Gemini-route trial: invented pages, homepages, exam-prep sources, LaTeX, a changed layout."""
    probs, notes = [], []
    if not md.lstrip().startswith("# Verify"): probs.append("title must start with '# Verify:' (layout changed)")
    if re.search(r"^\s*[*-]?\s*\**Status:?\**", md, re.M | re.I): probs.append("uses 'Status:' fields: verdicts belong in the '## N. claim: VERDICT' heading")
    for sec in SECTIONS:
        if sec.lower() not in md.lower(): probs.append("missing section %r" % sec)
    for n in re.findall(r"^##\s+(\d+)\.", md, re.M):
        body = re.split(r"^##\s+%s\..*$" % n, md, flags=re.M)[1].split("\n## ")[0]
        if "Wording" not in body: probs.append("claim %s has no 'Wording:' line" % n)
    if re.search(r"\$[^$\n]{1,80}\$|\\(propto|text|lambda|sigma|approx)", md): probs.append("contains LaTeX/formulas: quotes must be copied text, not maths")
    urls = sorted({u.rstrip(".,;:)]>`'\"") for u in re.findall(r"https?://[^\s<>()\[\]`\"']+", md)})
    for u in urls:
        q = urllib.parse.urlparse(u); host = q.netloc.lower()
        if any(b in host for b in BANNED): probs.append("banned source type: %s" % u)
        segs = [x for x in q.path.split("/") if x]
        articleish = q.query or "/wiki/" in q.path or any(re.search(r"[-_.\d~]", x) for x in segs)
        if not segs or not articleish:
            probs.append("homepage/section page, not an article: %s" % u)
    if not urls: probs.append("no URLs: every source bullet needs the exact page URL")
    if urls and not os.environ.get("FACTS_NOLINKS"):
        print("checking %d links..." % len(urls))
        with cf.ThreadPoolExecutor(8) as ex:
            for u, r in zip(urls, ex.map(link, urls)):
                if r.startswith("dead"): probs.append("page does not exist %s: %s" % (r[5:], u))
                elif r.startswith("unchecked"): notes.append("couldn't check %s %s: open it yourself" % (r[10:], u))
    return probs, notes
kind, d, slug = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
raw = sys.stdin.read().strip()
if not raw: sys.exit("clipboard is empty: use the copy button on Gemini's code block first")
# Whole reply copied? Take the right fenced block; a code-block copy has no fences.
blocks = re.findall(r"^```(\w*)[ \t]*\n(.*?)^```[ \t]*$", raw, re.M | re.S)
if blocks:
    want = ("json",) if kind == "story" else ("markdown", "md", "")   # verify and quick both take the markdown block
    raw = next((b for lang, b in blocks if lang.lower() in want), blocks[0][1]).strip()

if kind == "quick":   # the Quick Script skill's unchecked facts file: same place, no source audit
    if not re.search(r"^##\s+1\.", raw, re.M): sys.exit("this doesn't look like the facts file (no '## 1.' heading): copy Block 2, the markdown one")
    out = d / "verify.md"
    if out.exists(): shutil.copy(out, d / "verify.prev.md"); print("kept the old one as verify.prev.md")
    out.write_text(raw + "\n")
    print("saved %s (%d facts, unchecked: no web research)" % (out, len(re.findall(r"^##\s+\d+\.", raw, re.M))))
    m = re.search(r"^## Check these first\s*\n(.*?)(?=^## |\Z)", raw, re.M | re.S)
    if m: print("\nCheck these on Wikipedia before narrating:\n" + m.group(1).strip())
    sys.exit(0)

if kind == "verify":
    if not re.search(r"^##\s+1\.", raw, re.M): sys.exit("this doesn't look like verify.md (no '## 1.' claim heading): copy the Facts Research skill's code block")
    out = d / "verify.md"
    if out.exists(): shutil.copy(out, d / "verify.prev.md"); print("kept the old one as verify.prev.md")
    out.write_text(raw + "\n")
    n = len(re.findall(r"^##\s+\d+\.", raw, re.M))
    v = len(re.findall(r"^##\s+\d+\..*:\s*VERIFIED", raw, re.M | re.I))
    print("saved %s (%d claims, %d VERIFIED)" % (out, n, v))
    probs, notes = audit(raw)
    for x in notes: print("note:", x)
    for x in probs: print("PROBLEM:", x)
    if probs:
        print("\n%d problem(s). Paste the PROBLEM lines into a NEW Facts Research chat with the brief, or ask Claude to check it." % len(probs))
        sys.exit(2)
    print("no red flags (still open the 'Check these links' list yourself)")
    sys.exit(0)

try:
    data = json.loads(raw)
except ValueError as e:
    sys.exit("not valid JSON (%s): paste this error into the Facts Script skill and ask for the full JSON again" % e)
out = d / "story.v1.json"
if out.exists():
    old = json.loads(out.read_text())
    if old.get("narration", {}).get("audio"):
        sys.exit("%s is already narrated: changes now go through Claude (/facts-shorts:revise), which makes v2" % out)
# Fill the fixed fields so a small slip by Gemini doesn't matter.
data.update({"schema": "facts-story/1.0", "slug": slug, "id": "facts-" + slug, "version": 1, "status": "script"})
data.setdefault("format", "explainer-2d"); data.setdefault("disclosure", "Narration voice is AI-generated.")
data.setdefault("length", {"max": 60}); data.setdefault("narration", {}).setdefault("pace", 1.0)
out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("saved", out)
