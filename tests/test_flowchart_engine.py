import os
import unittest
import datetime
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from django.test import TestCase, Client
from core.models import Project, WBSTask, FailSafeReorgLog
from services.addon_manager import set_addon_status, is_addon_enabled
from services.flowchart_engine import generate_project_flowchart
from services.failsafe_engine import evaluate_and_trigger_failsafe_reorg


class FlowchartEngineTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = datetime.date.today()
        self.target_end = self.today + datetime.timedelta(days=120)

        self.project = Project.objects.create(
            name="Skyline Plaza Phase 3",
            code="PRJ-PLAZA-003",
            description="Multi-tier commercial plaza project.",
            total_budget=1200000.0,
            start_date=self.today - datetime.timedelta(days=10),
            target_end_date=self.target_end,
            status="active"
        )

        # Create standard WBS tasks matching phase definitions
        self.task1 = WBSTask.objects.create(
            project=self.project,
            wbs_code="1.1",
            task_name="Site Excavation & Trenching",
            planned_quantity=200.0,
            actual_quantity=200.0,  # 100% completed
            unit="cu.m",
            unit_cost=40.0,
            is_critical_path=True,
            planned_start_date=self.today - datetime.timedelta(days=10),
            planned_end_date=self.today
        )
        self.task1.calculate_evm()
        self.task1.save()

        self.task2 = WBSTask.objects.create(
            project=self.project,
            wbs_code="1.2",
            task_name="Concrete Foundation & Slab Pouring",
            planned_quantity=150.0,
            actual_quantity=30.0,  # 20% in progress
            unit="cu.m",
            unit_cost=160.0,
            is_critical_path=True,
            planned_start_date=self.today,
            planned_end_date=self.target_end
        )
        self.task2.calculate_evm()
        self.task2.save()

    def test_01_flowchart_generation(self):
        """Test dynamic flowchart node & edge generation"""
        set_addon_status(self.project.id, 'visual_flowchart_workflow', True)
        chart = generate_project_flowchart(self.project.id)

        self.assertTrue(chart.get('enabled'))
        self.assertGreaterEqual(len(chart.get('nodes', [])), 6)
        self.assertGreaterEqual(len(chart.get('edges', [])), 5)

        # Check phase status
        nodes = chart.get('nodes', [])
        phase1 = next((n for n in nodes if n['id'] == 'phase_1'), None)
        self.assertIsNotNone(phase1)
        self.assertEqual(phase1['status'], 'completed')

        phase2 = next((n for n in nodes if n['id'] == 'phase_2'), None)
        self.assertIsNotNone(phase2)
        self.assertEqual(phase2['status'], 'in_progress')

    def test_02_failsafe_rerouting_flowchart_binding(self):
        """Test fail-safe emergency re-routing dynamically updating flowchart nodes"""
        set_addon_status(self.project.id, 'visual_flowchart_workflow', True)
        set_addon_status(self.project.id, 'early_deadline_failsafe', True)

        # Trigger fail-safe re-org
        reorg_res = evaluate_and_trigger_failsafe_reorg(self.project.id, force=True)
        self.assertTrue(reorg_res.get('triggered'))

        # Check flowchart graph reflects crashed node
        chart = generate_project_flowchart(self.project.id)
        self.assertTrue(chart.get('summary', {}).get('failsafe_rerouted'))

        crashed_nodes = [n for n in chart.get('nodes', []) if n.get('is_crashed')]
        self.assertGreaterEqual(len(crashed_nodes), 1)

    def test_03_flowchart_addon_toggle(self):
        """Test visual flowchart add-on on/off behavior"""
        set_addon_status(self.project.id, 'visual_flowchart_workflow', False)
        chart_off = generate_project_flowchart(self.project.id)
        self.assertFalse(chart_off.get('enabled'))

    def test_04_rest_api_flowchart_endpoints(self):
        """Test GET /api/flowchart and POST /api/flowchart/rebuild APIs"""
        session = self.client.session
        session['active_project_id'] = self.project.id
        session.save()

        # GET /api/flowchart
        resp = self.client.get('/api/flowchart')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))

        # POST /api/flowchart/rebuild
        rebuild_resp = self.client.post('/api/flowchart/rebuild')
        self.assertEqual(rebuild_resp.status_code, 200)
        self.assertTrue(rebuild_resp.json().get('success'))


if __name__ == '__main__':
    unittest.main()
