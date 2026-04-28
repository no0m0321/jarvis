#!/usr/bin/env bash
# Build .app bundle from Swift Package output.
# Usage: ./build.sh
#        ./build.sh install   # also copy to /Applications/
#        ./build.sh launchd   # install + register LaunchAgent

set -e
cd "$(dirname "$0")"

ACTION="${1:-build}"

# 1. Swift Package build
echo "==> swift build (release)"
swift build -c release

# 2. Build .app bundle
APP_DIR="JarvisHUD.app"
echo "==> Assembling $APP_DIR"
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"

cp ".build/release/JarvisHUD" "$APP_DIR/Contents/MacOS/JarvisHUD"
cp "Info.plist" "$APP_DIR/Contents/Info.plist"
echo -n "APPLAPPL" > "$APP_DIR/Contents/PkgInfo"

# 3. Ad-hoc codesign (microphone 권한 부여 위해 필요)
echo "==> Ad-hoc codesign"
codesign --force --deep --sign - --options runtime "$APP_DIR" 2>&1 | tail -3 || true

echo ""
echo "✅ OK: $APP_DIR built"
echo ""

if [ "$ACTION" = "install" ] || [ "$ACTION" = "launchd" ]; then
    echo "==> Installing to /Applications/"
    rm -rf "/Applications/JarvisHUD.app"
    cp -R "$APP_DIR" /Applications/
    echo "✅ Installed: /Applications/JarvisHUD.app"
fi

if [ "$ACTION" = "launchd" ]; then
    PLIST_SRC="com.swxvno.jarvis.hud.plist"
    PLIST_DEST="$HOME/Library/LaunchAgents/com.swxvno.jarvis.hud.plist"
    echo "==> Registering LaunchAgent"
    cp "$PLIST_SRC" "$PLIST_DEST"
    launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
    echo "✅ LaunchAgent loaded — auto-starts on login"
fi

echo ""
echo "다음 단계:"
echo "  open ./$APP_DIR              # 즉시 실행 (테스트)"
echo "  ./build.sh install           # /Applications/ 에 설치"
echo "  ./build.sh launchd           # 설치 + 자동 시작 등록"
