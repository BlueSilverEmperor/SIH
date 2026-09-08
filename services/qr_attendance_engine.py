import hmac
import hashlib
import math
import datetime
from django.utils import timezone
from core.models import Project, AttendanceRecord

SECRET_KEY = "ConstructFlow_Secure_Attendance_Key_2026"


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two GPS coordinates in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


def generate_daily_qr_token(project_id, shift_type='morning_checkin', date_str=None):
    """
    Generates a cryptographically signed, daily-refreshing QR token for morning check-in or evening check-out.
    """
    if not date_str:
        date_str = datetime.date.today().isoformat()

    raw_payload = f"CONSTRUCTFLOW|PROJ_{project_id}|{shift_type}|{date_str}"
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        raw_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:16]

    token = f"{raw_payload}|{signature}"
    return {
        'token': token,
        'project_id': project_id,
        'shift_type': shift_type,
        'date': date_str,
        'signature': signature,
        'is_valid': True
    }


def verify_qr_token(token_str, project_id, shift_type=None):
    """
    Verifies cryptographic signature and timestamp of a QR token.
    """
    try:
        parts = token_str.split('|')
        if len(parts) != 5 or parts[0] != 'CONSTRUCTFLOW':
            return {'valid': False, 'reason': 'Invalid QR format'}

        token_proj = parts[1].replace('PROJ_', '')
        token_shift = parts[2]
        token_date = parts[3]
        token_sig = parts[4]

        if str(token_proj) != str(project_id):
            return {'valid': False, 'reason': 'Token belongs to a different project'}

        if shift_type and token_shift != shift_type:
            return {'valid': False, 'reason': f'Token is for {token_shift}, expected {shift_type}'}

        today_str = datetime.date.today().isoformat()
        if token_date != today_str:
            return {'valid': False, 'reason': f'Token expired (generated for {token_date})'}

        # Re-compute signature check
        raw_payload = f"CONSTRUCTFLOW|PROJ_{token_proj}|{token_shift}|{token_date}"
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            raw_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:16]

        if not hmac.compare_digest(token_sig, expected_sig):
            return {'valid': False, 'reason': 'Cryptographic signature mismatch (tampered token)'}

        return {
            'valid': True,
            'shift_type': token_shift,
            'date': token_date,
            'signature': token_sig
        }
    except Exception as e:
        return {'valid': False, 'reason': str(e)}


def record_geofenced_attendance(project_id, worker_name, worker_role, shift_type, token_str, user_lat, user_lng):
    """
    Validates QR token and checks worker's GPS location against project geofence.
    Logs attendance record into AttendanceRecord table.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'success': False, 'error': 'Project not found'}

    # 1. Verify Cryptographic QR Token
    qr_res = verify_qr_token(token_str, project_id, shift_type)
    if not qr_res['valid']:
        return {'success': False, 'error': f"Attendance Rejected: {qr_res['reason']}"}

    # 2. Check GPS Geofence Perimeter
    proj_lat = project.geofence_latitude
    proj_lng = project.geofence_longitude
    allowed_radius = project.geofence_radius_meters

    distance_m = calculate_haversine_distance(user_lat, user_lng, proj_lat, proj_lng)
    is_geofence_valid = (distance_m <= allowed_radius)

    status = 'verified' if is_geofence_valid else 'geofence_violation'

    # Save to Database
    record = AttendanceRecord.objects.create(
        project=project,
        worker_name=worker_name or 'Field Engineer',
        worker_role=worker_role or 'Construction Crew',
        shift_type=shift_type,
        latitude=user_lat,
        longitude=user_lng,
        distance_from_center_m=distance_m,
        is_geofence_valid=is_geofence_valid,
        token_hash=qr_res.get('signature', ''),
        status=status
    )

    if not is_geofence_valid:
        return {
            'success': False,
            'record': record.to_dict(),
            'error': f"Geofence Violation! You are {round(distance_m, 1)}m away from project center (allowed max: {allowed_radius}m)."
        }

    return {
        'success': True,
        'record': record.to_dict(),
        'message': f"Successfully verified {shift_type.replace('_', ' ').title()} for {worker_name}! GPS Location within perimeter ({round(distance_m, 1)}m from center)."
    }
