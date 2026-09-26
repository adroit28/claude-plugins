#!/usr/bin/env python3
"""Claude cost of this session so far, and of the step just finished, at API list prices.

  cost.py --step "research: cards" [--slug <slug>] [--session <id or transcript.jsonl>] [--no-log]

Reads the Claude Code transcript of the current session (CLAUDE_CODE_SESSION_ID, found under
~/.claude/projects/*/) plus its subagent transcripts (<session>/subagents/*.jsonl). Tokens are
counted once per API message: input, output, cache writes (5-minute and 1-hour) and cache reads,
each at its own rate from PRICES. Web searches are counted from WebSearch tool calls at
$10 per 1,000 (an estimate). WebFetch page summaries run on a small model that the transcript
does not record, so they are counted but not priced.

Each run appends a record to <shorts>/cost_log.jsonl. "This step" is the difference from the
previous record of the same session. "This video" adds up every step logged under --slug,
plus earlier steps in the same sessions that had no slug yet (research before the pick).
Stdlib only.

These are list-price equivalents. On a Claude subscription, usage counts against the plan's
limits instead of being billed per token. Set FOOTBALL_STORIES_INR_RATE (₹ per $) to change
the rupee conversion.
"""
import argparse, datetime as dt, glob, json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import shorts_dir

# $ per million tokens: input, output, 5-minute cache write, 1-hour cache write, cache read.
# List prices as of 2026-09. The longest matching model-id prefix wins; edit here when prices change.
PRICES = {
    "claude-opus-5-5":  (4.0, 20.0, 5.0, 8.0, 0.20),
    "claude-opus-5":    (5.0, 25.0, 6.25, 10.0, 0.50),
    "claude-sonnet-5":  (2.0, 10.0, 2.5, 4.0, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 2.0, 0.10),
    "claude-fable-5-1": (10.0, 50.0, 12.5, 20.0, 0.25),
    "claude-fable-5":   (10.0, 50.0, 12.5, 20.0, 1.00),
}
WEB_SEARCH = 0.01
INR = float(os.environ.get("FOOTBALL_STORIES_INR_RATE", "88"))
FIELDS = ("input", "output", "write_5m", "write_1h", "read")


def transcripts(session):
    if session and session.endswith(".jsonl"):
        main = pathlib.Path(session).expanduser()
    else:
        sid = session or os.environ.get("CLAUDE_CODE_SESSION_ID")
        if not sid:
            sys.exit("no session id: pass --session <id or transcript.jsonl>")
        hits = glob.glob(os.path.expanduser("~/.claude/projects/*/%s.jsonl" % sid))
        if not hits:
            sys.exit("transcript for session %s not found under ~/.claude/projects" % sid)
        main = pathlib.Path(hits[0])
    return main.stem, [main] + sorted((main.parent / main.stem / "subagents").glob("*.jsonl"))


def price(model):
    keys = [k for k in PRICES if model.startswith(k)]
    return PRICES[max(keys, key=len)] if keys else None


def tally(files):
    """{model: {field: tokens}} with each API message counted once, plus tool-call counts."""
    msgs, tools = {}, {}
    for f in files:
        for ln in f.open(errors="replace"):
            try: d = json.loads(ln)
            except ValueError: continue
            m = d.get("message") if isinstance(d.get("message"), dict) else None
            if not m or m.get("role") != "assistant": continue
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    tools[b.get("id")] = b.get("name")
            u, model, mid = m.get("usage"), m.get("model", ""), m.get("id")
            if not u or not mid or model.startswith("<"): continue
            cc = u.get("cache_creation") or {}
            w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
            w5m = cc.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - w1h) or 0
            row = {"input": u.get("input_tokens", 0) or 0, "output": u.get("output_tokens", 0) or 0,
                   "write_5m": w5m, "write_1h": w1h, "read": u.get("cache_read_input_tokens", 0) or 0}
            old = msgs.get(mid, (model, {}))[1]   # one message is logged once per content block: keep the max
            msgs[mid] = (model, {k: max(row[k], old.get(k, 0)) for k in FIELDS})
    by_model = {}
    for model, row in msgs.values():
        acc = by_model.setdefault(model, dict.fromkeys(FIELDS, 0))
        for k in FIELDS: acc[k] += row[k]
    names = list(tools.values())
    return by_model, {"WebSearch": names.count("WebSearch"), "WebFetch": names.count("WebFetch")}


