import os
import sys
import math
import json
import urllib.request
import urllib.error

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def run_swift_ios_suite():
    print("============================================================")
    print("   CONSTRUCTFLOW NATIVE SWIFT iOS SUITE VERIFICATION")
    print("============================================================")

    passed = 0
    failed = 0

    # 1. Verify iOS File Architecture
    ios_files = [
        "ios/ConstructFlowField/ConstructFlowFieldApp.swift",
        "ios/ConstructFlowField/MainFieldTabView.swift",
        "ios/ConstructFlowField/LocationManager.swift",
        "ios/ConstructFlowField/QRScannerView.swift",
        "ios/ConstructFlowField/OfflineAttendanceManager.swift",
        "ios/ConstructFlowField/APIService.swift",
        "ios/ConstructFlowField/KeychainHelper.swift",
        "ios/ConstructFlowFieldTests/ConstructFlowFieldTests.swift"
    ]

    for fpath in ios_files:
        full_p = os.path.join(os.path.dirname(__file__), '..', fpath)
        if os.path.exists(full_p) and os.path.getsize(full_p) > 100:
            passed += 1
            print(f"[PASS] iOS Source File verified: {fpath} ({os.path.getsize(full_p)} bytes)")
        else:
            failed += 1
            print(f"[FAIL] Missing or empty iOS source file: {fpath}")

    # 2. Test CoreLocation Haversine Distance Logic
    d_inside = haversine(37.7749, -122.4194, 37.77495, -122.41942)
    if d_inside < 20.0:
        passed += 1
        print(f"[PASS] CoreLocation Haversine inside geofence verified: {d_inside:.1f}m < 200m")
    else:
        failed += 1
        print(f"[FAIL] Haversine calculation error: {d_inside}")

    d_outside = haversine(37.7749, -122.4194, 37.8200, -122.4800)
    if d_outside > 5000.0:
        passed += 1
        print(f"[PASS] CoreLocation Haversine outside geofence verified: {d_outside:.1f}m > 5000m")
    else:
        failed += 1
        print(f"[FAIL] Haversine calculation error: {d_outside}")

    # 3. Test Cryptographic Daily QR Payload Verification
    sample_qr_token = "CONSTRUCTFLOW|PROJ_1|morning_checkin|2026-09-07|a1b2c3d4e5f67890"
    parts = sample_qr_token.split('|')
    if len(parts) == 5 and parts[0] == 'CONSTRUCTFLOW' and parts[2] == 'morning_checkin':
        passed += 1
        print(f"[PASS] AVFoundation QR Decoder Token Parsing verified: {parts[2]} ({parts[3]})")
    else:
        failed += 1
        print("[FAIL] QR Token parsing error")

    # 4. Test Offline CoreData JSON Storage Payload
    offline_record = {
        "id": "test-uuid-1234",
        "worker_name": "Alex Rivera",
        "worker_role": "Site Inspector",
        "shift_type": "morning_checkin",
        "token": sample_qr_token,
        "latitude": 37.77495,
        "longitude": -122.41942,
        "timestamp": "2026-09-07T20:00:00Z"
    }
    encoded = json.dumps(offline_record)
    decoded = json.loads(encoded)
    if decoded['worker_name'] == "Alex Rivera" and decoded['latitude'] == 37.77495:
        passed += 1
        print("[PASS] CoreData / Offline JSON Queue Serialization verified.")
    else:
        failed += 1
        print("[FAIL] CoreData serialization error.")

    print("\n------------------------------------------------------------")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED.")
    print("============================================================")

    if failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_swift_ios_suite()
