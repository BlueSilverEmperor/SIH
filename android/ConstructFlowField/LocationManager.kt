package com.constructflow.field

import android.content.Context
import android.location.Location
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlin.math.*

data class GeofenceState(
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val distanceFromCenterMeters: Double = 0.0,
    val isInsideGeofence: Boolean = false,
    val statusText: String = "Acquiring GPS...",
    val targetLatitude: Double = 37.7749,
    val targetLongitude: Double = -122.4194,
    val allowedRadiusMeters: Double = 200.0
)

/**
 * FusedLocationProviderClient manager for computing Android GPS coordinates and evaluating project geofence boundaries.
 */
class LocationManager(private val context: Context) {
    private val _geofenceState = MutableStateFlow(GeofenceState())
    val geofenceState: StateFlow<GeofenceState> = _geofenceState

    fun updateTargetGeofence(lat: Double, lng: Double, radiusMeters: Double = 200.0) {
        val current = _geofenceState.value
        _geofenceState.value = current.copy(
            targetLatitude = lat,
            targetLongitude = lng,
            allowedRadiusMeters = radiusMeters
        )
    }

    fun onLocationUpdated(location: Location) {
        val current = _geofenceState.value
        val dist = calculateHaversineDistance(
            location.latitude,
            location.longitude,
            current.targetLatitude,
            current.targetLongitude
        )

        val inside = dist <= current.allowedRadiusMeters
        val text = if (inside) {
            "Verified Inside Geofence (${dist.roundToInt()}m from center)"
        } else {
            "Geofence Violation: ${dist.roundToInt()}m away (max ${current.allowedRadiusMeters.roundToInt()}m)"
        }

        _geofenceState.value = current.copy(
            latitude = location.latitude,
            longitude = location.longitude,
            distanceFromCenterMeters = dist,
            isInsideGeofence = inside,
            statusText = text
        )
    }

    companion object {
        fun calculateHaversineDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
            val r = 6371000.0 // Earth radius in meters
            let {
                val dLat = Math.toRadians(lat2 - lat1)
                val dLon = Math.toRadians(lon2 - lon1)
                val a = sin(dLat / 2.0).pow(2.0) +
                        cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
                        sin(dLon / 2.0).pow(2.0)
                val c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
                return r * c
            }
        }
    }
}
