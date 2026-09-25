#!/usr/bin/env python3
"""Validate a multishot brief against the Kling 3.0 Custom limits.

Usage: shotcheck.py <brief.md> [--total 15] [--max-chars 560] [--chip-cost 50]

Reads "### Shot N, S s, Elements: a, b" headings and the fenced block that
follows each one. Prints one line per check and exits 1 if any check fails.
Warnings (words per second, tight budget) do not fail the run.
"""
import argparse
import re
import sys

HEADING = re.compile(
    r"^###\s*Shot\s+(\d+)\s*,\s*(\d+(?:\.\d+)?)\s*s\s*(?:,\s*Elements?:\s*(.*))?$",
    re.IGNORECASE,
)
CHIP = re.compile(r"@\[([a-z0-9_-]+)\]\([0-9a-f-]{36}\)|@([a-z0-9_-]+)", re.IGNORECASE)
SPEAKER = re.compile(r"\[([a-z0-9_-]+)\s*,\s*([^\]]*)\]\s*:", re.IGNORECASE)
FINGERS = re.compile(
    r"\b(finger|fingers|holds up|hold up|counts? on|counting)\b", re.IGNORECASE
)
LINE = re.compile(r'"([^"]+)"')


def parse(path):
    text = open(path, encoding="utf-8").read().splitlines()
    shots = []
    i = 0
    while i < len(text):
        m = HEADING.match(text[i].strip())
        if not m:
            i += 1
            continue
        num, secs, elems = int(m.group(1)), float(m.group(2)), m.group(3) or ""
        elems = [e.strip().lower() for e in elems.split(",") if e.strip()]
        body = []
        j = i + 1
        while j < len(text) and not text[j].startswith("```"):
            j += 1
        j += 1
        while j < len(text) and not text[j].startswith("```"):
            body.append(text[j])
            j += 1
        shots.append({"n": num, "secs": secs, "elems": elems, "text": "\n".join(body).strip()})
        i = j + 1
    return shots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("--total", type=float, default=15.0)
    ap.add_argument("--max-chars", type=int, default=560)
    ap.add_argument("--chip-cost", type=int, default=50)
    ap.add_argument("--min-secs", type=float, default=3.0)
    ap.add_argument("--max-shots", type=int, default=5)
    ap.add_argument("--max-wps", type=float, default=3.0)
    a = ap.parse_args()

    shots = parse(a.brief)
    fails, warns = [], []
    if not shots:
        print("FAIL no '### Shot N, S s, Elements: ...' headings found")
        sys.exit(1)

    total = sum(s["secs"] for s in shots)
    if len(shots) > a.max_shots:
        fails.append(f"{len(shots)} shots, limit {a.max_shots}")
    if abs(total - a.total) > 1e-6:
        fails.append(f"durations sum to {total:g} s, expected {a.total:g} s")

    voices = {}
    for s in shots:
        tag = f"shot {s['n']}"
        if s["secs"] < a.min_secs:
            fails.append(f"{tag}: {s['secs']:g} s is below the {a.min_secs:g} s minimum")
        if not s["text"]:
            fails.append(f"{tag}: empty text")
            continue

        chips = [(m.group(1) or m.group(2)).lower() for m in CHIP.finditer(s["text"])]
        visible = CHIP.sub(lambda m: "@" + (m.group(1) or m.group(2)), s["text"])
        stored = len(visible) + a.chip_cost * len(chips)
        if stored > a.max_chars:
            fails.append(f"{tag}: {stored} stored chars (limit {a.max_chars}), text will truncate")
        elif stored > a.max_chars - 60:
            warns.append(f"{tag}: {stored} stored chars, within 60 of the limit")

        for c in set(chips):
            if chips.count(c) > 1:
                fails.append(f"{tag}: @{c} tagged {chips.count(c)} times, tag once per shot")
            if s["elems"] and c not in s["elems"]:
                fails.append(f"{tag}: @{c} tagged but not in the Elements list ({', '.join(s['elems'])})")
        for e in s["elems"]:
            if e not in chips:
                fails.append(f"{tag}: Element {e} listed but never tagged in the text")

        for m in SPEAKER.finditer(s["text"]):
            who, rest = m.group(1).lower(), m.group(2).strip()
            if who == "both":
                continue
            if who not in s["elems"] and s["elems"]:
                fails.append(f"{tag}: speaker '{who}' is not an Element in this shot")
            voice = rest.split(",")[0].strip().lower()
            voices.setdefault(who, set()).add(voice)

        if FINGERS.search(s["text"]):
            fails.append(f"{tag}: finger counting or hand-count gesture found; remove it")

        words = sum(len(l.split()) for l in LINE.findall(s["text"]))
        wps = words / s["secs"] if s["secs"] else 0
        if wps > a.max_wps:
            warns.append(f"{tag}: {words} spoken words in {s['secs']:g} s ({wps:.1f} w/s), lines may drop")
        lines = len(SPEAKER.findall(s["text"]))
        if lines >= 3 and s["secs"] <= 3:
            warns.append(f"{tag}: {lines} spoken lines in {s['secs']:g} s, a line will likely vanish")
        if len(set(chips)) >= 2 and lines > 0:
            fails.append(f"{tag}: {len(set(chips))} Elements share the frame and someone speaks; shared frames must be silent")

    for who, vs in voices.items():
        if len(vs) > 1:
            fails.append(f"voice tag for {who} varies across shots: {sorted(vs)}")

    print(f"shots={len(shots)} total={total:g}s")
    for s in shots:
        chips = len(CHIP.findall(s["text"]))
        vis = len(CHIP.sub(lambda m: "@" + (m.group(1) or m.group(2)), s["text"]))
        print(f"  shot {s['n']}: {s['secs']:g}s chips={chips} stored={vis + a.chip_cost * chips}")
    for w in warns:
        print("WARN", w)
    for f in fails:
        print("FAIL", f)
    if not fails:
        print("OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
