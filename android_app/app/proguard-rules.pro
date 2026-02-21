# Keep app and entry points
-keep class org.example.keyboardmouse.** { *; }
# Keep Bluetooth classes used by reflection
-keep class android.bluetooth.** { *; }
-dontwarn android.bluetooth.**
