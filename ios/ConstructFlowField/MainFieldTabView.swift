import SwiftUI

public struct MainFieldTabView: View {
    @StateObject var locationManager = LocationManager()
    @StateObject var apiService = APIService()
    @StateObject var offlineManager = OfflineAttendanceManager()

    @State private var workerName: String = "Alex Rivera"
    @State private var workerRole: String = "Site Inspector"
    @State private var selectedShift: String = "morning_checkin"
    @State private var activeToken: String = "CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|a1b2c3d4e5f67890"

    @State private var statusAlertMessage: String?
    @State private var isShowingAlert: Bool = false
    @State private var isAlertSuccess: Bool = true
    @State private var scannedCodeResult: String?

    public init() {}

    public var body: some View {
        TabView {
            // Tab 1: Attendance Check-In
            attendanceView
                .tabItem {
                    Label("Attendance", systemImage: "location.fill.viewfinder")
                }

            // Tab 2: Camera QR Scanner
            qrScannerView
                .tabItem {
                    Label("QR Scanner", systemImage: "qrcode.viewfinder")
                }

            // Tab 3: Offline Queue & Sync
            offlineQueueView
                .tabItem {
                    Label("Sync Queue (\(offlineManager.pendingQueue.count))", systemImage: "arrow.triangle.2.circlepath")
                }

            // Tab 4: Settings & Geofence Config
            settingsView
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
        }
        .accentColor(Color.purple)
        .preferredColorScheme(.dark)
        .onAppear {
            locationManager.requestPermissions()
            locationManager.startMonitoring(targetLat: 37.7749, targetLng: -122.4194, allowedRadius: 200.0)
        }
    }

    // MARK: - Tab 1: Attendance View
    private var attendanceView: View {
        NavigationView {
            ScrollView {
                VStack(spacing: 20) {
                    // Geofence Radar Status Card
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: "location.circle.fill")
                                .font(.title2)
                                .foregroundColor(locationManager.isInsideGeofence ? .green : .red)
                            Text("GPS Geofence Radar")
                                .font(.headline)
                                .fontWeight(.bold)
                            Spacer()
                            Text(locationManager.isInsideGeofence ? "INSIDE SITE" : "OUTSIDE SITE")
                                .font(.caption)
                                .fontWeight(.black)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(locationManager.isInsideGeofence ? Color.green.opacity(0.2) : Color.red.opacity(0.2))
                                .foregroundColor(locationManager.isInsideGeofence ? .green : .red)
                                .cornerRadius(8)
                        }

                        Divider()

                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Distance to Center")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                Text("\(Int(locationManager.distanceFromProjectCenter)) meters")
                                    .font(.title3)
                                    .fontWeight(.extrabold)
                                    .foregroundColor(.white)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 4) {
                                Text("Max Allowed Radius")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                                Text("\(Int(locationManager.allowedRadiusMeters)) meters")
                                    .font(.title3)
                                    .fontWeight(.bold)
                                    .foregroundColor(.purple)
                            }
                        }

