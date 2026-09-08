import os
import unittest
import datetime
import json
import django
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from django.test import TestCase, Client
from core.models import Project, WBSTask, Blueprint3D, Supplier
from services.blueprint_cost_engine import calculate_blueprint_cost_and_takeoffs
from services.resource_allocation_engine import allocate_resources_and_suppliers_for_project
from services.blueprint_pipeline import execute_full_blueprint_pipeline


class BlueprintPipelineTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = datetime.date.today()

        # Create base project
        self.project = Project.objects.create(
            name="Commercial Tower Blueprint Test",
            code="PRJ-BP-TEST",
            description="Testing automated blueprint ingestion pipeline.",
            total_budget=1000000.0,
            start_date=self.today,
            target_end_date=self.today + datetime.timedelta(days=180),
            status="active"
        )

        # Create sample suppliers
        self.sup_concrete = Supplier.objects.create(
            name="Apex Concrete Supplies",
            category="Concrete",
            tco_score=90.0,
            delivery_score=92.0,
            quality_score=95.0
        )
        self.sup_steel = Supplier.objects.create(
            name="Vanguard Steel Rebar",
            category="Steel Rebar",
            tco_score=88.0,
            delivery_score=90.0,
            quality_score=94.0
        )

    def test_01_blueprint_cost_and_takeoffs_engine(self):
        """Test material takeoff & cost estimation calculation"""
        specs = {
            'slab_area': 600.0,
            'wall_count': 20,
            'column_count': 24,
            'stories': 3,
            'building_type': 'commercial_tower'
        }
        res = calculate_blueprint_cost_and_takeoffs(self.project.id, specs)

        self.assertTrue(res.get('success'))
        self.assertIn('takeoffs', res)
        self.assertIn('financials', res)
        self.assertGreater(res['takeoffs']['concrete_qty_cum'], 0)
        self.assertGreater(res['takeoffs']['steel_qty_tons'], 0)
        self.assertGreater(res['financials']['total_estimated_budget'], 0)

    def test_02_smart_resource_allocation_engine(self):
        """Test resource ordering and supplier allocation"""
        specs = {'slab_area': 600.0, 'wall_count': 20, 'column_count': 24, 'stories': 3}
        calculate_blueprint_cost_and_takeoffs(self.project.id, specs)

        res = allocate_resources_and_suppliers_for_project(self.project.id)

        self.assertTrue(res.get('success'))
        self.assertGreater(res.get('allocated_tasks_count'), 0)
        
        # Verify tasks have assigned suppliers
        tasks = WBSTask.objects.filter(project_id=self.project.id)
        assigned_tasks = [t for t in tasks if t.assigned_supplier is not None]
        self.assertGreaterEqual(len(assigned_tasks), 1)


    def test_03_master_blueprint_pipeline_orchestration(self):
        """Test full pipeline execution: Upload -> Parse -> Cost -> Resource -> 3D -> Flowchart"""
        # Create a dummy blueprint file
        upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'blueprints')
        os.makedirs(upload_dir, exist_ok=True)
        sample_path = os.path.join(upload_dir, 'sample_architectural_plan.txt')
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write("Commercial Tower Blueprint Specs: 750 sqm area, 22 walls, 28 columns, 4 stories.")

        rel_path = 'static/uploads/blueprints/sample_architectural_plan.txt'
        res = execute_full_blueprint_pipeline(self.project.id, rel_path, 'sample_architectural_plan.txt')

        self.assertTrue(res.get('success'))
        self.assertEqual(res.get('project_id'), self.project.id)
        self.assertIn('cost_estimation', res)
        self.assertIn('resource_allocation', res)
        self.assertIn('flowchart', res)

    def test_04_rest_api_blueprint_upload(self):
        """Test multipart POST /api/upload-blueprint request.FILES handling"""
        session = self.client.session
        session['active_project_id'] = self.project.id
        session.save()

        dummy_pdf = SimpleUploadedFile("architectural_drawing.pdf", b"%PDF-1.4 sample blueprint data content", content_type="application/pdf")

        response = self.client.post(
            '/api/upload-blueprint',
            {'blueprint_file': dummy_pdf}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('pipeline', data)
        self.assertTrue(data['pipeline'].get('success'))


if __name__ == '__main__':
    unittest.main()
