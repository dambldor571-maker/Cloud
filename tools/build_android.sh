#!/usr/bin/env bash
# Builds a debug-signed APK into build/frontline.apk.
# DEBUG_KEYSTORE overrides the signing key (CI uses tools/debug.keystore so
# every build can be installed over the previous one).
# Needs: GODOT (path to the Godot 4.3 binary), ANDROID_SDK_ROOT (with build-tools),
# Godot 4.3 export templates installed, and keytool (JDK 17) on PATH.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${GODOT:?set GODOT to the Godot 4.3 binary}"
: "${ANDROID_SDK_ROOT:?set ANDROID_SDK_ROOT to the Android SDK}"

KEYSTORE="${DEBUG_KEYSTORE:-$HOME/.android/debug.keystore}"
if [ ! -f "$KEYSTORE" ]; then
  mkdir -p "$(dirname "$KEYSTORE")"
  keytool -genkeypair -v -keystore "$KEYSTORE" -storepass android -alias androiddebugkey \
    -keypass android -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US" >/dev/null
fi
KEYSTORE="$(realpath "$KEYSTORE")"

# Godot reads the SDK path from editor settings; the keystore from env vars.
SETTINGS_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/godot"
mkdir -p "$SETTINGS_DIR"
cat > "$SETTINGS_DIR/editor_settings-4.3.tres" <<TRES
[gd_resource type="EditorSettings" format=3]

[resource]
export/android/android_sdk_path = "$ANDROID_SDK_ROOT"
export/android/debug_keystore = "$KEYSTORE"
export/android/debug_keystore_user = "androiddebugkey"
export/android/debug_keystore_pass = "android"
TRES
export GODOT_ANDROID_KEYSTORE_DEBUG_PATH="$KEYSTORE"
export GODOT_ANDROID_KEYSTORE_DEBUG_USER="androiddebugkey"
export GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD="android"

mkdir -p build
"$GODOT" --headless --path . --import >/dev/null 2>&1 || true
"$GODOT" --headless --path . --export-debug "Android" build/frontline.apk
test -s build/frontline.apk
echo "APK: build/frontline.apk ($(du -h build/frontline.apk | cut -f1))"
