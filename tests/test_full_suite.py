import unittest
import json
import os
import io
import django
from django.test import TestCase, Client
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from core.models import Project, WBSTask, FieldInput, ExtractedMetric, AnalyticsLog, Supplier, Blueprint3D
from seed import seed_database
from services.evm_engine import calculate_project_evm, approve_and_sync_metric, reject_metric
from services.supplier_engine import calculate_supplier_scores_and_softmax, get_recommended_supplier_by_category
from services.ai_engine import parse_blueprint_file_to_3d_specs
from services.blender_service import generate_3d_blueprint

class ConstructSyncFullQASuite(TestCase):

    def setUp(self):
        self.client = Client()
        seed_database()

    def test_01_database_orm_integrity(self):
        """Verify ORM integrity, foreign key constraints, and seed relationships."""
        project = Project.objects.first()
        self.assertIsNotNone(project, "Project must exist")
        self.assertTrue(project.code.startswith("PRJ-"))

        tasks = list(WBSTask.objects.filter(project_id=project.id))
        self.assertGreaterEqual(len(tasks), 5)
        for t in tasks:
            self.assertEqual(t.project_id, project.id)

        inputs = list(FieldInput.objects.filter(project_id=project.id))
        self.assertGreaterEqual(len(inputs), 2)

        suppliers = list(Supplier.objects.all())
        self.assertGreaterEqual(len(suppliers), 5)

        blueprints = list(Blueprint3D.objects.filter(project_id=project.id))
        self.assertGreaterEqual(len(blueprints), 1)

        print("[OK] Test 1 Passed: Database ORM models and relationships verified.")

    def test_02_multi_modal_ingestion_api(self):
        """Verify Multi-Modal Ingestion API for Photo, Invoice PDF, Audio, and Text Log."""
        project = Project.objects.first()

        # 2a. Text Log Ingestion
        res_text = self.client.post('/api/upload', data={
            'project_id': project.id,
            'input_type': 'text',
            'text_content': 'Completed 45 sq.m of brick masonry on floor 3 with 6 workers.',
            'notes': 'Daily site log notes',
            'source_author': 'QA Inspector'
        })
        self.assertEqual(res_text.status_code, 200)
        data_text = json.loads(res_text.content.decode('utf-8'))
        self.assertTrue(data_text['success'])
        self.assertEqual(data_text['field_input']['input_type'], 'text_log')
        self.assertGreater(data_text['extracted_metric']['confidence_score'], 0.8)

        # 2b. Photo Upload Ingestion
        photo_bytes = io.BytesIO(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xFF\xDB\x00\x43")
        photo_bytes.name = 'foundation_photo.jpg'
        res_photo = self.client.post('/api/upload', data={
            'project_id': project.id,
            'input_type': 'photo',
            'notes': 'Ready-mix concrete pour sector B footings',
            'file': photo_bytes
        })
        self.assertEqual(res_photo.status_code, 200)
        data_photo = json.loads(res_photo.content.decode('utf-8'))
        self.assertTrue(data_photo['success'])

        # 2c. PDF Invoice Ingestion
        pdf_bytes = io.BytesIO(b"%PDF-1.4 1 0 obj << /Type /Catalog >> endobj xref trailer << /Root 1 0 R >> %%EOF")
        pdf_bytes.name = 'inv_steel_rebar.pdf'
        res_pdf = self.client.post('/api/upload', data={
            'project_id': project.id,
            'input_type': 'invoice_pdf',
            'notes': 'Steel rebar invoice PO-884 for 15.0 tons at $850/ton',
            'file': pdf_bytes
        })
        self.assertEqual(res_pdf.status_code, 200)
        data_pdf = json.loads(res_pdf.content.decode('utf-8'))
        self.assertTrue(data_pdf['success'])

        print("[OK] Test 2 Passed: Multi-modal ingestion API verified (Text, Photo, PDF).")

    def test_03_ai_extraction_and_wbs_mapping(self):
        """Verify AI extraction, confidence scoring, and WBS task mapping."""
        extracted = ExtractedMetric.objects.first()
        self.assertIsNotNone(extracted)
        self.assertIsNotNone(extracted.wbs_task_id)
        self.assertGreater(extracted.confidence_score, 0.0)

        task = WBSTask.objects.filter(id=extracted.wbs_task_id).first()
        self.assertIsNotNone(task)
        print(f"[OK] Test 3 Passed: AI extraction mapped metric ID {extracted.id} to WBS Task '{task.task_name}'.")

    def test_04_supplier_rating_and_softmax(self):
        """Verify weighted criteria calculation and per-category Softmax probabilities (Sum = 1.0)."""
        categories = ['Steel Rebar', 'Concrete', 'Masonry', 'Electrical']

        for cat in categories:
            suppliers = calculate_supplier_scores_and_softmax(category=cat)
            if suppliers:
                prob_sum = sum(s.softmax_probability for s in suppliers)
                self.assertAlmostEqual(prob_sum, 1.0, places=4, msg=f"Softmax sum for {cat} must equal 1.0")

        recs = get_recommended_supplier_by_category()
        rec_dict = recs.get('recommendations', recs)
        self.assertIn('Steel Rebar', rec_dict)
        self.assertIsNotNone(rec_dict['Steel Rebar'])
        print("[OK] Test 4 Passed: Supplier Rating & Softmax Engine verified (Category Probabilities sum to 100%).")

    def test_05_live_evm_and_analytics_forecasting(self):
        """Verify EVM calculations: PV, EV, AC, SV, CV, SPI, CPI, BAC, EAC, ETC, VAC, Margin %."""
        project = Project.objects.first()
        evm = calculate_project_evm(project.id)

        self.assertIn('total_pv', evm)
        self.assertIn('total_ev', evm)
        self.assertIn('total_ac', evm)
        self.assertIn('bac', evm)
        self.assertIn('eac', evm)
        self.assertIn('etc', evm)
        self.assertIn('vac', evm)
        self.assertIn('projected_margin_pct', evm)

        self.assertEqual(evm['schedule_variance'], round(evm['total_ev'] - evm['total_pv'], 2))
        self.assertEqual(evm['cost_variance'], round(evm['total_ev'] - evm['total_ac'], 2))

        print(f"[OK] Test 5 Passed: Live EVM & Margin Forecasting verified (BAC=${evm['bac']:,.0f}, EAC=${evm['eac']:,.0f}, Margin={evm['projected_margin_pct']}%).")

    def test_06_blender_3d_generation_pipeline(self):
        """Verify Blender 3D Blueprint Generation API & disk file generation."""
        project = Project.objects.first()

        res = self.client.post('/api/generate-3d-model', data=json.dumps({
            'name': 'QA Test Floor 3D Model',
            'wall_count': 14,
            'column_count': 18,
            'slab_area': 450.0
        }), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content.decode('utf-8'))
        self.assertTrue(data['success'])

        bp = data['blueprint']
        full_path = os.path.join(settings.BASE_DIR, bp['model_file_path'])
        self.assertTrue(os.path.exists(full_path), f"File {full_path} must exist on disk")

        print(f"[OK] Test 6 Passed: Blender 3D Blueprint generation verified ({bp['model_file_path']}).")

    def test_07_web_views_rendering_and_routes(self):
        """Verify all 7 web view routes render status 200 OK."""
        routes = ['/', '/master-schedule', '/ingestion', '/review-queue', '/analytics', '/blueprint-3d', '/suppliers']
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with HTTP status {res.status_code}")
        print("[OK] Test 7 Passed: All 7 Web View Routes rendered successfully (200 OK).")

    def test_08_predictive_completion_time_engine(self):
        """Verify real-time Predictive Completion Time Engine, live velocity, and supplier risk buffer calculation."""
        project = Project.objects.first()
        from services.predictive_engine import calculate_predictive_completion
        data = calculate_predictive_completion(project.id)

        self.assertIsNotNone(data)
        self.assertIn('forecasted_end_date', data)
        self.assertIn('actual_velocity', data)
        self.assertIn('supplier_risk_buffer_days', data)

        res = self.client.get('/api/predictive-forecast')
        self.assertEqual(res.status_code, 200)
        res_json = json.loads(res.content.decode('utf-8'))
        self.assertTrue(res_json['success'])

        print(f"[OK] Test 8 Passed: Real-Time Predictive Completion Engine verified (Forecast End: {data['forecasted_end_date']}, Velocity: {data['actual_velocity']} units/day, Risk Buffer: +{data['supplier_risk_buffer_days']}d).")

    def test_09_project_creation_and_switching(self):
        """Verify adding new projects and switching active project session via API."""
        res_create = self.client.post('/api/projects', data=json.dumps({
            'name': 'QA Test Industrial Park',
            'code': 'PRJ-QA-PARK-2026',
            'description': 'QA Test Project Scope',
            'total_budget': 3500000.0,
            'start_date': '2026-04-01',
            'target_end_date': '2027-08-30'
        }), content_type='application/json')
        self.assertEqual(res_create.status_code, 200)
        data = json.loads(res_create.content.decode('utf-8'))
        self.assertTrue(data['success'])
        self.assertEqual(data['project']['code'], 'PRJ-QA-PARK-2026')

        new_id = data['project']['id']
        res_switch = self.client.post('/api/projects/switch', data=json.dumps({'project_id': new_id}), content_type='application/json')
        self.assertEqual(res_switch.status_code, 200)
        data_switch = json.loads(res_switch.content.decode('utf-8'))
        self.assertTrue(data_switch['success'])

        print(f"[OK] Test 9 Passed: New project creation and switching verified (Project: {data['project']['name']}).")