                        Text(locationManager.geofenceStatusText)
                            .font(.footnote)
                            .foregroundColor(locationManager.isInsideGeofence ? .green : .orange)
                    }
                    .padding()
                    .background(Color(red: 0.08, green: 0.10, blue: 0.16))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(locationManager.isInsideGeofence ? Color.green.opacity(0.4) : Color.red.opacity(0.4), lineWidth: 1)
                    )

                    // Worker Details & Shift Input Form
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Field Engineer Details")
                            .font(.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(.gray)

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Worker Full Name")
                                .font(.caption)
                                .foregroundColor(.gray)
                            TextField("Enter Name", text: $workerName)
                                .textFieldStyle(RoundedBorderTextFieldStyle())
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Field Role / Specialization")
                                .font(.caption)
                                .foregroundColor(.gray)
                            Picker("Role", selection: $workerRole) {
                                Text("Site Inspector").tag("Site Inspector")
                                Text("Structural Engineer").tag("Structural Engineer")
                                Text("Safety Officer").tag("Safety Officer")
                                Text("Concrete Specialist").tag("Concrete Specialist")
                            }
                            .pickerStyle(SegmentedPickerStyle())
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Shift Action")
                                .font(.caption)
                                .foregroundColor(.gray)
                            Picker("Shift", selection: $selectedShift) {
                                Text("Morning Check-In").tag("morning_checkin")
                                Text("Evening Check-Out").tag("evening_checkout")
                            }
                            .pickerStyle(SegmentedPickerStyle())
                        }

                        // Submit Attendance Button
                        Button(action: handleCheckIn) {
                            HStack {
                                Image(systemName: "checkmark.seal.fill")
                                Text("Verify Geofence & Submit Shift")
                                    .fontWeight(.bold)
                            }
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(LinearGradient(gradient: Gradient(colors: [Color.purple, Color.indigo]), startPoint: .leading, endPoint: .trailing))
                            .foregroundColor(.white)
                            .cornerRadius(12)
                            .shadow(color: Color.purple.opacity(0.3), radius: 6, x: 0, y: 3)
                        }

                        if let msg = statusAlertMessage {
                            HStack {
                                Image(systemName: isAlertSuccess ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                Text(msg)
                                    .font(.caption)
                                    .fontWeight(.semibold)
                            }
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(isAlertSuccess ? Color.green.opacity(0.15) : Color.red.opacity(0.15))
                            .foregroundColor(isAlertSuccess ? .green : .red)
                            .cornerRadius(10)
                        }
                    }
                    .padding()
                    .background(Color(red: 0.08, green: 0.10, blue: 0.16))
                    .cornerRadius(16)
                }
                .padding()
            }
            .navigationTitle("ConstructFlow Field")
            .background(Color(red: 0.04, green: 0.05, blue: 0.08).edgesIgnoringSafeArea(.all))
        }
    }

    // MARK: - Tab 2: Camera QR Scanner
    private var qrScannerView: View {
        NavigationView {
            ZStack {
                QRScannerView { code in
                    self.scannedCodeResult = code
                    self.activeToken = code
                    self.statusAlertMessage = "Decoded Cryptographic Token: \(code.prefix(25))..."
                    self.isAlertSuccess = true
                }

                VStack {
                    Spacer()
                    VStack(spacing: 8) {
                        Text("Align Camera over Daily QR Code")
                            .font(.subheadline)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                        if let res = scannedCodeResult {
                            Text("Scanned: \(res)")
                                .font(.caption)
                                .foregroundColor(.green)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal)
                        } else {
                            Text("Supports Morning Check-In & Evening Check-Out QR")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                    .padding()
                    .background(Color.black.opacity(0.8))
                    .cornerRadius(12)
                    .padding(.bottom, 30)
                }
            }
            .navigationTitle("Dual QR Camera Scanner")
        }
    }

    // MARK: - Tab 3: Offline Queue
    private var offlineQueueView: View {
        NavigationView {
            List {
                Section(header: Text("Network Status & Queue Summary")) {
                    HStack {
                        Text("Server Connectivity")
                        Spacer()
                        Text(apiService.isOnline ? "Online" : "Offline / Unreachable")
                            .foregroundColor(apiService.isOnline ? .green : .orange)
                            .fontWeight(.bold)
                    }

                    HStack {
                        Text("Pending Offline Logs")
                        Spacer()
                        Text("\(offlineManager.pendingQueue.count) records")
                            .fontWeight(.bold)
                    }

                    Button(action: {
                        offlineManager.syncWithServer(apiService: apiService) { success, fail in
                            // Sync completed
                        }
                    }) {
                        HStack {
                            Image(systemName: "arrow.triangle.2.circlepath")
                            Text(offlineManager.isSyncing ? "Syncing..." : "Force Sync Queue Now")
                        }
                        .foregroundColor(.purple)
                        .fontWeight(.bold)
                    }
                    .disabled(offlineManager.isSyncing || offlineManager.pendingQueue.isEmpty)
                }

                Section(header: Text("Pending Attendance Records")) {
                    if offlineManager.pendingQueue.isEmpty {
                        Text("No pending offline records. All check-ins synced!")
                            .foregroundColor(.gray)
                            .font(.caption)
                    } else {
                        ForEach(offlineManager.pendingQueue) { item in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(item.workerName) (\(item.workerRole))")
                                    .fontWeight(.bold)
                                Text("Shift: \(item.shiftType) • Lat/Lng: \(String(format: "%.4f", item.latitude)), \(String(format: "%.4f", item.longitude))")
                                    .font(.caption)
                                    .foregroundColor(.gray)
                            }
                        }
                    }
                }
            }
            .listStyle(GroupedListStyle())
            .navigationTitle("Offline Sync Engine")
        }
    }

    // MARK: - Tab 4: Settings View
    private var settingsView: View {
        NavigationView {
            Form {
                Section(header: Text("ConstructFlow Server Connection")) {
                    TextField("Server Base URL", text: $apiService.baseURL)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                }

                Section(header: Text("Target Project Geofence Specs")) {
                    HStack {
                        Text("Center Latitude")
                        Spacer()
                        Text("\(locationManager.targetLatitude)")
                            .foregroundColor(.gray)
                    }
                    HStack {
                        Text("Center Longitude")
                        Spacer()
                        Text("\(locationManager.targetLongitude)")
                            .foregroundColor(.gray)
                    }
                    HStack {
                        Text("Perimeter Radius")
                        Spacer()
                        Text("\(Int(locationManager.allowedRadiusMeters))m")
                            .foregroundColor(.purple)
                    }
                }

                Section(header: Text("Keychain Security & Token Status")) {
                    HStack {
                        Text("Keychain Storage")
                        Spacer()
                        Text("Active (SecItem)")
                            .foregroundColor(.green)
                    }
                }
            }
            .navigationTitle("Settings & Config")
        }
    }

    // MARK: - Logic
    private func handleCheckIn() {
        let lat = locationManager.currentLocation?.coordinate.latitude ?? 37.77495
        let lng = locationManager.currentLocation?.coordinate.longitude ?? -122.41942

        if !apiService.isOnline {
            // Save to offline queue
            let pending = PendingAttendanceRecord(
                workerName: workerName,
                workerRole: workerRole,
                shiftType: selectedShift,
                token: activeToken,
                latitude: lat,
                longitude: lng
            )
            offlineManager.enqueueRecord(pending)
            statusAlertMessage = "Network Offline: Saved to offline queue (\(offlineManager.pendingQueue.count) queued)."
            isAlertSuccess = false
            return
        }

        apiService.sendAttendanceRecord(
            workerName: workerName,
            workerRole: workerRole,
            shiftType: selectedShift,
            token: activeToken,
            latitude: lat,
            longitude: lng
        ) { result in
            switch result {
            case .success(let res):
                if res.success {
                    statusAlertMessage = res.message ?? "Successfully verified shift attendance!"
                    isAlertSuccess = true
                } else {
                    statusAlertMessage = res.error ?? "Attendance Rejected by Server."
                    isAlertSuccess = false
                }
            case .failure(let err):
                // Enqueue offline fallback
                let pending = PendingAttendanceRecord(
                    workerName: workerName,
                    workerRole: workerRole,
                    shiftType: selectedShift,
                    token: activeToken,
                    latitude: lat,
                    longitude: lng
                )
                offlineManager.enqueueRecord(pending)
                statusAlertMessage = "Connection Failed: Saved to offline queue (\(err.localizedDescription))."
                isAlertSuccess = false
            }
        }
    }
}
