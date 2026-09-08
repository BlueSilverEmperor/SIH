import os
import json
import datetime
import django
from django.test import TestCase, Client
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from core.models import Project, WBSTask, Supplier, AttendanceRecord, WeatherRiskLog, ProcurementReviewItem, FailSafeReorgLog
from seed import seed_database
from services.qr_attendance_engine import generate_daily_qr_token, verify_qr_token, record_geofenced_attendance
from services.weather_hedging_engine import evaluate_weather_risk_and_hedge
from services.failsafe_engine import evaluate_and_trigger_failsafe_reorg
from services.supplier_engine import calculate_supplier_scores_and_softmax


class EnterpriseEcosystemQASuite(TestCase):

    def setUp(self):
        self.client = Client()
        seed_database()
        self.project = Project.objects.first()

    def test_01_cryptographic_qr_tokens(self):
        """Verify HMAC-SHA256 daily-refreshing QR token generation and signature verification."""
        morning_qr = generate_daily_qr_token(self.project.id, shift_type='morning_checkin')
        self.assertTrue(morning_qr['is_valid'])
        self.assertIn('CONSTRUCTFLOW', morning_qr['token'])
        self.assertEqual(morning_qr['shift_type'], 'morning_checkin')

        # Verify token validity
        ver_res = verify_qr_token(morning_qr['token'], self.project.id, shift_type='morning_checkin')
        self.assertTrue(ver_res['valid'])

        # Verify tampered token rejection
        tampered_token = morning_qr['token'] + "X"
        bad_res = verify_qr_token(tampered_token, self.project.id, shift_type='morning_checkin')
        self.assertFalse(bad_res['valid'])
        self.assertIn('tampered', bad_res['reason'].lower())

        print("[OK] Test Enterprise 1 Passed: Cryptographic HMAC QR Token generation and verification.")

    def test_02_geofenced_attendance_and_gps(self):
        """Verify GPS Haversine distance calculation and geofence perimeter validation."""
        morning_qr = generate_daily_qr_token(self.project.id, shift_type='morning_checkin')
        
        # Valid GPS Check-in (inside 200m radius)
        valid_res = record_geofenced_attendance(
            project_id=self.project.id,
            worker_name="Alex Rivera",
            worker_role="Site Inspector",
            shift_type="morning_checkin",
            token_str=morning_qr['token'],
            user_lat=37.77495,
            user_lng=-122.41942
        )
        self.assertTrue(valid_res['success'])
        self.assertEqual(valid_res['record']['status'], 'verified')
        self.assertTrue(valid_res['record']['is_geofence_valid'])

        # Geofence Violation Check-in (5km away)
        out_res = record_geofenced_attendance(
            project_id=self.project.id,
            worker_name="Delinquent Field Worker",
            worker_role="Subcontractor",
            shift_type="morning_checkin",
            token_str=morning_qr['token'],
            user_lat=37.82000,
            user_lng=-122.48000
        )
        self.assertFalse(out_res['success'])
        self.assertEqual(out_res['record']['status'], 'geofence_violation')
        self.assertFalse(out_res['record']['is_geofence_valid'])

        print("[OK] Test Enterprise 2 Passed: Geofenced GPS location perimeter verification.")

    def test_03_hitl_procurement_and_softmax(self):
        """Verify HITL Procurement authorization queue and Softmax vendor scoring integration."""
        suppliers = calculate_supplier_scores_and_softmax()
        self.assertGreater(len(suppliers), 0)

        top_steel_supplier = max([s for s in suppliers if s.category == 'Steel Rebar'], key=lambda s: s.softmax_probability)
        self.assertIsNotNone(top_steel_supplier)

        response = self.client.post('/api/procurement/approve', data=json.dumps({
            'material_name': 'Structural Rebar Fe550D',
            'quantity': 60.0,
            'unit_cost': 920.0,
            'supplier_id': top_steel_supplier.id
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['success'])
        self.assertEqual(data['procurement']['material_name'], 'Structural Rebar Fe550D')
        self.assertEqual(data['task']['assigned_supplier_id'], top_steel_supplier.id)

        print("[OK] Test Enterprise 3 Passed: HITL Procurement Review & Softmax Vendor Scoring.")

    def test_04_3day_failsafe_reorg_engine(self):
        """Verify 3-Day Early Deadline Fail-Safe Engine dependency crashing."""
        failsafe_res = evaluate_and_trigger_failsafe_reorg(self.project.id, force=True)
        self.assertTrue(failsafe_res['enabled'])
        self.assertTrue(failsafe_res['triggered'])
        self.assertGreater(failsafe_res['days_saved'], 0)

        logs = FailSafeReorgLog.objects.filter(project_id=self.project.id)
        self.assertGreaterEqual(logs.count(), 1)

        print("[OK] Test Enterprise 4 Passed: Strict 3-Day Early Deadline Fail-Safe Re-Organization Engine.")

    def test_05_weather_risk_hedging(self):
        """Verify Weather-Risk Scheduling Hedging Engine outdoor activity protection."""
        hedging_res = evaluate_weather_risk_and_hedge(self.project.id, forecast_override={
            'condition': 'Severe Downpour & Gale Winds',
            'precipitation': 90.0,
            'wind_speed': 50.0,
            'temperature': 17.0
        })
        self.assertTrue(hedging_res['enabled'])
        self.assertTrue(hedging_res['hedged'])
        self.assertEqual(hedging_res['risk_severity'], 'severe')
        self.assertEqual(hedging_res['buffer_days_added'], 3)

        logs = WeatherRiskLog.objects.filter(project_id=self.project.id)
        self.assertGreaterEqual(logs.count(), 1)

        print("[OK] Test Enterprise 5 Passed: Weather-Risk Scheduling Hedging Engine.")

    def test_06_voice_field_logging(self):
        """Verify Voice-Activated Field Logging API integration with AI extraction."""
        voice_text = "Site inspector voice log: Completed 120 sq.m of interior drywall framing on floor 3 with 5 crew members today."
        response = self.client.post('/api/addons/voice-log', data=json.dumps({
            'transcript': voice_text
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['success'])
        self.assertGreater(len(data['metrics_extracted']), 0)

        print("[OK] Test Enterprise 6 Passed: Voice-Activated Field Logging API.")

    def test_07_companion_and_web_routes(self):
        """Verify all Web views render successfully (Companion, Addons, Review Queue, Flowchart, etc.)."""
        routes = ['/companion', '/addons', '/review-queue', '/flowchart', '/master-schedule', '/ingestion', '/suppliers', '/blueprint-3d', '/analytics', '/']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed to render 200 OK")

        print("[OK] Test Enterprise 7 Passed: All Companion App and Enterprise Web View routes rendered 200 OK.")
