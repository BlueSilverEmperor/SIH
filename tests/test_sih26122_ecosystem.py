import os
import django
from django.test import TestCase, Client
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from core.models import (
    Project, WBSTask, BoMComponent, DrydockBerth, ITARVendorAudit, TurnaroundShutdown, Supplier
)
from services.multi_industry_engine import (
    get_plantflow_metrics, get_dockflow_metrics, get_aeroguard_metrics, get_turnaroundos_metrics
)
from seed import seed_database


class SIH26122EcosystemTestCase(TestCase):
    """
    Comprehensive integration test suite verifying SIH26122 seed data integrity and workspace routing across all 5 sub-apps.
    """

    def setUp(self):
        self.client = Client()
        seed_database()
        self.project = Project.objects.first()

    def test_constructflow_sih26122_baseline(self):
        """Verify ConstructFlow AI Apex Commercial Tower Phase 2 project & WBS baseline."""
        self.assertIsNotNone(self.project)
        self.assertIn("Apex Commercial Tower Phase 2", self.project.name)
        self.assertEqual(self.project.total_budget, 14200000.0)

        tasks = WBSTask.objects.filter(project=self.project)
        self.assertGreaterEqual(tasks.count(), 2)

        foundation_task = tasks.filter(task_name__icontains="Foundation").first()
        self.assertIsNotNone(foundation_task)
        self.assertEqual(foundation_task.actual_quantity, 1200.0)

        rebar_task = tasks.filter(task_name__icontains="Rebar").first()
        self.assertIsNotNone(rebar_task)
        self.assertIn("Grade 60", rebar_task.task_name)

    def test_plantflow_sih26122_ev_assembly_line(self):
        """Verify PlantFlow AI Automated EV Assembly Line A & SKU-ST-882 telemetry."""
        metrics = get_plantflow_metrics(self.project.id)
        self.assertGreaterEqual(metrics['total_bom_items'], 1)

        stator = BoMComponent.objects.filter(part_number="SKU-ST-882").first()
        self.assertIsNotNone(stator)
        self.assertEqual(stator.daily_target_units, 500.0)
        self.assertEqual(stator.active_phase, "Stator Winding Active")
        self.assertEqual(stator.status, "optimal")

    def test_dockflow_sih26122_vessel_hull409(self):
        """Verify DockFlow AI Offshore Patrol Vessel Hull #409 & Berth 3 telemetry."""
        metrics = get_dockflow_metrics(self.project.id)
        self.assertGreaterEqual(metrics['total_drydock_berths'], 1)

        hull = DrydockBerth.objects.filter(hull_number="Hull #409").first()
        self.assertIsNotNone(hull)
        self.assertEqual(hull.berth_code, "BERTH-03")
        self.assertEqual(hull.steel_tonnage, 800.0)
        self.assertIn("DH36", hull.steel_grade)
        self.assertEqual(hull.main_deck_welding_pct, 74.0)

    def test_aeroguard_sih26122_batch7_itar_audit(self):
        """Verify AeroGuard AI Batch VII Avionic Telemetry Housing ITAR Level 3 audit."""
        metrics = get_aeroguard_metrics(self.project.id)
        self.assertGreaterEqual(metrics['total_itar_audited_vendors'], 1)

        audit = ITARVendorAudit.objects.filter(batch_code="Batch VII").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.itar_level, "ITAR Level 3")
        self.assertIn("Titanium Ti-6Al-4V", audit.material_billet_type)
        self.assertEqual(audit.metallurgical_audit_status, "Passed")

    def test_turnaroundos_sih26122_cdu_catalyst_regeneration(self):
        """Verify TurnaroundOS AI CDU Catalyst Regeneration 96-hr window shutdown."""
        metrics = get_turnaroundos_metrics(self.project.id)
        self.assertGreaterEqual(metrics['total_shutdown_units'], 1)

        cdu = TurnaroundShutdown.objects.filter(unit_name__icontains="Crude Distillation").first()
        self.assertIsNotNone(cdu)
        self.assertEqual(cdu.turnaround_window_hours, 96)
        self.assertEqual(cdu.catalyst_pellet_type, "Type-V Catalyst Pellets")
        self.assertEqual(cdu.purge_status, "Reactor Purge Complete")

    def test_industry_selector_and_workspace_routes(self):
        """Verify industry selection portal and workspace route HTTP responses."""
        resp_select = self.client.get('/select-industry')
        self.assertEqual(resp_select.status_code, 200)

        routes = ['/', '/plantflow', '/dockflow', '/aeroguard', '/turnaroundos']
        for route in routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Failed to load workspace route {route}")
