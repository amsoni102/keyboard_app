package org.example.keyboardmouse

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.MotionEvent
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ListView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.io.OutputStream
import java.util.UUID

// Same protocol as laptop server: one command per line, UTF-8, newline-terminated
private val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

class MainActivity : AppCompatActivity() {

    private var socket: BluetoothSocket? = null
    private var output: OutputStream? = null
    private var statusText: TextView? = null
    private var deviceList: ListView? = null
    private var adapter: ArrayAdapter<String>? = null
    private val devices = mutableListOf<Pair<String, String>>() // address to name
    private var selectedAddress: String? = null

    private var touchStartX = 0f
    private var touchStartY = 0f
    private var hasMoved = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        statusText = findViewById(R.id.status)
        deviceList = findViewById(R.id.device_list)
        adapter = ArrayAdapter(this, android.R.layout.simple_list_item_1, mutableListOf<String>())
        deviceList?.adapter = adapter
        deviceList?.setOnItemClickListener { _, _, position, _ ->
            if (position < devices.size) {
                selectedAddress = devices[position].first
                statusText?.text = "Selected: ${devices[position].second}"
            }
        }
        requestBluetoothPermission()
        findViewById<Button>(R.id.refresh).setOnClickListener { refreshDevices() }
        findViewById<Button>(R.id.connect).setOnClickListener { connect() }
        setupTouchPad()
        setupKeys()
    }

    private fun requestBluetoothPermission() {
        if (Build.VERSION.SDK_INT >= 31 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.BLUETOOTH_CONNECT), 1)
        }
    }

    private fun refreshDevices() {
        if (Build.VERSION.SDK_INT >= 31 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            statusText?.text = "Grant Bluetooth permission first"
            return
        }
        val bt = BluetoothAdapter.getDefaultAdapter() ?: run {
            statusText?.text = "Bluetooth not available"
            return
        }
        if (!bt.isEnabled) {
            statusText?.text = "Turn on Bluetooth"
            return
        }
        devices.clear()
        bt.bondedDevices?.forEach { d ->
            devices.add(d.address to (d.name ?: d.address))
        }
        adapter?.clear()
        adapter?.addAll(devices.map { "${it.second} (${it.first})" })
        adapter?.notifyDataSetChanged()
        statusText?.text = if (devices.isEmpty()) "No paired devices. Pair your laptop first." else "Tap a device, then Connect."
    }

    private fun connect() {
        val addr = selectedAddress
        if (addr == null) {
            statusText?.text = "Select a device first (tap one above)"
            return
        }
        if (Build.VERSION.SDK_INT >= 31 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            statusText?.text = "Grant Bluetooth permission first"
            return
        }
        try {
            socket?.close()
            val device: BluetoothDevice = BluetoothAdapter.getDefaultAdapter().getRemoteDevice(addr)
            socket = device.createRfcommSocketToServiceRecord(SPP_UUID).apply { connect() }
            output = socket?.outputStream
            statusText?.text = "Connected to $addr"
        } catch (e: Exception) {
            statusText?.text = "Connect failed: ${e.message}"
        }
    }

    private fun send(line: String) {
        try {
            output?.write((line + "\n").toByteArray(Charsets.UTF_8))
            output?.flush()
        } catch (_: Exception) { }
    }

    private fun setupTouchPad() {
        val pad = findViewById<View>(R.id.touch_pad)
        pad.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    touchStartX = event.x
                    touchStartY = event.y
                    hasMoved = false
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.x - touchStartX).toInt()
                    val dy = -(event.y - touchStartY).toInt()
                    touchStartX = event.x
                    touchStartY = event.y
                    if (dx != 0 || dy != 0) {
                        hasMoved = true
                        send("MOVE:$dx,$dy")
                    }
                }
                MotionEvent.ACTION_UP -> {
                    if (!hasMoved) send("CLICK:left")
                }
            }
            true
        }
    }

    private fun setupKeys() {
        val keys = listOf(
            "Backspace" to "backspace", "Enter" to "enter", "Tab" to "tab", "Esc" to "escape",
            "Up" to "up", "Down" to "down", "Left" to "left", "Right" to "right"
        )
        keys.forEach { (label, key) ->
            findViewById<Button>(resources.getIdentifier("key_${key}", "id", packageName)).setOnClickListener { send("KEY:$key") }
        }
        findViewById<Button>(R.id.scroll_up).setOnClickListener { send("SCROLL:2") }
        findViewById<Button>(R.id.scroll_down).setOnClickListener { send("SCROLL:-2") }
    }

    override fun onDestroy() {
        try { socket?.close() } catch (_: Exception) { }
        super.onDestroy()
    }
}
