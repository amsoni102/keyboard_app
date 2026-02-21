#!/bin/bash
# Install Android SDK license files so Gradle can use the SDK (e.g. /usr/lib/android-sdk).
# Run once: sudo ./install-licenses-sudo.sh
# Then build: export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 && ./gradlew assembleRelease

set -e
SDK="${ANDROID_HOME:-/usr/lib/android-sdk}"
if [ ! -d "$SDK" ]; then
  echo "SDK not found: $SDK. Set ANDROID_HOME or edit this script."
  exit 1
fi
LIC="$SDK/licenses"
mkdir -p "$LIC"
# Add preview license (Gradle often checks this); keep existing android-sdk-license
if [ ! -f "$LIC/android-sdk-preview-license" ]; then
  echo -e "\n84831b9409646a918e30573bab4c9c91346d8a9c" > "$LIC/android-sdk-preview-license"
  echo "Added $LIC/android-sdk-preview-license"
fi
echo "Licenses in $LIC"
echo "Run: export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 && ./gradlew assembleRelease"
