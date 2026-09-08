package com.constructflow.field

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Main Jetpack Compose Screen for ConstructFlow Android Field Companion App.
 */
@Composable
fun MainFieldScreen(
    locationManager: LocationManager,
    apiService: ApiService,
    db: LocalAttendanceDatabase
) {
    var selectedTab by remember { mutableStateOf(0) }
    var workerName by remember { mutableStateOf("Alex Rivera") }
    var workerRole by remember { mutableStateOf("Site Inspector") }
    var shiftType by remember { mutableStateOf("morning_checkin") }
    var activeToken by remember { mutableStateOf("CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|a1b2c3d4e5f67890") }
    var statusMessage by remember { mutableStateOf<String?>(null) }
    var isSuccess by remember { mutableStateOf(true) }

    val geofenceState by locationManager.geofenceState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("ConstructFlow Field Android", color = Color.White, fontWeight = FontWeight.Bold) },
                backgroundColor = Color(0xFF111827)
            )
        },
        bottomBar = {
            BottomNavigation(backgroundColor = Color(0xFF111827)) {
                BottomNavigationItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    label = { Text("Attendance") },
                    icon = { Text("📍") }
                )
                BottomNavigationItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    label = { Text("QR Scanner") },
                    icon = { Text("📷") }
                )
                BottomNavigationItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    label = { Text("Sync Queue") },
                    icon = { Text("🔄") }
                )
                BottomNavigationItem(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    label = { Text("Settings") },
                    icon = { Text("⚙️") }
                )
            }
        },
        backgroundColor = Color(0xFF090D16)
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues).fillMaxSize()) {
            when (selectedTab) {
                0 -> AttendanceContent(
                    geofenceState = geofenceState,
                    workerName = workerName,
                    onWorkerNameChange = { workerName = it },
                    workerRole = workerRole,
                    onWorkerRoleChange = { workerRole = it },
                    shiftType = shiftType,
                    onShiftTypeChange = { shiftType = it },
                    statusMessage = statusMessage,
                    isSuccess = isSuccess,
                    onSubmit = {
                        apiService.sendAttendanceCheckIn(
                            workerName, workerRole, shiftType, activeToken,
                            geofenceState.latitude, geofenceState.longitude
                        ) { res ->
                            if (res.success) {
                                statusMessage = res.message ?: "Shift Attendance Verified!"
                                isSuccess = true
                            } else {
                                // Save to Room DB queue offline fallback
                                db.insertRecord(
                                    AttendanceRecordEntity(
                                        workerName = workerName,
                                        workerRole = workerRole,
                                        shiftType = shiftType,
                                        token = activeToken,
                                        latitude = geofenceState.latitude,
                                        longitude = geofenceState.longitude
                                    )
                                )
                                statusMessage = "Saved Offline Queue: ${res.error}"
                                isSuccess = false
                            }
                        }
                    }
                )
                1 -> QRScannerContent(activeToken) { scanned -> activeToken = scanned }
                2 -> SyncQueueContent(db)
                3 -> SettingsContent(apiService, geofenceState)
            }
        }
    }
}

@Composable
fun AttendanceContent(
    geofenceState: GeofenceState,
    workerName: String,
    onWorkerNameChange: (String) -> Unit,
    workerRole: String,
    onWorkerRoleChange: (String) -> Unit,
    shiftType: String,
    onShiftTypeChange: (String) -> Unit,
    statusMessage: String?,
    isSuccess: Boolean,
    onSubmit: () -> Unit
) {
    Column(modifier = Modifier.padding(16.dp).fillMaxSize(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        // Geofence Card
        Card(
            backgroundColor = Color(0xFF111827),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("GPS Geofence Radar", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Spacer(modifier = Modifier.weight(1f))
                    Text(
                        if (geofenceState.isInsideGeofence) "INSIDE SITE" else "OUTSIDE SITE",
                        color = if (geofenceState.isInsideGeofence) Color.Green else Color.Red,
                        fontWeight = FontWeight.Black,
                        fontSize = 12.sp
                    )
                }
                Text("Distance to Center: ${geofenceState.distanceFromCenterMeters.toInt()}m", color = Color.LightGray)
                Text(geofenceState.statusText, color = if (geofenceState.isInsideGeofence) Color.Green else Color(0xFFFF9800), fontSize = 12.sp)
            }
        }

        // Form Fields
        OutlinedTextField(
            value = workerName,
            onValueChange = onWorkerNameChange,
            label = { Text("Worker Full Name") },
            colors = TextFieldDefaults.outlinedTextFieldColors(textColor = Color.White, focusedBorderColor = Color(0xFF9C27B0)),
            modifier = Modifier.fillMaxWidth()
        )

        Button(
            onClick = onSubmit,
            colors = ButtonDefaults.buttonColors(backgroundColor = Color(0xFF9C27B0)),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.fillMaxWidth().height(50.dp)
        ) {
            Text("Verify Geofence & Submit Shift", color = Color.White, fontWeight = FontWeight.Bold)
        }

        statusMessage?.let { msg ->
            Card(
                backgroundColor = if (isSuccess) Color(0x2200FF00) else Color(0x22FF0000),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
            ) {
                Text(msg, color = if (isSuccess) Color.Green else Color.Red, modifier = Modifier.padding(12.dp), fontSize = 12.sp)
            }
        }
    }
}

@Composable
fun QRScannerContent(currentToken: String, onTokenScanned: (String) -> Unit) {
    Column(modifier = Modifier.padding(16.dp).fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Text("CameraX Dual QR Scanner Active", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Spacer(modifier = Modifier.height(16.dp))
        Text("Current Decoded Token:\n$currentToken", color = Color.Green, fontSize = 12.sp)
    }
}

@Composable
fun SyncQueueContent(db: LocalAttendanceDatabase) {
    val pending = db.getAllPending()
    Column(modifier = Modifier.padding(16.dp).fillMaxSize()) {
        Text("Offline Room Database Sync Queue", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Text("Pending records: ${pending.size}", color = Color.Gray, fontSize = 14.sp)
        Spacer(modifier = Modifier.height(16.dp))
        pending.forEach { record ->
            Text("• ${record.workerName} (${record.shiftType})", color = Color.LightGray, fontSize = 12.sp)
        }
    }
}

@Composable
fun SettingsContent(apiService: ApiService, geofenceState: GeofenceState) {
    Column(modifier = Modifier.padding(16.dp).fillMaxSize()) {
        Text("Settings & Config", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Spacer(modifier = Modifier.height(16.dp))
        Text("Server Base URL: ${apiService.baseUrl}", color = Color.LightGray)
        Text("Geofence Target: ${geofenceState.targetLatitude}, ${geofenceState.targetLongitude}", color = Color.LightGray)
    }
}
