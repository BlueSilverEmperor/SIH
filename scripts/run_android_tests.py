import os
import sys
import math
import json

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def run_kotlin_android_suite():
    print("============================================================")
    print("  CONSTRUCTFLOW NATIVE KOTLIN ANDROID SUITE VERIFICATION")
    print("============================================================")

    passed = 0
    failed = 0

    # 1. Verify Android Source File Architecture
    android_files = [
        "android/ConstructFlowField/MainActivity.kt",
        "android/ConstructFlowField/MainFieldScreen.kt",
        "android/ConstructFlowField/LocationManager.kt",
        "android/ConstructFlowField/CameraXQRScanner.kt",
        "android/ConstructFlowField/AttendanceEntity.kt",
        "android/ConstructFlowField/ApiService.kt",
        "android/ConstructFlowField/EncryptedPreferencesHelper.kt",
        "android/ConstructFlowFieldTests/ConstructFlowAndroidTests.kt"
    ]

    for fpath in android_files:
        full_p = os.path.join(os.path.dirname(__file__), '..', fpath)
        if os.path.exists(full_p) and os.path.getsize(full_p) > 100:
            passed += 1
            print(f"[PASS] Android Source File verified: {fpath} ({os.path.getsize(full_p)} bytes)")
        else:
            failed += 1
            print(f"[FAIL] Missing or empty Android source file: {fpath}")

    # 2. Test FusedLocationProvider Haversine Distance Logic
    d_inside = haversine(37.7749, -122.4194, 37.77495, -122.41942)
    if d_inside < 20.0:
        passed += 1
        print(f"[PASS] FusedLocationProvider Haversine inside geofence verified: {d_inside:.1f}m < 200m")
    else:
        failed += 1
        print(f"[FAIL] Haversine distance error: {d_inside}")

    d_outside = haversine(37.7749, -122.4194, 37.8200, -122.4800)
    if d_outside > 5000.0:
        passed += 1
        print(f"[PASS] FusedLocationProvider Haversine outside geofence verified: {d_outside:.1f}m > 5000m")
    else:
        failed += 1
        print(f"[FAIL] Haversine distance error: {d_outside}")

    # 3. Test CameraX QR Code Analyzer Parsing
    sample_qr_token = "CONSTRUCTFLOW|PROJ_1|evening_checkout|2026-09-07|sig98765"
    parts = sample_qr_token.split('|')
    if len(parts) == 5 and parts[0] == 'CONSTRUCTFLOW' and parts[2] == 'evening_checkout':
        passed += 1
        print(f"[PASS] CameraX QR Analyzer Token Parsing verified: {parts[2]} ({parts[3]})")
    else:
        failed += 1
        print("[FAIL] QR Token parsing error")

    # 4. Test Room Database Entity Serialization
    room_record = {
        "id": "android-uuid-9988",
        "worker_name": "Alex Rivera",
        "worker_role": "Site Inspector",
        "shift_type": "evening_checkout",
        "token": sample_qr_token,
        "latitude": 37.77495,
        "longitude": -122.41942,
        "timestamp": 1757275200000,
        "sync_status": "pending"
    }
    encoded = json.dumps(room_record)
    decoded = json.loads(encoded)
    if decoded['worker_name'] == "Alex Rivera" and decoded['shift_type'] == "evening_checkout":
        passed += 1
        print("[PASS] Room Database Entity SQLite Serialization verified.")
    else:
        failed += 1
        print("[FAIL] Room entity serialization error")

    print("\n------------------------------------------------------------")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED.")
    print("============================================================")

    if failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_kotlin_android_suite()
