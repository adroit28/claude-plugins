#!/usr/bin/env python3
"""The topic ledger (<content root>/IDEAS.md): every topic ever pitched, picked, made or rejected, so none repeats.

  ideas.py list [--status pitched]                    the table (default: all rows)
  ideas.py taken                                      titles and slugs to skip when suggesting (one per line)
  ideas.py coverage                                   made/picked count per category (balance the test set)
  ideas.py add "Why 13 is unlucky" --category superstitions --hook "..." [--status pitched] [--slug thirteen]
  ideas.py set <slug or title words> --status picked|made|rejected [--slug s] [--note "..."]

IDEAS.md is a markdown table (status · slug · title · category · hook · date · note) that the user
can also edit by hand; this script keeps it sorted by status and refuses a title that is already in
it (case and punctuation ignored, or the same slug). Stdlib only.
"""
import argparse, datetime as dt, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import channel, content_dir

COLS = ["status", "slug", "title", "category", "hook", "date", "note"]
ORDER = {"made": 0, "picked": 1, "pitched": 2, "rejected": 3}
HEAD = ("# Topic ledger\n\nEvery topic pitched, picked, made or rejected. The ideas skill skips anything in this table.\n"
        "Status: made (published or rendered) · picked (in progress) · pitched (suggested, still free) · rejected (don't pitch again).\n\n")
key = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def path():
    return content_dir() / "IDEAS.md"


def load():
    p = path()
    if not p.exists(): return []
    rows = []
    for ln in p.read_text().splitlines():
        if not ln.startswith("|") or set(ln.replace("|", "").strip()) <= set("-: "): continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells[0].lower() == "status": continue
        rows.append(dict(zip(COLS, cells + [""] * (len(COLS) - len(cells)))))
    return rows


def save(rows):
    rows.sort(key=lambda r: (ORDER.get(r["status"], 9), r["date"]))
    esc = lambda v: (v or "").replace("|", "/").replace("\n", " ")
    t = "| " + " | ".join(COLS) + " |\n|" + "---|" * len(COLS) + "\n"
    t += "".join("| " + " | ".join(esc(r.get(c, "")) for c in COLS) + " |\n" for r in rows)
    path().parent.mkdir(parents=True, exist_ok=True)
    path().write_text(HEAD + t)


def find(rows, q):
    hits = [r for r in rows if r["slug"] == q] or [r for r in rows if key(q) in key(r["title"])]
    if len(hits) != 1: sys.exit("%d rows match %r: use the slug" % (len(hits), q))
    return hits[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "taken", "coverage", "add", "set"]); ap.add_argument("text", nargs="?")
    ap.add_argument("--status"); ap.add_argument("--slug", default=""); ap.add_argument("--category", default="")
    ap.add_argument("--hook", default=""); ap.add_argument("--note")
    a = ap.parse_args(); rows = load()
    if a.cmd == "list":
        for r in rows:
            if not a.status or r["status"] == a.status:
                print("%-8s %-22s %-48s %-16s %s" % (r["status"], r["slug"], r["title"][:48], r["category"], r["date"]))
        print("(%d rows in %s)" % (len(rows), path()))
    elif a.cmd == "taken":
        for r in rows: print("%s · %s · %s" % (r["status"], r["slug"] or "-", r["title"]))
    elif a.cmd == "coverage":
        cats = channel()["categories"]
        for c in cats + sorted({r["category"] for r in rows} - set(cats)):
            n = [r for r in rows if r["category"] == c and r["status"] in ("made", "picked")]
            print("%-18s %d  %s" % (c, len(n), ", ".join(r["slug"] or r["title"] for r in n)))
    elif a.cmd == "add":
        if not a.text: sys.exit("title required")
        for r in rows:
            if key(r["title"]) == key(a.text) or (a.slug and r["slug"] == a.slug):
                sys.exit("already in the ledger (%s): %s" % (r["status"], r["title"]))
        rows.append({"status": a.status or "pitched", "slug": a.slug, "title": a.text, "category": a.category, "hook": a.hook,
                     "date": dt.date.today().isoformat(), "note": a.note or ""})
        save(rows); print("added: %s" % a.text)
    elif a.cmd == "set":
        r = find(rows, a.text or "")
        if a.status: r["status"] = a.status
        if a.slug: r["slug"] = a.slug
        if a.note is not None: r["note"] = a.note
        r["date"] = dt.date.today().isoformat()
        save(rows); print("%s -> %s" % (r["title"], r["status"]))


if __name__ == "__main__":
    main()
