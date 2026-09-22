#!/usr/bin/env python3
"""One-time OAuth authorization for the ai-catchup mailer. Safe to re-run.

Requests gmail.send plus userinfo.email, stores the token at
~/.config/ai-catchup/token.json (mode 600) and writes the signed-in address
to ~/.config/ai-catchup/config.json as the recipient.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Google returns only the scopes the user ticked on the consent screen. Accept
# that instead of crashing, then check below that gmail.send was among them.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

sys.path.insert(0, str(Path(__file__).parent))
from send_email import CONFIG_FILE, TOKEN_FILE, get_credentials  # noqa: E402

SEND = "https://www.googleapis.com/auth/gmail.send"
from googleapiclient.discovery import build  # noqa: E402


def main() -> None:
    if not TOKEN_FILE.exists():
        print("Opening browser for authorization...")
        print('Expect a "Google hasn\'t verified this app" screen.')
        print('Click Advanced -> "Go to <app name> (unsafe)". It is your own app.\n')

    creds = get_credentials(interactive=True)
    granted = set(getattr(creds, "granted_scopes", None) or creds.scopes or [])
    if SEND not in granted:
        TOKEN_FILE.unlink(missing_ok=True)
        raise SystemExit(
            "\nGoogle granted only: " + ", ".join(sorted(granted)) +
            "\nThe 'Send email on your behalf' box on the consent screen was not"
            " ticked, so no token was saved.\nRun this again and tick every box"
            " before clicking Continue.")
    info = build("oauth2", "v2", credentials=creds, cache_discovery=False).userinfo().get().execute()
    email = info["email"]

    existing = {}
    if CONFIG_FILE.exists():
        existing = json.loads(CONFIG_FILE.read_text())
    existing.setdefault("to", email)
    CONFIG_FILE.write_text(json.dumps(existing, indent=2) + "\n")

    print("\n--- Connected ---")
    print(f"Account   : {email}")
    print(f"Sends to  : {existing['to']}  (edit {CONFIG_FILE} to change)")
    print(f"Scopes    : {', '.join(creds.scopes or [])}")
    print(f"Token     : {TOKEN_FILE} (mode 600)")


if __name__ == "__main__":
    main()
