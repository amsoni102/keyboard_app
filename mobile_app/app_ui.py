# Full UI: load this after the app window is up to avoid "Loading..." crash.
from protocol import encode_command, CMD_KEY, CMD_MOUSE_CLICK, CMD_SCROLL
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.graphics import Color, Rectangle

from bt_client import get_bt


class TouchPad(BoxLayout):
    last_touch_pos = ObjectProperty(None, allownone=True)
    has_moved = BooleanProperty(False)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        touch.grab(self)
        self.last_touch_pos = (touch.x, touch.y)
        self.has_moved = False
        return True

    def on_touch_move(self, touch):
        if touch.grab_current != self:
            return False
        bt = get_bt()
        if not bt or not hasattr(self.parent, "send") or not self.parent.send:
            return True
        ox, oy = self.last_touch_pos
        dx = int(touch.x - ox)
        dy = int(-(touch.y - oy))
        self.last_touch_pos = (touch.x, touch.y)
        if dx or dy:
            self.has_moved = True
            self.parent.send(encode_command("MOVE", f"{dx},{dy}").strip())
        return True

    def on_touch_up(self, touch):
        if touch.grab_current != self:
            return False
        touch.ungrab(self)
        if not self.has_moved:
            bt = get_bt()
            if bt and hasattr(self.parent, "send") and self.parent.send:
                self.parent.send(encode_command("CLICK", "left").strip())
        return True


class ControlScreen(BoxLayout):
    status = StringProperty("Not connected")
    connected = BooleanProperty(False)
    send = None

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.bt = None

        self.add_widget(Label(size_hint_y=None, height=40, text="Keyboard & Mouse Remote"))
        self.status_label = Label(size_hint_y=None, height=30, text=self.status)
        self.add_widget(self.status_label)
        self.bind(status=self._update_status_label)

        conn_layout = BoxLayout(size_hint_y=None, height=80)
        self.device_spinner = ScrollView(size_hint_x=0.6)
        self.device_list = GridLayout(cols=1, size_hint_y=None, spacing=2)
        self.device_list.bind(minimum_height=self.device_list.setter("height"))
        self.device_spinner.add_widget(self.device_list)
        conn_layout.add_widget(self.device_spinner)
        refresh_btn = Button(text="Refresh", size_hint_x=0.2, on_press=self.refresh_devices)
        conn_layout.add_widget(refresh_btn)
        connect_btn = Button(text="Connect", size_hint_x=0.2, on_press=self.do_connect)
        conn_layout.add_widget(connect_btn)
        self.add_widget(conn_layout)

        self.add_widget(Label(size_hint_y=None, height=25, text="Touch pad (drag = move, tap = click)"))
        self.touch_pad = TouchPad(size_hint_y=0.4)
        self.touch_pad.canvas.before.add(Color(0.2, 0.25, 0.35, 1))
        self.touch_pad.canvas.before.add(Rectangle(pos=self.touch_pad.pos, size=self.touch_pad.size))
        self.touch_pad.bind(pos=self._update_pad_rect, size=self._update_pad_rect)
        self.add_widget(self.touch_pad)

        keys_layout = GridLayout(cols=4, size_hint_y=None, height=120, spacing=4, padding=4)
        for label, key in [
            ("Backspace", "backspace"), ("Enter", "enter"), ("Tab", "tab"), ("Esc", "escape"),
            ("Up", "up"), ("Down", "down"), ("Left", "left"), ("Right", "right"),
        ]:
            btn = Button(text=label, on_press=lambda b, k=key: self.send_key(k))
            keys_layout.add_widget(btn)
        self.add_widget(keys_layout)

        scroll_layout = BoxLayout(size_hint_y=None, height=50)
        scroll_layout.add_widget(Button(text="Scroll Up", on_press=lambda _: self.send_scroll(2)))
        scroll_layout.add_widget(Button(text="Scroll Down", on_press=lambda _: self.send_scroll(-2)))
        self.add_widget(scroll_layout)

    def _update_status_label(self, *args):
        self.status_label.text = self.status

    def _update_pad_rect(self, *args):
        for c in self.touch_pad.canvas.before.children:
            if type(c).__name__ == "Rectangle":
                c.pos = self.touch_pad.pos
                c.size = self.touch_pad.size
                break

    def refresh_devices(self, *args):
        self.bt = get_bt()
        if not self.bt:
            self.status = "Bluetooth not available"
            return
        self.device_list.clear_widgets()
        try:
            devices = self.bt["list_paired"]()
            for d in devices:
                btn = Button(
                    text=f"{d['name']}\n{d['address']}",
                    size_hint_y=None, height=60,
                    on_press=lambda b, addr=d["address"]: self._select_device(addr),
                )
                self.device_list.add_widget(btn)
            if not devices:
                self.device_list.add_widget(Label(text="No paired devices. Pair laptop first.", size_hint_y=None, height=40))
        except Exception as e:
            self.status = str(e)

    def _select_device(self, address: str):
        self._selected_address = address
        self.status = "Selected: " + address

    def do_connect(self, *args):
        self.bt = get_bt()
        if not self.bt:
            self.status = "Bluetooth not available"
            return
        addr = getattr(self, "_selected_address", None)
        if not addr:
            self.status = "Select a device first (tap one above)"
            return
        try:
            self.bt["connect"](addr)
            self.send = self.bt["send"]
            self.connected = True
            self.status = "Connected to " + addr
        except Exception as e:
            self.status = "Connect failed: " + str(e)
            self.connected = False

    def send_key(self, key: str):
        if self.send:
            self.send(encode_command(CMD_KEY, key).strip())

    def send_scroll(self, dy: int):
        if self.send:
            self.send(encode_command(CMD_SCROLL, str(dy)).strip())
