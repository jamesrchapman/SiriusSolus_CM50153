package com.jroycha.solus_app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothManager
import android.bluetooth.le.*
import android.content.Context
import android.os.ParcelUuid
import android.util.Log
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp


import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat


import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.Preview
import com.jroycha.solus_app.ui.theme.Solus_AppTheme


private const val SOLUS_NAME = "SolusPump"
private lateinit var bluetoothAdapter: BluetoothAdapter
private var bluetoothGatt: BluetoothGatt? = null

class MainActivity : ComponentActivity() {

    private val blePermissions = arrayOf(
        Manifest.permission.BLUETOOTH_SCAN,
        Manifest.permission.BLUETOOTH_CONNECT,
        Manifest.permission.ACCESS_FINE_LOCATION
    )
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions.values.all { it }
        if (!granted) {
            // you could show a message here
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val missing = blePermissions.filter {
                ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
            }

            if (missing.isNotEmpty()) {
                permissionLauncher.launch(missing.toTypedArray())
            }
        }
        val bluetoothManager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = bluetoothManager.adapter

        setContent {
            SolusScanner()
            SolusApp()
//            Solus_AppTheme {
//                // A surface container using the 'background' color from the theme
////                Surface(
////                    modifier = Modifier.fillMaxSize(),
////                    color = MaterialTheme.colorScheme.background
////                ) {
////                    Greeting("Android")
////                }
//            }
        }
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    Solus_AppTheme {
        Greeting("Android")
    }
}

@Composable
fun SolusScanner() {
    var foundDevice by remember { mutableStateOf<BluetoothDevice?>(null) }
    var isConnected by remember { mutableStateOf(false) }

    val scanner = bluetoothAdapter.bluetoothLeScanner

    Column(Modifier.padding(16.dp)) {
        Button(onClick = {
            val filter = ScanFilter.Builder().setDeviceName(SOLUS_NAME).build()
            val settings = ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build()
            scanner.startScan(listOf(filter), settings, object : ScanCallback() {
                override fun onScanResult(callbackType: Int, result: ScanResult) {
                    result.device?.let { device ->
                        Log.i("SolusScan", "Found device: ${device.name} - ${device.address}")
                        foundDevice = device
                        scanner.stopScan(this)
                    }
                }
            })
        }) {
            Text("Scan for SolusPump")
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (foundDevice != null && !isConnected) {
            Button(onClick = {
                foundDevice?.connectGatt(null, false, object : BluetoothGattCallback() {
                    override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                        if (newState == BluetoothGatt.STATE_CONNECTED) {
                            Log.i("SolusConnect", "Connected to GATT server")
                            bluetoothGatt = gatt
                            isConnected = true
                        } else {
                            Log.w("SolusConnect", "Disconnected from GATT server")
                            bluetoothGatt = null
                            isConnected = false
                        }
                    }
                })
            }) {
                Text("Connect to ${foundDevice?.name}")
            }
        }

        if (isConnected) {
            Text("✅ Connected to SolusPump")
        }
    }
}



@Composable
fun SolusApp() {
    var connected by remember { mutableStateOf(false) }
    var commandText by remember { mutableStateOf("") }
    var commandLog by remember { mutableStateOf(listOf<String>()) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Top Bar
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                text = if (connected) "✅ Connected to SolusPump" else "❌ Disconnected",
                fontSize = 18.sp
            )
            Button(onClick = { connected = !connected }) {
                Text(if (connected) "Disconnect" else "Connect")
            }
        }

        // Manual Command Input
        OutlinedTextField(
            value = commandText,
            onValueChange = { commandText = it },
            label = { Text("Command") },
            modifier = Modifier.fillMaxWidth()
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {
                commandLog = commandLog + "Sent: $commandText"
                // Send to ESP32 via BLE
            }) {
                Text("Send")
            }
            Button(onClick = { commandText = "PUSH:0.1" }) {
                Text("Push 0.1u")
            }
            Button(onClick = { commandText = "FLUSH" }) {
                Text("Flush")
            }
        }

        // Log Section
        Text("Command Log:", fontSize = 16.sp)
        LazyColumn(modifier = Modifier.weight(1f)) {
            items(commandLog) { log ->
                Text(log)
            }
        }
    }
}




Incorporate Later:

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.shape.RoundedCornerShape

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                SolusApp()
            }
        }
    }
}

@Composable
fun SolusApp() {
    var connected by remember { mutableStateOf(false) }
    var commandText by remember { mutableStateOf("") }
    var commandLog by remember { mutableStateOf(listOf<String>()) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0A0E23))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(20.dp)
    ) {
        // Header
        Text(
            text = "SolusPump Controller",
            fontSize = 24.sp,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center
        )

        // Connection Status
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(if (connected) Color(0xFF1B5E20) else Color(0xFFB71C1C))
                .padding(horizontal = 16.dp, vertical = 12.dp)
        ) {
            Text(
                text = if (connected) "✅ Connected" else "❌ Disconnected",
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Button(onClick = { connected = !connected }) {
                Text(if (connected) "Disconnect" else "Connect")
            }
        }

        // Manual Command Input
        OutlinedTextField(
            value = commandText,
            onValueChange = { commandText = it },
            label = { Text("Enter Command") },
            modifier = Modifier.fillMaxWidth(),
            colors = OutlinedTextFieldDefaults.colors(
                unfocusedContainerColor = Color(0xFF1A1C2E),
                focusedContainerColor = Color(0xFF25273F),
                focusedTextColor = Color.White,
                unfocusedTextColor = Color.LightGray,
                focusedLabelColor = Color.White,
                unfocusedLabelColor = Color.Gray
            )
        )

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                onClick = {
                    commandLog = commandLog + "Sent: $commandText"
                    // Send to ESP32 via BLE
                },
                modifier = Modifier.weight(1f)
            ) {
                Text("Send")
            }
            Button(onClick = { commandText = "PUSH:0.1" }, modifier = Modifier.weight(1f)) {
                Text("Push 0.1u")
            }
            Button(onClick = { commandText = "FLUSH" }, modifier = Modifier.weight(1f)) {
                Text("Flush")
            }
        }

        // Log Section
        Text("Command Log:", fontSize = 16.sp, color = Color.White)
        Box(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFF1A1C2E))
                .padding(12.dp)
        ) {
            LazyColumn {
                items(commandLog) { log ->
                    Text(
                        log,
                        color = Color.LightGray,
                        modifier = Modifier.padding(vertical = 2.dp)
                    )
                }
            }
        }
    }
}
