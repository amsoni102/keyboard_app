[app]
title = Keyboard Mouse Remote
package.name = keyboardmouse
package.domain = org.example
source.dir = .
source.include_exts = py,pyc
version = 0.1
requirements = python3,kivy,pyjnius
orientation = portrait
# Single arch for faster build; use arm64-v8a for most modern phones
android.archs = arm64-v8a
# Local recipe to patch pyjnius for Python 3 (long -> int)
android.local_recipes = recipes
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT
# Target API 33 for "latest privacy protection" (34 can break p4a/NDK)
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33

[buildozer]
log_level = 2
warn_on_root = 1
