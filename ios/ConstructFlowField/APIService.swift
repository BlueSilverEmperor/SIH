import Foundation
import Combine

public struct AttendanceAPIResponse: Codable {
    public var success: Bool
    public var message: String?
    public var error: String?
    public var record: AttendanceRecordPayload?
}

public struct AttendanceRecordPayload: Codable {
    public var id: Int?
    public var worker_name: String?
    public var worker_role: String?
    public var shift_type: String?
    public var status: String?
    public var is_geofence_valid: Bool?
    public var distance_from_center_m: Double?
}

public struct QRTokenResponse: Codable {
    public var success: Bool
    public var qr: QRDetailPayload?
    public var error: String?
}

public struct QRDetailPayload: Codable {
    public var token: String
    public var project_id: Int
    public var shift_type: String
    public var date: String
    public var signature: String
}

/// Asynchronous URLSession API Service communicating with ConstructFlow backend server.
public class APIService: ObservableObject {
    @Published public var baseURL: String = "http://127.0.0.1:8000"
    @Published public var isOnline: Bool = true

    public init(baseURL: String = "http://127.0.0.1:8000") {
        self.baseURL = baseURL
    }

    public func sendAttendanceRecord(
        workerName: String,
        workerRole: String,
        shiftType: String,
        token: String,
        latitude: Double,
        longitude: Double,
        completion: @escaping (Result<AttendanceAPIResponse, Error>) -> Void
    ) {
        guard let url = URL(string: "\(baseURL)/api/attendance/check-in-out") else {
            completion(.failure(NSError(domain: "APIService", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid API URL"])))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 10.0

        let body: [String: Any] = [
            "worker_name": workerName,
            "worker_role": workerRole,
            "shift_type": shiftType,
            "token": token,
            "latitude": latitude,
            "longitude": longitude
        ]

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body, options: [])
        } catch {
            completion(.failure(error))
            return
        }

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    self.isOnline = false
                    completion(.failure(error))
                }
                return
            }

            guard let data = data else {
                DispatchQueue.main.async {
                    completion(.failure(NSError(domain: "APIService", code: 500, userInfo: [NSLocalizedDescriptionKey: "No data received"])))
                }
                return
            }

            do {
                let apiRes = try JSONDecoder().decode(AttendanceAPIResponse.self, from: data)
                DispatchQueue.main.async {
                    self.isOnline = true
                    completion(.success(apiRes))
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
        task.resume()
    }

    public func fetchDailyQRToken(shiftType: String, completion: @escaping (Result<QRTokenResponse, Error>) -> Void) {
        guard let url = URL(string: "\(baseURL)/api/attendance/qr-token?shift_type=\(shiftType)") else {
            completion(.failure(NSError(domain: "APIService", code: 400, userInfo: [NSLocalizedDescriptionKey: "Invalid API URL"])))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 8.0

        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
                return
            }

            guard let data = data else {
                DispatchQueue.main.async {
                    completion(.failure(NSError(domain: "APIService", code: 500, userInfo: [NSLocalizedDescriptionKey: "No data received"])))
                }
                return
            }

            do {
                let qrRes = try JSONDecoder().decode(QRTokenResponse.self, from: data)
                DispatchQueue.main.async {
                    completion(.success(qrRes))
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
        task.resume()
    }
}
