import Foundation
import Combine

public struct PendingAttendanceRecord: Codable, Identifiable {
    public var id: String
    public var workerName: String
    public var workerRole: String
    public var shiftType: String
    public var token: String
    public var latitude: Double
    public var longitude: Double
    public var timestamp: Date

    public init(id: String = UUID().uuidString, workerName: String, workerRole: String, shiftType: String, token: String, latitude: Double, longitude: Double, timestamp: Date = Date()) {
        self.id = id
        self.workerName = workerName
        self.workerRole = workerRole
        self.shiftType = shiftType
        self.token = token
        self.latitude = latitude
        self.longitude = longitude
        self.timestamp = timestamp
    }
}

/// Offline-First Resilience Manager caching field attendance check-ins during network drops.
public class OfflineAttendanceManager: ObservableObject {
    @Published public var pendingQueue: [PendingAttendanceRecord] = []
    @Published public var isSyncing: Bool = false
    @Published public var lastSyncMessage: String = "No pending offline logs."

    private let queueFilePath: URL

    public init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        self.queueFilePath = docs.appendingPathComponent("constructflow_offline_queue.json")
        loadQueueFromDisk()
    }

    public func enqueueRecord(_ record: PendingAttendanceRecord) {
        pendingQueue.append(record)
        saveQueueToDisk()
        lastSyncMessage = "Record saved offline. \(pendingQueue.count) items queued."
    }

    public func removeRecord(id: String) {
        pendingQueue.removeAll { $0.id == id }
        saveQueueToDisk()
    }

    public func clearQueue() {
        pendingQueue.removeAll()
        saveQueueToDisk()
    }

    private func saveQueueToDisk() {
        do {
            let data = try JSONEncoder().encode(pendingQueue)
            try data.write(to: queueFilePath)
        } catch {
            print("[OfflineManager] Failed to save queue to disk: \(error.localizedDescription)")
        }
    }

    private func loadQueueFromDisk() {
        guard FileManager.default.fileExists(atPath: queueFilePath.path) else { return }
        do {
            let data = try Data(contentsOf: queueFilePath)
            self.pendingQueue = try JSONDecoder().decode([PendingAttendanceRecord].self, from: data)
        } catch {
            print("[OfflineManager] Failed to load queue from disk: \(error.localizedDescription)")
        }
    }

    public func syncWithServer(apiService: APIService, completion: @escaping (Int, Int) -> Void) {
        guard !pendingQueue.isEmpty else {
            completion(0, 0)
            return
        }

        isSyncing = true
        let copy = pendingQueue
        var successCount = 0
        var failureCount = 0
        let group = DispatchGroup()

        for rec in copy {
            group.enter()
            apiService.sendAttendanceRecord(
                workerName: rec.workerName,
                workerRole: rec.workerRole,
                shiftType: rec.shiftType,
                token: rec.token,
                latitude: rec.latitude,
                longitude: rec.longitude
            ) { result in
                switch result {
                case .success(let response):
                    if response.success {
                        self.removeRecord(id: rec.id)
                        successCount += 1
                    } else {
                        failureCount += 1
                    }
                case .failure:
                    failureCount += 1
                }
                group.leave()
            }
        }

        group.notify(queue: .main) {
            self.isSyncing = false
            self.lastSyncMessage = "Sync completed: \(successCount) uploaded, \(failureCount) failed."
            completion(successCount, failureCount)
        }
    }
}
