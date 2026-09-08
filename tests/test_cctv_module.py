import json
from django.test import TestCase, Client
from core.models import Project, WBSTask, CCTVCamera, CCTVStreamLog
from services.cctv_streaming_service import (
    generate_cctv_stream_token,
    verify_cctv_stream_token,
    generate_camera_frame_jpeg,
    audit_camera_feed_with_ai
)


class CCTVModuleTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.project = Project.objects.create(
            name="Test Construction Project",
            code="PRJ-TEST-001",
            total_budget=500000.0,
            status="active"
        )

        self.wbs_task = WBSTask.objects.create(
            project=self.project,
            wbs_code="1.1",
            task_name="Foundation Excavation",
            planned_quantity=100.0,
            actual_quantity=60.0,
            unit="cu.m",
            unit_cost=50.0,
            actual_cost=3000.0,
            is_critical_path=True
        )

        self.camera = CCTVCamera.objects.create(
            project=self.project,
            name="Zone A Excavation Cam",
            camera_code="CAM-TEST-A",
            location_tag="Zone A",
            rtsp_url="rtsp://admin:pass@192.168.1.50:554/stream",
            stream_type="mjpg",
            resolution="1080p",
            fps=30,
            status="online",
            associated_wbs_task=self.wbs_task
        )

    def test_cctv_camera_model_to_dict(self):
        cam_dict = self.camera.to_dict()
        self.assertEqual(cam_dict['camera_code'], "CAM-TEST-A")
        self.assertEqual(cam_dict['location_tag'], "Zone A")
        self.assertEqual(cam_dict['associated_wbs_task_id'], self.wbs_task.id)

    def test_cctv_stream_token_generation_and_verification(self):
        token_info = generate_cctv_stream_token(self.camera.id, client_ip='127.0.0.1')
        token_str = token_info['token']
        self.assertTrue(token_str.startswith("CCTV_STREAM|CAM_"))

        # Verify valid token
        is_valid = verify_cctv_stream_token(self.camera.id, token_str, client_ip='127.0.0.1')
        self.assertTrue(is_valid)

        # Verify invalid token for wrong camera_id
        is_invalid_cam = verify_cctv_stream_token(999, token_str)
        self.assertFalse(is_invalid_cam)

        # Verify tampered token signature
        tampered_token = token_str[:-4] + "ffff"
        is_invalid_sig = verify_cctv_stream_token(self.camera.id, tampered_token)
        self.assertFalse(is_invalid_sig)

    def test_generate_camera_frame_jpeg(self):
        jpeg_bytes = generate_camera_frame_jpeg(self.camera, frame_count=1)
        self.assertTrue(isinstance(jpeg_bytes, bytes))
        # JPEG header check: 0xFF 0xD8
        self.assertEqual(jpeg_bytes[:2], b'\xff\xd8')

    def test_audit_camera_feed_with_ai(self):
        audit = audit_camera_feed_with_ai(self.camera.id)
        self.assertEqual(audit['camera_code'], "CAM-TEST-A")
        self.assertEqual(audit['associated_task_id'], self.wbs_task.id)
        self.assertIn('ai_visual_progress_pct', audit)
        self.assertIn('ppe_compliance_rate_pct', audit)
        self.assertTrue(len(audit['ai_recommendations']) > 0)

    def test_cctv_web_view_rendering(self):
        response = self.client.get('/cctv')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CAM-TEST-A")
        self.assertContains(response, "Zone A Excavation Cam")

    def test_api_cctv_cameras_get_and_post(self):
        # GET list cameras
        response = self.client.get('/api/cctv/cameras')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)

        # POST register new camera
        new_cam_data = {
            'name': 'Zone B Concrete Cam',
            'camera_code': 'CAM-TEST-B',
            'location_tag': 'Zone B',
            'rtsp_url': 'rtsp://admin:pass@192.168.1.51:554/stream',
            'stream_type': 'mjpg',
            'resolution': '4K',
            'fps': 60,
            'associated_wbs_task_id': self.wbs_task.id
        }
        response = self.client.post(
            '/api/cctv/cameras',
            data=json.dumps(new_cam_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        post_res = json.loads(response.content.decode('utf-8'))
        self.assertTrue(post_res['success'])
        self.assertEqual(post_res['camera']['camera_code'], 'CAM-TEST-B')

    def test_api_cctv_stream_endpoint_security(self):
        token_info = generate_cctv_stream_token(self.camera.id)
        valid_token = token_info['token']

        # Request with valid token
        response = self.client.get(f'/api/cctv/stream/{self.camera.id}?token={valid_token}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)

        # Request with invalid token -> 403 Forbidden
        response_invalid = self.client.get(f'/api/cctv/stream/{self.camera.id}?token=invalid_token_123')
        self.assertEqual(response_invalid.status_code, 403)

    def test_api_cctv_ai_audit_endpoint(self):
        response = self.client.get(f'/api/cctv/ai-audit/{self.camera.id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['success'])
        self.assertEqual(data['audit']['camera_code'], 'CAM-TEST-A')
