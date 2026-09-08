import XCTest
import CoreLocation

public class ConstructFlowFieldTests {
    public static func runAllTests() -> (passed: Int, failed: Int, logs: [String]) {
        var passed = 0
        var failed = 0
        var logs: [String] = []

        func assert(_ condition: Bool, _ message: String) {
            if condition {
                passed += 1
                logs.append("[PASS] \(message)")
            } else {
                failed += 1
                logs.append("[FAIL] \(message)")
            }
        }

        // Test 1: Haversine Distance & Geofence Perimeter
        let lat1 = 37.7749, lon1 = -122.4194
        let lat2 = 37.77495, lon2 = -122.41942 // ~8.5 meters away
        let dist1 = LocationManager.calculateHaversineDistance(lat1: lat1, lon1: lon1, lat2: lat2, lon2: lon2)
        assert(dist1 < 20.0, "Haversine distance calculation accurate (\(String(format: "%.1f", dist1))m < 20m)")

        let latFar = 37.8200, lonFar = -122.4800 // ~7.2 km away
        let distFar = LocationManager.calculateHaversineDistance(lat1: lat1, lon1: lon1, lat2: latFar, lon2: lonFar)
        assert(distFar > 5000.0, "Outside geofence calculation accurate (\(String(format: "%.1f", distFar))m > 5000m)")

        // Test 2: Keychain Helper Operations
        let testSecret = "SecretToken12345"
        let saved = KeychainHelper.shared.saveString(testSecret, service: "ConstructFlowQA", account: "WorkerToken")
        assert(saved, "Keychain saveString succeeded")

        let retrieved = KeychainHelper.shared.readString(service: "ConstructFlowQA", account: "WorkerToken")
        assert(retrieved == testSecret, "Keychain readString retrieved identical secret (\(retrieved ?? ""))")

        let deleted = KeychainHelper.shared.delete(service: "ConstructFlowQA", account: "WorkerToken")
        assert(deleted, "Keychain delete secret succeeded")

        // Test 3: Offline Queue Operations
        let manager = OfflineAttendanceManager()
        manager.clearQueue()
        assert(manager.pendingQueue.count == 0, "Offline queue initially empty")

        let record = PendingAttendanceRecord(
            workerName: "Alex Rivera",
            workerRole: "Site Inspector",
            shiftType: "morning_checkin",
            token: "CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|test",
            latitude: 37.7749,
            longitude: -122.4194
        )
        manager.enqueueRecord(record)
        assert(manager.pendingQueue.count == 1, "Enqueue offline record succeeded")

        manager.removeRecord(id: record.id)
        assert(manager.pendingQueue.count == 0, "Remove offline record succeeded")

        // Test 4: API Payload Formatting
        let api = APIService(baseURL: "http://127.0.0.1:8000")
        assert(api.baseURL == "http://127.0.0.1:8000", "APIService baseURL initialized correctly")

        return (passed, failed, logs)
    }
}
