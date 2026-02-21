# Building the APK

The app uses the Android SDK at `/usr/lib/android-sdk`. Builds fail until SDK licenses are accepted.

## 1. Accept SDK licenses (one-time)

You need `sdkmanager` from the Android command-line tools.

**Option A – Install command-line tools (if not already):**

```bash
sudo apt install -y google-android-cmdline-tools-13.0-installer
```

When asked **“Mirror to download packages?”** type **`1`** and Enter (for https://dl.google.com). Wait for the install to finish.

**Option B – If you use Android Studio:** open SDK Manager, install “Android SDK Platform 33” and “Android SDK Build-Tools 34”, and accept the licenses in the UI.

**Then accept all licenses:**

```bash
export ANDROID_HOME=/usr/lib/android-sdk
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses
```

(If `sdkmanager` is elsewhere, use `find /usr -name sdkmanager` to locate it.)

## 2. Build the release APK

Use JDK 17 (not only JRE) and run Gradle:

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
cd android_app
./gradlew assembleRelease
```

APK output: `app/build/outputs/apk/release/app-release.apk`.

## If you built successfully before

That was likely on a machine where:

- Android Studio had already been run (and accepted licenses), or  
- `sdkmanager --licenses` had been run once, or  
- A different SDK path (e.g. `~/Android/Sdk`) was used with licenses already accepted.

On this system, the SDK is `/usr/lib/android-sdk` and its licenses must be accepted once as above.
