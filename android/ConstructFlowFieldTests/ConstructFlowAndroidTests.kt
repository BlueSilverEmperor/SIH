package com.constructflow.field

class ConstructFlowAndroidTests {
    companion object {
        fun runAllTests(): TestResult {
            var passed = 0
            var failed = 0
            val logs = mutableListOf<String>()

            fun assert(condition: Boolean, message: String) {
                if (condition) {
                    passed++
                    logs.add("[PASS] $message")
                } else {
                    failed++
                    logs.add("[FAIL] $message")
                }
            }

            // Test 1: Haversine Distance & Geofence Boundary
            let {
                val dInside = LocationManager.calculateHaversineDistance(37.7749, -122.4194, 37.77495, -122.41942)
                assert(dInside < 20.0, "Kotlin Haversine inside geofence verified: ${"%.1f".format(dInside)}m < 20m")

                val dOutside = LocationManager.calculateHaversineDistance(37.7749, -122.4194, 37.8200, -122.4800)
                assert(dOutside > 5000.0, "Kotlin Haversine outside geofence verified: ${"%.1f".format(dOutside)}m > 5000m")
            }

            // Test 2: Room SQLite Queue Database
            let {
                val db = LocalAttendanceDatabase()
                db.clearAll()
                assert(db.getAllPending().isEmpty(), "Room Database initially empty")

                val entity = AttendanceRecordEntity(
                    workerName = "Alex Rivera",
                    workerRole = "Site Inspector",
                    shiftType = "morning_checkin",
                    token = "CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|test",
                    latitude = 37.7749,
                    longitude = -122.4194
                )
                db.insertRecord(entity)
                assert(db.getAllPending().size == 1, "Room DB insertRecord succeeded")

                db.deleteRecord(entity.id)
                assert(db.getAllPending().isEmpty(), "Room DB deleteRecord succeeded")
            }

            // Test 3: CameraX QR Scanner Analyzer Parsing
            let {
                var scannedResult: QRScanResult? = null
                val analyzer = CameraXQRScannerAnalyzer { scannedResult = it }
                analyzer.processQRCodeText("CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|sig123")
                
                assert(scannedResult != null && scannedResult?.isValidFormat == true, "CameraX QR Token analyzer parsed valid token")
                assert(scannedResult?.shiftType == "morning_checkin", "CameraX QR Token shiftType extracted correctly")
            }

            return TestResult(passed, failed, logs)
        }
    }
}

data class TestResult(val passed: Int, val failed: Int, val logs: List<String>)
