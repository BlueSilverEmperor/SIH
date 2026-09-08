from django.urls import path
from . import views

urlpatterns = [
    # Web views
    path('', views.dashboard_view, name='dashboard'),
    path('master-schedule', views.master_schedule_view, name='master_schedule'),
    path('ingestion', views.ingestion_view, name='ingestion'),
    path('review-queue', views.review_queue_view, name='review_queue'),
    path('analytics', views.analytics_view, name='analytics'),
    path('blueprint-3d', views.blueprint_3d_view, name='blueprint_3d'),
    path('suppliers', views.suppliers_view, name='suppliers'),
    path('addons', views.addons_view, name='addons'),
    path('companion', views.companion_app_view, name='companion'),

    # REST API Endpoints
    path('api/upload', views.api_upload, name='api_upload'),
    path('api/approve-metric/<int:metric_id>', views.api_approve_metric, name='api_approve_metric'),
    path('api/reject-metric/<int:metric_id>', views.api_reject_metric, name='api_reject_metric'),
    path('api/wbs-tasks', views.api_wbs_tasks, name='api_wbs_tasks'),
    path('api/generate-3d-model', views.api_generate_3d_model, name='api_generate_3d_model'),
    path('api/3d-models', views.api_get_3d_models, name='api_get_3d_models'),
    path('api/suppliers', views.api_suppliers, name='api_suppliers'),
    path('api/predictive-forecast', views.api_predictive_forecast, name='api_predictive_forecast'),
    path('api/update-task-schedule', views.api_update_task_schedule, name='api_update_task_schedule'),
    path('api/upload-blueprint', views.api_upload_blueprint, name='api_upload_blueprint'),
    path('api/projects', views.api_create_project, name='api_create_project'),
    path('api/projects/switch', views.api_switch_project, name='api_switch_project'),
    path('api/seed', views.api_seed, name='api_seed'),

    # Add-On Feature Toggle APIs
    path('api/addons', views.api_get_addons, name='api_get_addons'),
    path('api/addons/toggle', views.api_toggle_addon, name='api_toggle_addon'),
    path('api/addons/daily-audit', views.api_daily_audit_trigger, name='api_daily_audit_trigger'),
    path('api/addons/failsafe-reorg', views.api_failsafe_reorg_trigger, name='api_failsafe_reorg_trigger'),
    path('api/addons/weather-hedging', views.api_weather_hedging, name='api_weather_hedging'),
    path('api/addons/voice-log', views.api_voice_log, name='api_voice_log'),

    # Geofenced Companion & QR Attendance APIs
    path('api/attendance/qr-token', views.api_get_qr_token, name='api_get_qr_token'),
    path('api/attendance/check-in-out', views.api_record_attendance, name='api_record_attendance'),
    path('api/attendance/logs', views.api_get_attendance_logs, name='api_get_attendance_logs'),

    # HITL Procurement Review APIs
    path('api/procurement/approve', views.api_approve_procurement, name='api_approve_procurement'),

    # NoSQL File Storage Engine APIs
    path('api/nosql/files', views.api_nosql_files, name='api_nosql_files'),
    path('api/nosql/sync', views.api_nosql_sync, name='api_nosql_sync'),

    # Visual Flowchart Workflow Engine
    path('flowchart', views.flowchart_view, name='flowchart'),
    path('api/flowchart', views.api_get_flowchart, name='api_get_flowchart'),
    path('api/flowchart/rebuild', views.api_rebuild_flowchart, name='api_rebuild_flowchart'),

    # Real-Time CCTV Surveillance & Monitoring Module
    path('cctv', views.cctv_view, name='cctv'),
    path('api/cctv/cameras', views.api_cctv_cameras, name='api_cctv_cameras'),
    path('api/cctv/stream/<int:camera_id>', views.api_cctv_stream, name='api_cctv_stream'),
    path('api/cctv/ai-audit/<int:camera_id>', views.api_cctv_ai_audit, name='api_cctv_ai_audit'),

    # Geofenced Attendance Register Module
    path('attendance', views.attendance_view, name='attendance'),
    path('api/attendance/checkin', views.api_attendance_checkin, name='api_attendance_checkin'),
    path('api/attendance/checkout', views.api_attendance_checkout, name='api_attendance_checkout'),
    path('api/attendance/summary', views.api_attendance_summary, name='api_attendance_summary'),
    path('api/attendance/geofence', views.api_update_geofence, name='api_update_geofence'),

    # Unified Multi-Industry Platform Container Routes
    path('select-industry', views.select_industry_view, name='select_industry'),
    path('plantflow', views.plantflow_view, name='plantflow'),
    path('dockflow', views.dockflow_view, name='dockflow'),
    path('aeroguard', views.aeroguard_view, name='aeroguard'),
    path('turnaroundos', views.turnaroundos_view, name='turnaroundos'),
    path('api/industry/switch', views.api_switch_industry, name='api_switch_industry'),
    path('api/industry/metrics', views.api_industry_metrics, name='api_industry_metrics'),
]






