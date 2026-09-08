import unittest
import json
import os
import django
from django.test import TestCase, Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from core.models import Project, WBSTask, Supplier
from seed import seed_database
from services.predictive_engine import calculate_predictive_completion
from services.evm_engine import calculate_project_evm

class TestPredictiveEngine(TestCase):

    def setUp(self):
        self.client = Client()
        seed_database()

    def test_baseline_predictive_calculation(self):
        """Test baseline predictive completion calculation on freshly seeded database."""
        project = Project.objects.first()
        res = calculate_predictive_completion(project.id)
        
        self.assertIsNotNone(res)
        self.assertEqual(res['project_id'], project.id)
        self.assertIn('forecasted_end_date', res)
        self.assertIn('actual_velocity', res)
        self.assertIn('planned_velocity', res)
        self.assertIn('schedule_variance_days', res)
        print(f"[PASS] Baseline Predictive Calculation verified: Velocity={res['actual_velocity']} units/day, Forecast End={res['forecasted_end_date']}, Variance={res['schedule_variance_days']}d")

    def test_schedule_delay_simulation(self):
        """Simulate a 40% reduction in actual output to verify schedule delay forecasting."""
        project = Project.objects.first()
        tasks = WBSTask.objects.filter(project_id=project.id)
        
        for t in tasks:
            t.actual_quantity = round(t.planned_quantity * 0.3, 1)
            t.calculate_evm()
            t.save()

        res = calculate_predictive_completion(project.id)
        self.assertIsNotNone(res)
        self.assertGreater(res['schedule_variance_days'], 0)
        self.assertIn(res['predictive_status'], ['delayed', 'critical_slip'])
        print(f"[PASS] Schedule Delay Simulation verified: Variance=+{res['schedule_variance_days']} days (Status: {res['predictive_status']})")

    def test_supplier_risk_buffer_projection(self):
        """Assign a low-scoring supplier to a critical-path task and verify risk buffer addition."""
        project = Project.objects.first()
        
        risky_vendor = Supplier.objects.create(
            name="Delinquent Steel LLC",
            category="structural_steel",
            contact_email="bad@steel.com",
            tco_score=40.0,
            delivery_score=35.0,
            quality_score=50.0,
            stability_score=45.0,
            esg_score=50.0,
            status="active"
        )
        risky_vendor.calculate_weighted_score()
        risky_vendor.softmax_probability = 0.05
        risky_vendor.save()

        critical_task = WBSTask.objects.filter(project_id=project.id, is_critical_path=True).first()
        self.assertIsNotNone(critical_task)
        critical_task.assigned_supplier = risky_vendor
        critical_task.save()

        res = calculate_predictive_completion(project.id)
        self.assertIsNotNone(res)
        self.assertGreater(res['supplier_risk_buffer_days'], 0)
        self.assertGreater(len(res['supplier_risk_notes']), 0)
        print(f"[PASS] Supplier Risk Buffer verified: Added +{res['supplier_risk_buffer_days']} risk buffer days for supplier '{risky_vendor.name}'")

    def test_api_endpoints(self):
        """Test GET /api/predictive-forecast and POST /api/update-task-schedule."""
        res_get = self.client.get('/api/predictive-forecast')
        self.assertEqual(res_get.status_code, 200)
        json_get = json.loads(res_get.content.decode('utf-8'))
        self.assertTrue(json_get['success'])
        self.assertIn('predictive', json_get)

        task = WBSTask.objects.first()
        res_post = self.client.post('/api/update-task-schedule', data=json.dumps({
            'task_id': task.id,
            'is_critical_path': True,
            'milestone_name': 'Super Critical Gate'
        }), content_type='application/json')
        self.assertEqual(res_post.status_code, 200)
        json_post = json.loads(res_post.content.decode('utf-8'))
        self.assertTrue(json_post['success'])
        self.assertTrue(json_post['task']['is_critical_path'])
        print("[PASS] Predictive API Endpoints GET & POST verified.")

    def test_zero_actual_velocity_fallback(self):
        """Verify that when actual_velocity is 0.0, effective_velocity falls back to planned_velocity rather than 0.1."""
        project = Project.objects.first()
        tasks = WBSTask.objects.filter(project_id=project.id)
        
        # Reset all actual quantities to 0
        for t in tasks:
            t.actual_quantity = 0.0
            t.calculate_evm()
            t.save()

        res = calculate_predictive_completion(project.id)
        self.assertIsNotNone(res)
        self.assertEqual(res['actual_velocity'], 0.0)
        self.assertGreater(res['effective_velocity'], 0.1)
        self.assertLess(res['remaining_forecast_days'], 5000)
        print(f"[PASS] Zero Velocity Fallback verified: Actual Vel={res['actual_velocity']}, Eff Vel={res['effective_velocity']} units/day, Forecast Days={res['remaining_forecast_days']}")

