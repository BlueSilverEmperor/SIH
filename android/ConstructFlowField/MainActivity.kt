package com.constructflow.field

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material.MaterialTheme
import androidx.compose.material.darkColors
import androidx.compose.ui.graphics.Color

class MainActivity : ComponentActivity() {

    private lateinit var locationManager: LocationManager
    private lateinit var apiService: ApiService
    private lateinit var db: LocalAttendanceDatabase

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        locationManager = LocationManager(this)
        apiService = ApiService("http://10.0.2.2:8000")
        db = LocalAttendanceDatabase()

        setContent {
            MaterialTheme(colors = darkColors(primary = Color(0xFF9C27B0), background = Color(0xFF090D16))) {
                MainFieldScreen(
                    locationManager = locationManager,
                    apiService = apiService,
                    db = db
                )
            }
        }
    }
}
