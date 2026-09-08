import json
from django.test import TestCase, Client
from django.utils import timezone
from core.models import Project, WBSTask, AttendanceRecord
from services.geofence_attendance_engine import (
    calculate_haversine_distance,
    process_worker_checkin,
    process_worker_checkout,
    update_project_geofence,
    get_attendance_summary_metrics
)


class GeofenceAttendanceTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.project = Project.objects.create(
            name="Test Geofence Project",
            code="PRJ-GEO-001",
            total_budget=800000.0,
            geofence_latitude=37.7749,
            geofence_longitude=-122.4194,
            geofence_radius_meters=200.0,
            status="active"
        )

        self.wbs_task = WBSTask.objects.create(
            project=self.project,
            wbs_code="1.1",
            task_name="Structural Steel Alignment",
            planned_quantity=100.0,
            actual_quantity=50.0,
            unit="tons",
            unit_cost=100.0,
            actual_cost=5000.0,
            is_critical_path=True
        )

    def test_haversine_distance_calculation(self):
        # 1. Exact same coordinates -> 0m
        dist_zero = calculate_haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
        self.assertAlmostEqual(dist_zero, 0.0, delta=0.1)

        # 2. Nearby coordinate inside 200m -> ~10m
        dist_inside = calculate_haversine_distance(37.7749, -122.4194, 37.77495, -122.41942)
        self.assertTrue(dist_inside < 200.0)

        # 3. Far coordinate outside 200m -> >5000m
        dist_outside = calculate_haversine_distance(37.7749, -122.4194, 37.8400, -122.5000)
        self.assertTrue(dist_outside > 200.0)

    def test_geofenced_checkin_inside_perimeter(self):
        res = process_worker_checkin(
            project_id=self.project.id,
            worker_id="WRK-TEST-01",
            worker_name="John Doe",
            worker_role="Field Engineer",
            lat=37.77495,
            lng=-122.41942,
            trade_category="Structural",
            hourly_rate=40.0,
            wbs_task_id=self.wbs_task.id
        )
        self.assertTrue(res['success'])
        self.assertTrue(res['is_geofence_valid'])
        self.assertEqual(res['record']['status'], 'verified')
        self.assertEqual(res['record']['shift_status'], 'ACTIVE_ON_SITE')

    def test_geofenced_checkin_outside_perimeter(self):
        res = process_worker_checkin(
            project_id=self.project.id,
            worker_id="WRK-TEST-02",
            worker_name="Jane Smith",
            worker_role="Inspector",
            lat=37.8400,
            lng=-122.5000,
            trade_category="Inspection",
            hourly_rate=50.0
        )
        self.assertTrue(res['success'])
        self.assertFalse(res['is_geofence_valid'])
        self.assertEqual(res['record']['status'], 'out_of_bounds')
        self.assertEqual(res['record']['shift_status'], 'OUT_OF_BOUNDS')

    def test_duplicate_checkin_prevention_state_machine(self):
        # First check-in
        res1 = process_worker_checkin(
            project_id=self.project.id,
            worker_id="WRK-TEST-03",
            worker_name="Robert Paulson",
            lat=37.7749,
            lng=-122.4194
        )
        self.assertTrue(res1['success'])

        # Duplicate check-in while active -> REJECTED
        res2 = process_worker_checkin(
            project_id=self.project.id,
            worker_id="WRK-TEST-03",
            worker_name="Robert Paulson",
            lat=37.7749,
            lng=-122.4194
        )
        self.assertFalse(res2['success'])
        self.assertIn("already checked in", res2['error'])

    def test_checkout_calculation_and_evm_cost_sync(self):
        # 1. Check in worker
        process_worker_checkin(
            project_id=self.project.id,
            worker_id="WRK-TEST-04",
            worker_name="Emily Watson",
            hourly_rate=50.0,
            lat=37.7749,
            lng=-122.4194,
            wbs_task_id=self.wbs_task.id
        )

        initial_actual_cost = self.wbs_task.actual_cost

        # 2. Check out worker
        res = process_worker_checkout(
            project_id=self.project.id,
            worker_id="WRK-TEST-04",
            lat=37.7749,
            lng=-122.4194
        )

        self.assertTrue(res['success'])
        self.assertEqual(res['record']['shift_status'], 'COMPLETED')
        self.assertTrue(res['shift_duration_hours'] > 0)
        self.assertTrue(res['labor_cost'] > 0)

        # 3. Verify EVM actual cost was updated
        self.wbs_task.refresh_from_db()
        self.assertTrue(self.wbs_task.actual_cost > initial_actual_cost)

    def test_attendance_web_view(self):
        response = self.client.get('/attendance')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Geofenced Worker Attendance Register")

    def test_api_attendance_endpoints(self):
        # 1. Checkin API
        checkin_payload = {
            'worker_id': 'WRK-API-101',
            'worker_name': 'API Worker',
            'worker_role': 'Welder',
            'trade_category': 'Welding',
            'hourly_rate': 45.0,
            'latitude': 37.7749,
            'longitude': -122.4194,
            'wbs_task_id': self.wbs_task.id
        }
        res_checkin = self.client.post(
            '/api/attendance/checkin',
            data=json.dumps(checkin_payload),
            content_type='application/json'
        )
        self.assertEqual(res_checkin.status_code, 200)

        # 2. Summary API
        res_summary = self.client.get('/api/attendance/summary')
        self.assertEqual(res_summary.status_code, 200)
        data_sum = json.loads(res_summary.content.decode('utf-8'))
        self.assertTrue(data_sum['success'])
        self.assertTrue(data_sum['active_on_site_count'] >= 1)

        # 3. Checkout API
        res_checkout = self.client.post(
            '/api/attendance/checkout',
            data=json.dumps({'worker_id': 'WRK-API-101'}),
            content_type='application/json'
        )
        self.assertEqual(res_checkout.status_code, 200)

        # 4. Geofence Update API
        geofence_payload = {
            'latitude': 37.7755,
            'longitude': -122.4199,
            'radius_meters': 300.0
        }
        res_geo = self.client.post(
            '/api/attendance/geofence',
            data=json.dumps(geofence_payload),
            content_type='application/json'
        )
        self.assertEqual(res_geo.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.geofence_radius_meters, 300.0)
