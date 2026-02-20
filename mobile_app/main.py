"""
Keyboard & Mouse Remote - same code runs on desktop (simulate) and Android.
Desktop: run from project root with run_desktop.sh (uses PyBluez for BT).
Android: built with Buildozer; requests BLUETOOTH_CONNECT at runtime.
"""
import sys
import traceback

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.logger import Logger


def _request_bluetooth_permission_android():
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Build = autoclass("android.os.Build")
        if Build.VERSION.SDK_INT < 31:
            return
        activity = PythonActivity.mActivity
        if activity is None:
            return
        Permission = autoclass("android.content.pm.PackageManager")
        perm = "android.permission.BLUETOOTH_CONNECT"
        if activity.checkSelfPermission(perm) == Permission.PERMISSION_GRANTED:
            return
        activity.requestPermissions([perm], 9001)
    except Exception:
        pass  # Not on Android or jnius not available


def _load_ui(dt):
    app = App.get_running_app()
    root = app.root
    if not root or not root.children:
        return
    status_label = root.children[0]
    try:
        import app_ui
        screen = app_ui.ControlScreen()
        root.clear_widgets()
        root.add_widget(screen)
    except Exception as e:
        err = traceback.format_exc()
        Logger.exception("KeyboardMouse: load UI failed")
        status_label.text = "Startup failed:\n\n" + str(e) + "\n\n" + err[:800]


def _delayed_permission(dt):
    _request_bluetooth_permission_android()


class KeyboardMouseApp(App):
    def build(self):
        root = BoxLayout(orientation="vertical", padding=20)
        root.add_widget(Label(text="Starting...", font_size="20sp"))
        return root

    def on_start(self):
        Clock.schedule_once(_load_ui, 0.5)
        Clock.schedule_once(_delayed_permission, 1.5)


def _excepthook(etype, value, tb):
    Logger.critical("KeyboardMouse: %s", "".join(traceback.format_exception(etype, value, tb)))
    sys.__excepthook__(etype, value, tb)


if __name__ == "__main__":
    sys.excepthook = _excepthook
    KeyboardMouseApp().run()
