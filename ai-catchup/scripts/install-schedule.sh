#!/bin/bash
# Install (or reinstall) the launchd agent that runs run.sh every day at noon.
#   install-schedule.sh            install and load
#   install-schedule.sh --remove   unload and delete
set -eu
LABEL="com.suraj.ai-catchup"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
HERE="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="$HOME/.config/ai-catchup/logs"
UID_="$(id -u)"

if [ "${1:-}" = "--remove" ]; then
  launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed $LABEL"
  exit 0
fi

mkdir -p "$LOGDIR" "$(dirname "$PLIST")"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$HERE/run.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$LOGDIR/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/launchd.err.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>HOME</key><string>$HOME</string></dict>
</dict>
</plist>
EOF

launchctl bootout "gui/$UID_/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID_" "$PLIST"
launchctl enable "gui/$UID_/$LABEL"
echo "installed $LABEL -> runs $HERE/run.sh daily at 12:00"
echo "run now:   launchctl kickstart -k gui/$UID_/$LABEL"
echo "status:    launchctl print gui/$UID_/$LABEL | head -20"
