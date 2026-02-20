"""
Bluetooth client: connects to the laptop server and sends keyboard/mouse commands.
On Android uses Java Bluetooth API via jnius; on desktop uses PyBluez for testing.
"""

from protocol import SPP_UUID

def _android_send_line(stream, line: str) -> None:
    data = (line if line.endswith("\n") else line + "\n").encode("utf-8")
    stream.write(bytes(data))
    stream.flush()

def get_android_client():
    """Return (connect_func, send_func) that use Android Bluetooth, or None if not on Android."""
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
        BluetoothDevice = autoclass("android.bluetooth.BluetoothDevice")
        UUID = autoclass("java.util.UUID")
        # SPP UUID
        spp_uuid = UUID.fromString(SPP_UUID)

        _socket = None
        _output_stream = None

        def connect(device_address: str):
            nonlocal _socket, _output_stream
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter.isEnabled():
                raise RuntimeError("Bluetooth is disabled")
            device = adapter.getRemoteDevice(device_address)
            _socket = device.createRfcommSocketToServiceRecord(spp_uuid)
            _socket.connect()
            _output_stream = _socket.getOutputStream()

        def send(line: str):
            if _output_stream is None:
                raise RuntimeError("Not connected")
            _android_send_line(_output_stream, line)

        def disconnect():
            nonlocal _socket, _output_stream
            if _socket:
                try:
                    _socket.close()
                except Exception:
                    pass
                _socket = None
            _output_stream = None

        def list_paired():
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter.isEnabled():
                return []
            bonded = adapter.getBondedDevices()
            if bonded is None:
                return []
            return [{"name": d.getName(), "address": d.getAddress()} for d in bonded]

        return {"connect": connect, "send": send, "disconnect": disconnect, "list_paired": list_paired}
    except Exception:
        return None


def get_desktop_client():
    """For testing on desktop: use PyBluez to connect to a Bluetooth address."""
    try:
        import bluetooth
    except ImportError:
        return None

    _sock = None

    def connect(device_address: str):
        nonlocal _sock
        services = bluetooth.find_service(address=device_address, uuid=SPP_UUID)
        if not services:
            raise RuntimeError("SPP service not found on device. Is the laptop server running?")
        port = services[0]["port"]
        _sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        _sock.connect((device_address, port))

    def send(line: str):
        if _sock is None:
            raise RuntimeError("Not connected")
        data = (line if line.endswith("\n") else line + "\n").encode("utf-8")
        _sock.send(data)

    def disconnect():
        nonlocal _sock
        if _sock:
            try:
                _sock.close()
            except Exception:
                pass
            _sock = None

    def list_paired():
        try:
            nearby = bluetooth.discover_devices(duration=3, lookup_names=True)
            return [{"name": name or addr, "address": addr} for addr, name in nearby]
        except Exception:
            return []

    return {"connect": connect, "send": send, "disconnect": disconnect, "list_paired": list_paired}


_client_cache = None


def get_client():
    """Return Android client on Android, else desktop (PyBluez) client if available."""
    global _client_cache
    if _client_cache is not None:
        return _client_cache
    android = get_android_client()
    if android is not None:
        _client_cache = android
        return android
    _client_cache = get_desktop_client()
    return _client_cache


def get_bt():
    """Cached Bluetooth client (same as get_client(), for UI use)."""
    return get_client()