def dollars(by_model, tools):
    out, unknown = {}, []
    for model, t in by_model.items():
        p = price(model)
        if not p: unknown.append(model); continue
        out[model] = sum(t[k] * p[i] for i, k in enumerate(FIELDS)) / 1e6
    out["web searches"] = tools["WebSearch"] * WEB_SEARCH
    return out, unknown


def fmt(d):
    total = sum(d.values())
    parts = ", ".join("%s $%.2f" % (k.replace("claude-", ""), v) for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if v >= 0.005)
    return "$%.2f (≈₹%.0f)%s" % (total, total * INR, "  [" + parts + "]" if parts else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", default="checkpoint"); ap.add_argument("--slug"); ap.add_argument("--session")
    ap.add_argument("--no-log", action="store_true", help="print only, don't append to cost_log.jsonl")
    a = ap.parse_args()
    sid, files = transcripts(a.session)
    by_model, tools = tally(files)
    now, unknown = dollars(by_model, tools)

    log = shorts_dir() / "cost_log.jsonl"
    past = [json.loads(l) for l in log.read_text().splitlines() if l.strip()] if log.exists() else []
    prev = next((r for r in reversed(past) if r["session"] == sid), None)
    step = {k: v - (prev or {}).get("cost", {}).get(k, 0) for k, v in now.items()}
    rec = {"at": dt.datetime.now().isoformat(timespec="seconds"), "session": sid, "step": a.step, "slug": a.slug,
           "cost": {k: round(v, 4) for k, v in now.items()}, "step_cost": round(sum(step.values()), 4),
           "tokens": by_model, "tools": tools}
    if not a.no_log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as fh: fh.write(json.dumps(rec) + "\n")

    print("Claude cost at API list prices, after: %s" % a.step)
    print("  this step     %s" % fmt(step))
    print("  this session  %s" % fmt(now))
    if a.slug:
        rows = past + [rec]
        sessions = {r["session"] for r in rows if r.get("slug") == a.slug}
        video = sum(r["step_cost"] for r in rows if r.get("slug") == a.slug or (r["session"] in sessions and not r.get("slug")))
        print("  this video    $%.2f (≈₹%.0f), %d session(s)" % (video, video * INR, len(sessions)))
    for model, t in sorted(by_model.items()):
        print("  tokens %-18s in %s · out %s · cache write %s · cache read %s" % (model, "{:,}".format(t["input"]),
              "{:,}".format(t["output"]), "{:,}".format(t["write_5m"] + t["write_1h"]), "{:,}".format(t["read"])))
    print("  %d web searches priced at $10/1,000 (estimate); %d page reads not priced (small-model summaries)"
          % (tools["WebSearch"], tools["WebFetch"]))
    if unknown: print("  warn: no price for %s: add it to PRICES in cost.py" % ", ".join(unknown))
    top = max(by_model.items(), key=lambda kv: kv[1]["read"], default=None)
    if top and price(top[0]) and top[1]["read"] * price(top[0])[4] / 1e6 > 0.4 * max(now.get(top[0], 0), 1e-9):
        print("  note: most of %s's cost is re-reading the conversation; a fresh session for the next step is cheaper" % top[0])
    print("  (list-price equivalent: on a Claude subscription this counts against plan limits instead;"
          " ₹ at %g/$, set FOOTBALL_STORIES_INR_RATE)" % INR)


if __name__ == "__main__":
    main()
