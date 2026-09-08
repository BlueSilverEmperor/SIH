import Foundation
import CoreLocation
import Combine

/// Native CoreLocation Geofence Manager for tracking worker GPS location and calculating distance to active project perimeter.
public class LocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published public var currentLocation: CLLocation?
    @Published public var distanceFromProjectCenter: Double = 0.0
    @Published public var isInsideGeofence: Bool = false
    @Published public var geofenceStatusText: String = "Acquiring GPS..."
    @Published public var authorizationStatus: CLAuthorizationStatus = .notDetermined

    public var targetLatitude: Double = 37.7749
    public var targetLongitude: Double = -122.4194
    public var allowedRadiusMeters: Double = 200.0

    private let locationManager = CLLocationManager()

    public override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        locationManager.distanceFilter = 5.0 // Update every 5 meters
        locationManager.allowsBackgroundLocationUpdates = false
        locationManager.pausesLocationUpdatesAutomatically = true
    }

    public func requestPermissions() {
        locationManager.requestWhenInUseAuthorization()
    }

    public func startMonitoring(targetLat: Double, targetLng: Double, allowedRadius: Double = 200.0) {
        self.targetLatitude = targetLat
        self.targetLongitude = targetLng
        self.allowedRadiusMeters = allowedRadius
        
        locationManager.startUpdatingLocation()
        locationManager.startMonitoringSignificantLocationChanges()
    }

    public func stopMonitoring() {
        locationManager.stopUpdatingLocation()
    }

    /// Computes great-circle Haversine distance in meters between two coordinates.
    public static func calculateHaversineDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double) -> Double {
        let R = 6371000.0 // Earth radius in meters
        let dLat = (lat2 - lat1) * .pi / 180.0
        let dLon = (lon2 - lon1) * .pi / 180.0
        
        let a = sin(dLat / 2.0) * sin(dLat / 2.0) +
                cos(lat1 * .pi / 180.0) * cos(lat2 * .pi / 180.0) *
                sin(dLon / 2.0) * sin(dLon / 2.0)
        let c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
        return R * c
    }

    public func evaluateLocation(_ location: CLLocation) {
        self.currentLocation = location
        let distance = LocationManager.calculateHaversineDistance(
            lat1: location.coordinate.latitude,
            lon1: location.coordinate.longitude,
            lat2: targetLatitude,
            lon2: targetLongitude
        )
        
        self.distanceFromProjectCenter = distance
        self.isInsideGeofence = (distance <= allowedRadiusMeters)
        
        if isInsideGeofence {
            self.geofenceStatusText = "Verified Inside Geofence (\(Int(distance))m from center)"
        } else {
            self.geofenceStatusText = "Geofence Violation: \(Int(distance))m away (max \(Int(allowedRadiusMeters))m)"
        }
    }

    // MARK: - CLLocationManagerDelegate

    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        evaluateLocation(location)
    }

    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        self.authorizationStatus = manager.authorizationStatus
        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways {
            locationManager.startUpdatingLocation()
        }
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("[CoreLocation] Error acquiring location: \(error.localizedDescription)")
    }
}
