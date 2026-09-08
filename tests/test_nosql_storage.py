import os
import unittest
import datetime
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constructsync_project.settings')
django.setup()

from django.test import TestCase, Client
from core.models import Project, FieldInput, Blueprint3D
from services.nosql_storage import (
    sanitize_nosql_table_name,
    save_file_to_nosql,
    get_nosql_files_for_project,
    sync_all_project_files_to_nosql
)


class NoSQLStorageEngineTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.today = datetime.date.today()

        self.project = Project.objects.create(
            name="Metro Tower Phase 2",
            code="PRJ-METRO-002",
            description="Metro tower infrastructure project.",
            total_budget=800000.0,
            status="active"
        )

        # Create sample field input (Invoice PDF)
        self.field_input = FieldInput.objects.create(
            project=self.project,
            input_type="invoice_pdf",
            file_path="static/uploads/invoices/sample_inv.pdf",
            original_filename="sample_inv.pdf",
            notes="Steel rebar supplier invoice #1042",
            source_author="Vendor SteelCo",
            status="pending_review"
        )

        # Create sample 3D Blueprint model
        self.blueprint = Blueprint3D.objects.create(
            project=self.project,
            name="Metro Tower 3D Mesh",
            source_filename="blueprint_architectural.pdf",
            wall_count=18,
            column_count=24,
            slab_area_sqm=650.0,
            model_file_path="static/models/3d_blueprints/bp_proj_test.obj",
            format="obj",
            status="generated"
        )

    def test_01_nosql_table_name_generation(self):
        """Test NoSQL collection/table name matches project name"""
        table_name = sanitize_nosql_table_name(self.project.name)
        self.assertEqual(table_name, "Metro_Tower_Phase_2")

    def test_02_save_invoice_and_photo_to_nosql(self):
        """Test saving invoice, photo, and 3D model into project NoSQL table"""
        # Save invoice file to NoSQL
        inv_res = save_file_to_nosql(
            project_id=self.project.id,
            relative_file_path="static/uploads/invoices/sample_inv.pdf",
            file_category="invoice_pdf",
            original_filename="sample_inv.pdf",
            notes="Invoice PDF payload test"
        )
        self.assertTrue(inv_res.get('success'))
        self.assertEqual(inv_res.get('table_name'), "Metro_Tower_Phase_2")

        # Save photo file to NoSQL
        photo_res = save_file_to_nosql(
            project_id=self.project.id,
            relative_file_path="static/uploads/photos/site_foundation.jpg",
            file_category="photo",
            original_filename="site_foundation.jpg",
            notes="Site foundation photo"
        )
        self.assertTrue(photo_res.get('success'))

        # Fetch all files for project table
        files = get_nosql_files_for_project(self.project.id)
        self.assertGreaterEqual(len(files), 2)

    def test_03_batch_project_sync_to_nosql(self):
        """Test batch synchronization of all project files to NoSQL"""
        sync_res = sync_all_project_files_to_nosql(self.project.id)
        self.assertTrue(sync_res.get('success'))
        self.assertEqual(sync_res.get('table_name'), "Metro_Tower_Phase_2")
        self.assertGreaterEqual(sync_res.get('synced_count'), 2)

    def test_04_rest_api_nosql_endpoints(self):
        """Test GET /api/nosql/files and POST /api/nosql/sync APIs"""
        session = self.client.session
        session['active_project_id'] = self.project.id
        session.save()

        # Sync API
        sync_resp = self.client.post('/api/nosql/sync')
        self.assertEqual(sync_resp.status_code, 200)
        self.assertTrue(sync_resp.json().get('success'))

        # Files API
        files_resp = self.client.get('/api/nosql/files')
        self.assertEqual(files_resp.status_code, 200)
        data = files_resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('nosql_table_name'), "Metro_Tower_Phase_2")
        self.assertGreaterEqual(data.get('count'), 2)


if __name__ == '__main__':
    unittest.main()
