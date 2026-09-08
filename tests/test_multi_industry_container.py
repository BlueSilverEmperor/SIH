import json
from django.test import TestCase, Client
from core.models import (
    Project, Supplier, CCTVCamera,
    BoMComponent, DrydockBerth, ITARVendorAudit, TurnaroundShutdown
)
from services.multi_industry_engine import (
    INDUSTRIES,
    get_industry_details,
    get_all_industries,
    get_plantflow_metrics,
    get_dockflow_metrics,
    get_aeroguard_metrics,
    get_turnaroundos_metrics
)


class MultiIndustryContainerTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.project = Project.objects.create(
            name="Multi-Industry Test Complex",
            code="PRJ-IND-901",
            total_budget=2000000.0,
            industry_sector="constructflow",
            status="active"
        )

        self.supplier = Supplier.objects.create(
            name="AeroDefense Alloy Components",
            category="Specialized Alloy",
            weighted_score=92.5
        )

        self.camera = CCTVCamera.objects.create(
            project=self.project,
            name="Drydock Telemetry Cam 1",
            camera_code="CAM-DOCK-1",
            location_tag="Berth 01"
        )

        self.bom_comp = BoMComponent.objects.create(
            project=self.project,
            part_number="PN-ENG-101",
            component_name="Turbine Rotor Shaft",
            workstation="Machining Bay 1",
            bom_quantity=100.0,
            target_line_rate_units_hr=50.0,
            actual_line_rate_units_hr=48.0,
            status="optimal"
        )

        self.berth = DrydockBerth.objects.create(
            project=self.project,
            berth_code="DRYDOCK-01",
            vessel_name="SS Titan Mariner",
            hull_section="Section A Bow",
            docking_status="docked",
            completion_percentage=75.0,
            telemetry_camera=self.camera
        )

        self.itar_audit = ITARVendorAudit.objects.create(
            project=self.project,
            supplier=self.supplier,
            itar_registration_number="ITAR-REG-991",
            clearance_level="Top Secret",
            audit_status="compliant",
            compliance_score=99.5
        )

        self.turnaround = TurnaroundShutdown.objects.create(
            project=self.project,
            unit_name="Crude Unit 1",
            shutdown_phase="overhaul",
            hot_work_permits_count=6,
            flare_stack_status="normal",
            hazard_level="low",
            completion_percentage=60.0
        )

    def test_multi_industry_registry(self):
        all_ind = get_all_industries()
        self.assertEqual(len(all_ind), 5)
        
        details = get_industry_details('plantflow')
        self.assertEqual(details['name'], 'PlantFlow AI')
        self.assertEqual(details['route'], '/plantflow')

    def test_domain_model_to_dict(self):
        bom_d = self.bom_comp.to_dict()
        self.assertEqual(bom_d['part_number'], "PN-ENG-101")
        self.assertEqual(bom_d['efficiency_pct'], 96.0)

        berth_d = self.berth.to_dict()
        self.assertEqual(berth_d['vessel_name'], "SS Titan Mariner")
        self.assertEqual(berth_d['telemetry_camera_id'], self.camera.id)

        itar_d = self.itar_audit.to_dict()
        self.assertEqual(itar_d['itar_registration_number'], "ITAR-REG-991")

        ta_d = self.turnaround.to_dict()
        self.assertEqual(ta_d['unit_name'], "Crude Unit 1")

    def test_industry_analytics_calculators(self):
        plant_m = get_plantflow_metrics(self.project.id)
        self.assertEqual(plant_m['total_bom_items'], 1)

        dock_m = get_dockflow_metrics(self.project.id)
        self.assertEqual(dock_m['total_drydock_berths'], 1)

        aero_m = get_aeroguard_metrics(self.project.id)
        self.assertEqual(aero_m['total_itar_audited_vendors'], 1)

        ta_m = get_turnaroundos_metrics(self.project.id)
        self.assertEqual(ta_m['total_shutdown_units'], 1)

    def test_select_industry_gate_rendering(self):
        response = self.client.get('/select-industry')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ConstructFlow AI")
        self.assertContains(response, "PlantFlow AI")
        self.assertContains(response, "DockFlow AI")
        self.assertContains(response, "AeroGuard AI")
        self.assertContains(response, "TurnaroundOS AI")

    def test_sub_app_views_rendering(self):
        # 1. ConstructFlow (Default /)
        res1 = self.client.get('/')
        self.assertEqual(res1.status_code, 200)

        # 2. PlantFlow (/plantflow)
        res2 = self.client.get('/plantflow')
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "PlantFlow AI")

        # 3. DockFlow (/dockflow)
        res3 = self.client.get('/dockflow')
        self.assertEqual(res3.status_code, 200)
        self.assertContains(res3, "DockFlow AI")

        # 4. AeroGuard (/aeroguard)
        res4 = self.client.get('/aeroguard')
        self.assertEqual(res4.status_code, 200)
        self.assertContains(res4, "AeroGuard AI")

        # 5. TurnaroundOS (/turnaroundos)
        res5 = self.client.get('/turnaroundos')
        self.assertEqual(res5.status_code, 200)
        self.assertContains(res5, "TurnaroundOS AI")

    def test_api_industry_switch_and_metrics(self):
        # 1. Switch Industry API
        payload = {'industry_key': 'dockflow'}
        res_switch = self.client.post(
            '/api/industry/switch',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res_switch.status_code, 200)
        data_s = json.loads(res_switch.content.decode('utf-8'))
        self.assertTrue(data_s['success'])
        self.assertEqual(data_s['target_route'], '/dockflow')

        # 2. Industry Metrics API
        res_m = self.client.get('/api/industry/metrics?industry_key=dockflow')
        self.assertEqual(res_m.status_code, 200)
        data_m = json.loads(res_m.content.decode('utf-8'))
        self.assertTrue(data_m['success'])
        self.assertEqual(data_m['metrics']['total_drydock_berths'], 1)
