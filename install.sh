#!/bin/bash

# Configs
REPO_ROOT="$(dirname "$0")"
SRC_SCRIPT="$REPO_ROOT/src/sync_engine.py"
INSTALL_DIR="$HOME/scripts/chromium-sync" 
TARGET_SCRIPT="$INSTALL_DIR/sync_engine.py"

PLIST_NAME="com.user.browsersync.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_OUT="/tmp/sync_browsers.log"
LOG_ERR="/tmp/sync_browsers.err"

echo "📦 Installing Chromium Sync Tool..."

# 1. Instalação do Script
if [ ! -f "$SRC_SCRIPT" ]; then
    echo "❌ Error: Source script not found at $SRC_SCRIPT"
    exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$SRC_SCRIPT" "$TARGET_SCRIPT"
chmod +x "$TARGET_SCRIPT"
echo "✅ Core engine installed to: $TARGET_SCRIPT"

# 2. Criação do LaunchAgent 
cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.browsersync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$TARGET_SCRIPT</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>$LOG_OUT</string>
    <key>StandardErrorPath</key>
    <string>$LOG_ERR</string>
</dict>
</plist>
EOF

# 3. Ativar o Serviço
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "🚀 Service loaded successfully!"
echo "   - Log: $LOG_OUT"
