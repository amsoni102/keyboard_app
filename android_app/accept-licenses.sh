#!/bin/bash
# Accept Android SDK licenses so Gradle can download/use platform and build-tools.
# Run once: ./accept-licenses.sh

set -e
SDK="${ANDROID_HOME:-$(grep -E '^sdk\.dir=' local.properties 2>/dev/null | cut -d= -f2)}"
if [ -z "$SDK" ] || [ ! -d "$SDK" ]; then
  echo "ANDROID_HOME not set or sdk.dir in local.properties not found."
  echo "Set ANDROID_HOME to your Android SDK path, e.g.: export ANDROID_HOME=/usr/lib/android-sdk"
  exit 1
fi

# Prefer cmdline-tools sdkmanager (often in cmdline-tools/latest/bin or tools/bin)
SM=""
for p in "$SDK/cmdline-tools/latest/bin/sdkmanager" "$SDK/tools/bin/sdkmanager" "$SDK/bin/sdkmanager"; do
  if [ -x "$p" ]; then SM="$p"; break; fi
done
if [ -z "$SM" ]; then
  echo "sdkmanager not found in $SDK"
  echo "Install Android Studio (which installs the SDK and lets you accept licenses in the UI),"
  echo "or install command-line tools, e.g.: sudo apt install -y google-android-cmdline-tools-13.0-installer"
  echo "During installer, choose mirror 1 (dl.google.com) if asked."
  exit 1
fi

echo "Accepting licenses with: $SM"
yes | "$SM" --licenses
echo "Done. Run: ./gradlew assembleRelease"
exit 0
