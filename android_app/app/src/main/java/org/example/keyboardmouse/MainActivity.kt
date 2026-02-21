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
import android.widget.LinearLayout
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

    // Touchpad: faster cursor movement, less sensitive to jitter (dead zone)
    private val touchpadSpeed = 2.8f
    private val touchpadDeadZonePx = 3

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
            try {
                socket = device.createRfcommSocketToServiceRecord(SPP_UUID).apply { connect() }
            } catch (e: Exception) {
                // Fallback: some devices need channel 1 explicitly to connect to Linux BlueZ SPP
                val m = device.javaClass.getMethod("createRfcommSocket", Int::class.javaPrimitiveType)
                socket = m.invoke(device, 1) as BluetoothSocket
                (socket as BluetoothSocket).connect()
            }
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
                    val rawDx = event.x - touchStartX
                    val rawDy = -(event.y - touchStartY)
                    touchStartX = event.x
                    touchStartY = event.y
                    // Dead zone: ignore tiny movements (less sensitive to jitter)
                    val dx = if (kotlin.math.abs(rawDx) < touchpadDeadZonePx) 0f else rawDx * touchpadSpeed
                    val dy = if (kotlin.math.abs(rawDy) < touchpadDeadZonePx) 0f else rawDy * touchpadSpeed
                    val ix = dx.toInt()
                    val iy = dy.toInt()
                    if (ix != 0 || iy != 0) {
                        hasMoved = true
                        send("MOVE:$ix,$iy")
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
        // Mouse & Enter
        findViewById<Button>(R.id.key_left_click).setOnClickListener { send("CLICK:left") }
        findViewById<Button>(R.id.key_enter).setOnClickListener { send("KEY:enter") }
        // Arrows
        findViewById<Button>(R.id.key_up).setOnClickListener { send("KEY:up") }
        findViewById<Button>(R.id.key_down).setOnClickListener { send("KEY:down") }
        findViewById<Button>(R.id.key_left).setOnClickListener { send("KEY:left") }
        findViewById<Button>(R.id.key_right).setOnClickListener { send("KEY:right") }
        // Letter keys A–Z (send KEY:x when pressed)
        setupLetterKeys()
    }

    private fun setupLetterKeys() {
        val container = findViewById<LinearLayout>(R.id.letter_keys_container)
        val letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        val cols = 9
        var row: LinearLayout? = null
        letters.forEachIndexed { i, c ->
            if (i % cols == 0) {
                row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                    ).apply { setMargins(0, 2, 0, 2) }
                }
                container.addView(row)
            }
            val ch = c.lowercaseChar()
            val btn = Button(this).apply {
                text = c.toString()
                setOnClickListener { send("KEY:$ch") }
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply {
                    setMargins(2, 0, 2, 0)
                }
            }
            row?.addView(btn)
        }
    }

    override fun onDestroy() {
        try { socket?.close() } catch (_: Exception) { }
        super.onDestroy()
    }
}
