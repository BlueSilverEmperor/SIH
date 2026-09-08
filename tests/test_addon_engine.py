import os
import unittest
import datetime
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from django.test import TestCase, Client
from core.models import Project, WBSTask, Supplier, ProjectAddOn, DailyProgressAudit, FailSafeReorgLog
from services.addon_manager import get_project_addons, is_addon_enabled, set_addon_status, toggle_addon
from services.daily_audit_service import run_daily_progress_audit
from services.failsafe_engine import evaluate_and_trigger_failsafe_reorg
from services.supplier_engine import calculate_supplier_scores_and_softmax, get_recommended_supplier_by_category
from services.blender_service import generate_3d_blueprint


class ModularAddOnEngineTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = datetime.date.today()
        self.target_end = self.today + datetime.timedelta(days=100)

        self.project = Project.objects.create(
            name="Add-On Test Construction Site",
            code="PRJ-ADDON-TEST",
            description="Testing modular add-on feature toggles and fail-safe engine.",
            total_budget=500000.0,
            start_date=self.today - datetime.timedelta(days=20),
            target_end_date=self.target_end,
            status="active"
        )

        self.task1 = WBSTask.objects.create(
            project=self.project,
            wbs_code="1.1",
            task_name="Excavation & Shoring",
            planned_quantity=100.0,
            actual_quantity=20.0,
            unit="cu.m",
            unit_cost=50.0,
            is_critical_path=True,
            planned_start_date=self.today - datetime.timedelta(days=20),
            planned_end_date=self.target_end
        )
        self.task1.calculate_evm()
        self.task1.save()

        self.supplier = Supplier.objects.create(
            name="Test Rebar Corp",
            category="Steel Rebar",
            tco_score=85.0,
            delivery_score=90.0,
            quality_score=88.0,
            stability_score=80.0,
            esg_score=75.0
        )

    def test_01_feature_toggle_architecture(self):
        """Verify project add-on toggling and persistence"""
        addons = get_project_addons(self.project.id)
        self.assertIn('supplier_softmax_engine', addons)
        self.assertIn('blender_3d_generator', addons)
        self.assertIn('daily_progress_audit', addons)
        self.assertIn('early_deadline_failsafe', addons)

        # Toggle OFF supplier_softmax_engine
        set_addon_status(self.project.id, 'supplier_softmax_engine', False)
        self.assertFalse(is_addon_enabled(self.project.id, 'supplier_softmax_engine'))

        # Toggle ON
        set_addon_status(self.project.id, 'supplier_softmax_engine', True)
        self.assertTrue(is_addon_enabled(self.project.id, 'supplier_softmax_engine'))

    def test_02_addon_1_supplier_softmax_toggle(self):
        """Test Add-On 1 (Supplier Softmax) on vs off behavior"""
        # When active
        set_addon_status(self.project.id, 'supplier_softmax_engine', True)
        res_on = get_recommended_supplier_by_category(project_id=self.project.id)
        self.assertTrue(res_on.get('enabled'))
        self.assertIn('Steel Rebar', res_on.get('recommendations', {}))

        # When disabled
        set_addon_status(self.project.id, 'supplier_softmax_engine', False)
        res_off = get_recommended_supplier_by_category(project_id=self.project.id)
        self.assertFalse(res_off.get('enabled'))

    def test_03_addon_2_blender_3d_generator_toggle(self):
        """Test Add-On 2 (Blender 3D Generator) on vs off behavior"""
        set_addon_status(self.project.id, 'blender_3d_generator', False)
        with self.assertRaises(PermissionError):
            generate_3d_blueprint(
                project_id=self.project.id,
                blueprint_name="Test Blueprint",
                source_filename="blueprint.pdf"
            )

        # When enabled
        set_addon_status(self.project.id, 'blender_3d_generator', True)
        bp_result = generate_3d_blueprint(
            project_id=self.project.id,
            blueprint_name="Test Blueprint Active",
            source_filename="blueprint.pdf"
        )
        self.assertIsNotNone(bp_result.get('model_file_path'))

    def test_04_addon_3_daily_progress_audit_toggle(self):
        """Test Add-On 3 (Daily Progress Tracker & Audit Service)"""
        # When active
        set_addon_status(self.project.id, 'daily_progress_audit', True)
        audit_res = run_daily_progress_audit(self.project.id)
        self.assertTrue(audit_res.get('enabled'))
        self.assertIn('audit_status', audit_res)

        # When disabled
        set_addon_status(self.project.id, 'daily_progress_audit', False)
        audit_res_off = run_daily_progress_audit(self.project.id)
        self.assertFalse(audit_res_off.get('enabled'))

    def test_05_addon_4_failsafe_3day_early_deadline(self):
        """Test Add-On 4 (3-Day Early Deadline Fail-Safe Re-Organization Engine)"""
        set_addon_status(self.project.id, 'early_deadline_failsafe', True)
        
        # Trigger forced fail-safe re-org
        reorg_res = evaluate_and_trigger_failsafe_reorg(self.project.id, force=True)
        self.assertTrue(reorg_res.get('enabled'))
        self.assertTrue(reorg_res.get('triggered'))

        # Check enforced deadline is target_end_date - 3 days
        enforced_deadline_str = (self.target_end - datetime.timedelta(days=3)).isoformat()
        self.assertEqual(reorg_res.get('enforced_deadline'), enforced_deadline_str)
        self.assertGreater(reorg_res.get('days_saved'), 0)

        # Confirm FailSafeReorgLog created
        log_count = FailSafeReorgLog.objects.filter(project_id=self.project.id).count()
        self.assertGreaterEqual(log_count, 1)

    def test_06_rest_api_endpoints(self):
        """Test REST API routes for Add-Ons"""
        session = self.client.session
        session['active_project_id'] = self.project.id
        session.save()

        # GET /api/addons
        response = self.client.get('/api/addons')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

        # POST /api/addons/toggle
        toggle_resp = self.client.post(
            '/api/addons/toggle',
            data=json.dumps({'addon_key': 'blender_3d_generator', 'is_enabled': False}),
            content_type='application/json'
        )
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.json().get('is_enabled'))

        # POST /api/addons/daily-audit
        audit_resp = self.client.get('/api/addons/daily-audit')
        self.assertEqual(audit_resp.status_code, 200)

        # POST /api/addons/failsafe-reorg
        failsafe_resp = self.client.post(
            '/api/addons/failsafe-reorg',
            data=json.dumps({'force': True}),
            content_type='application/json'
        )
        self.assertEqual(failsafe_resp.status_code, 200)
        self.assertTrue(failsafe_resp.json().get('reorg', {}).get('triggered'))


if __name__ == '__main__':
    unittest.main()
