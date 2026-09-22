#!/usr/bin/env python3
"""Email one ai-catchup note, with a cost and token footer.

Two ways to call it:

  send_email.py --result <run.json> [--exit-code N] [--stderr <file>]
      After run.sh. Parses the print-mode JSON envelope, emails the note it
      names (or a failure report), and appends a row to runs.csv.

  send_email.py --note <note.md> [--preview out.html]
      Manual test. Emails an existing note with no cost stats, or writes the
      HTML to a file instead of sending when --preview is given.

Credentials, recipient and logs live in ~/.config/ai-catchup/. Nothing
user-specific is read from or written to the skill directory.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import html
import json
import os
import re
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import markdown
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CONFIG = Path.home() / ".config" / "ai-catchup"
CLIENT_FILE = CONFIG / "oauth_client.json"
TOKEN_FILE = CONFIG / "token.json"
CONFIG_FILE = CONFIG / "config.json"
LOG_FILE = CONFIG / "runs.csv"

# gmail.send can only send. It cannot read, search or delete mail, so a leaked
# token is bounded to "someone can send email as me". userinfo.email is used
# once, by authorize.py, to learn the recipient address.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

LOG_FIELDS = ["date", "time", "status", "slug", "cost_usd", "input_tokens",
              "output_tokens", "cache_creation_tokens", "cache_read_tokens",
              "turns", "duration_s", "note"]

FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)

CSS = """
body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:16px;line-height:1.5;
color:#1d1d1f;max-width:720px;margin:0 auto;padding:16px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:28px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}
pre{background:#f4f4f6;padding:12px;border-radius:6px;overflow-x:auto;font-size:13px;line-height:1.4}
code{font-family:Menlo,Consolas,monospace;font-size:13px;background:#f4f4f6;padding:1px 4px;border-radius:3px}
pre code{background:none;padding:0}
table{border-collapse:collapse;font-size:14px;margin:8px 0}th,td{border:1px solid #ddd;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#f4f4f6}
.meta{color:#6e6e73;font-size:14px;margin-bottom:20px}
.footer{margin-top:36px;padding-top:12px;border-top:2px solid #ddd;color:#6e6e73;font-size:13px}
.footer table{font-size:13px}
"""


# --- auth -----------------------------------------------------------------

def get_credentials(*, interactive: bool = False) -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif interactive:
        from google_auth_oauthlib.flow import InstalledAppFlow
        if not CLIENT_FILE.exists():
            raise SystemExit(
                f"Missing {CLIENT_FILE}. Copy an OAuth desktop-client JSON there.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
    else:
        raise SystemExit("No valid token. Run scripts/authorize.py from a terminal.")
    CONFIG.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
    os.chmod(TOKEN_FILE, 0o600)
    return creds


def gmail(creds: Credentials | None = None):
    return build("gmail", "v1", credentials=creds or get_credentials(),
                 cache_discovery=False)


def recipient() -> str:
    try:
        return json.loads(CONFIG_FILE.read_text())["to"]
    except (OSError, KeyError, ValueError):
        raise SystemExit(f"No recipient in {CONFIG_FILE}. Run scripts/authorize.py.")


# --- note rendering -------------------------------------------------------

def split_note(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, markdown body)."""
    meta: dict[str, str] = {}
    m = FRONT.match(text)
    if m:
        for line in m.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta[key.strip()] = value.strip()
        text = text[m.end():]
    return meta, text


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def fmt(value) -> str:
    if value is None:
        return "?"
    if isinstance(value, float):
        return f"${value:.2f}" if value < 1000 else f"{value:,.0f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def stats_table(stats: dict | None, models: dict | None) -> str:
    if not stats:
        return "<p>No run stats (manual send).</p>"
    rows = [
        ("Cost, list price", f"${stats['cost_usd']:.2f}" if stats.get("cost_usd") is not None else "?"),
        ("Input tokens", fmt(stats.get("input_tokens"))),
        ("Output tokens", fmt(stats.get("output_tokens"))),
        ("Cache written", fmt(stats.get("cache_creation_tokens"))),
        ("Cache read", fmt(stats.get("cache_read_tokens"))),
        ("Turns", fmt(stats.get("turns"))),
        ("Duration", f"{stats.get('duration_s', 0) // 60}m {stats.get('duration_s', 0) % 60}s"),
    ]
    for name, m in (models or {}).items():
        rows.append((f"Model {name}", f"${m.get('costUSD', 0):.2f}, "
                     f"{m.get('inputTokens', 0):,} in / {m.get('outputTokens', 0):,} out"))
    return "<table>" + "".join(
        f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows) + "</table>"


def render_html(note_md: str, meta: dict, footer_rows: list[tuple[str, str]],
                stats: dict | None, models: dict | None) -> str:
    body = markdown.markdown(note_md, extensions=["tables", "fenced_code", "sane_lists"])
    meta_line = " · ".join(
        f"{esc(k)}: {esc(v)}" for k, v in meta.items() if k not in ("topic", "slug"))
    footer = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in footer_rows)
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<style>{CSS}</style></head><body>"
            f"<div class='meta'>{meta_line}</div>{body}"
            f"<div class='footer'><h2>Run</h2><table>{footer}</table>"
            f"<h2>Cost and tokens</h2>{stats_table(stats, models)}</div></body></html>")


# --- envelope parsing -----------------------------------------------------

def reply_json(text: str) -> dict | None:
    """The skill promises one JSON object as its whole reply; tolerate prose."""
    for m in reversed(list(re.finditer(r"\{[^{}]*\}", text, re.S))):
        try:
            data = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(data, dict) and "status" in data:
            return data
    return None


def stats_from(env: dict) -> dict:
    usage = env.get("usage") or {}
    return {
        "cost_usd": env.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "cache_creation_tokens": usage.get("cache_creation_input_tokens"),
        "cache_read_tokens": usage.get("cache_read_input_tokens"),
        "turns": env.get("num_turns"),
        "duration_s": round((env.get("duration_ms") or 0) / 1000),
    }


# --- send and log ---------------------------------------------------------

def send(subject: str, text: str, html_body: str | None) -> str:
    to = recipient()
    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["From"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(text, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = gmail().users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]


def log_run(status: str, slug: str, stats: dict | None, note: str) -> None:
    now = dt.datetime.now()
    row = {"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"),
           "status": status, "slug": slug, "note": note, **(stats or {})}
    new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def tail(path: str | None, n: int = 40) -> str:
    if not path or not Path(path).exists():
        return ""
    lines = Path(path).read_text(errors="replace").splitlines()
    return "\n".join(lines[-n:])


# --- main -----------------------------------------------------------------

def handle_result(args: argparse.Namespace) -> int:
    stats, models, reply, env = None, None, None, {}
    try:
        env = json.loads(Path(args.result).read_text())
        stats = stats_from(env)
        models = env.get("modelUsage")
        reply = reply_json(env.get("result") or "")
    except (OSError, ValueError) as exc:
        env = {"result": f"could not read envelope: {exc}"}

    failed = args.exit_code != 0 or env.get("is_error") or reply is None
    if failed:
        text = (f"ai-catchup --auto failed.\n\nexit code: {args.exit_code}\n"
                f"subtype: {env.get('subtype')}\n\n--- reply ---\n"
                f"{(env.get('result') or '')[:4000]}\n\n--- stderr ---\n{tail(args.stderr)}")
        subject = f"AI catch-up FAILED (exit {args.exit_code})"
        send(subject, text, None)
        log_run("failed", "", stats, "")
        print(subject)
        return 1

    if reply.get("status") == "nothing-new":
        window = reply.get("window", "?")
        text = f"Nothing new in the window {window} and no backlog to draw from."
        send(f"AI catch-up: nothing new ({window})", text,
             render_html(f"<p>{esc(text)}</p>", {}, [("window", window)], stats, models))
        log_run("nothing-new", "", stats, "")
        print("nothing new")
        return 0

    note_path = Path(reply.get("note", ""))
    if not note_path.is_file():
        send("AI catch-up FAILED (note missing)",
             f"Reply named a note that does not exist: {note_path}\n\n{env.get('result')}", None)
        log_run("failed", reply.get("slug", ""), stats, str(note_path))
        return 1

    meta, body = split_note(note_path.read_text())
    topic = meta.get("topic") or reply.get("topic") or reply.get("slug") or note_path.stem
    footer = [("note", str(note_path)),
              ("picked from", reply.get("picked_from", "?")),
              ("window", reply.get("window", "?")),
              ("candidates", str(reply.get("candidates", "?")))]
    subject = f"AI catch-up: {topic}"
    plain = body + "\n\n---\n" + "\n".join(f"{k}: {v}" for k, v in footer) + \
        "\n" + json.dumps(stats)
    send(subject, plain, render_html(body, meta, footer, stats, models))
    log_run("ok", reply.get("slug", ""), stats, str(note_path))
    print(subject)
    return 0


def handle_note(args: argparse.Namespace) -> int:
    note_path = Path(args.note).expanduser()
    meta, body = split_note(note_path.read_text())
    topic = meta.get("topic") or note_path.stem
    html_body = render_html(body, meta, [("note", str(note_path)), ("mode", "manual test")],
                            None, None)
    if args.preview:
        Path(args.preview).write_text(html_body)
        print(f"wrote {args.preview}")
        return 0
    send(f"AI catch-up (test): {topic}", body, html_body)
    print(f"sent test email: {topic}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--result", help="print-mode JSON envelope from run.sh")
    src.add_argument("--note", help="an existing note to email (manual test)")
    ap.add_argument("--exit-code", type=int, default=0)
    ap.add_argument("--stderr", help="stderr file from the claude run, quoted on failure")
    ap.add_argument("--preview", help="with --note: write HTML here instead of sending")
    args = ap.parse_args()
    return handle_result(args) if args.result else handle_note(args)


if __name__ == "__main__":
    sys.exit(main())
