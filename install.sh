#!/data/data/com.termux/files/usr/bin/bash
# ARPXTOOL · termux installer
set -e
echo "→ installing dependencies"
pkg update -y >/dev/null 2>&1 || true
pkg install -y python openjdk-17 >/dev/null 2>&1 || true

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin"

cat > "$BIN/arpxtool" <<LAUNCH
#!/bin/sh
exec python3 "$HERE/arpxtool_pro.py" "\$@"
LAUNCH
chmod +x "$BIN/arpxtool"

echo "→ self check"
python3 "$HERE/arpxtool_pro.py" --self-check | tail -3
echo "✓ done · run: arpxtool -i app.apk"
