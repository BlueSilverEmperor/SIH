from django.contrib import admin
from .models import Project, Supplier, WBSTask, FieldInput, ExtractedMetric, AnalyticsLog, Blueprint3D, CCTVCamera, CCTVStreamLog, AttendanceRecord, BoMComponent, DrydockBerth, ITARVendorAudit, TurnaroundShutdown

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'total_budget', 'industry_sector', 'predictive_status', 'status', 'created_at')
    search_fields = ('code', 'name')
    list_filter = ('industry_sector', 'status', 'predictive_status')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'weighted_score', 'softmax_probability', 'status')
    search_fields = ('name', 'category')
    list_filter = ('category', 'status')

@admin.register(WBSTask)
class WBSTaskAdmin(admin.ModelAdmin):
    list_display = ('wbs_code', 'task_name', 'project', 'planned_value', 'earned_value', 'completion_percentage', 'status')
    search_fields = ('wbs_code', 'task_name')
    list_filter = ('status', 'is_critical_path', 'project')

@admin.register(FieldInput)
class FieldInputAdmin(admin.ModelAdmin):
    list_display = ('input_type', 'project', 'source_author', 'status', 'uploaded_at')
    search_fields = ('original_filename', 'notes', 'source_author')
    list_filter = ('input_type', 'status', 'project')

@admin.register(ExtractedMetric)
class ExtractedMetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'detected_material', 'extracted_quantity', 'unit', 'confidence_score', 'status')
    search_fields = ('detected_material', 'ai_reasoning')
    list_filter = ('status', 'unit')

@admin.register(AnalyticsLog)
class AnalyticsLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'snapshot_date', 'total_pv', 'total_ev', 'total_ac', 'spi', 'cpi')
    list_filter = ('project',)

@admin.register(Blueprint3D)
class Blueprint3DAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'wall_count', 'column_count', 'format', 'status', 'created_at')
    list_filter = ('format', 'status', 'project')

@admin.register(CCTVCamera)
class CCTVCameraAdmin(admin.ModelAdmin):
    list_display = ('camera_code', 'name', 'location_tag', 'stream_type', 'status', 'project')
    search_fields = ('camera_code', 'name', 'location_tag')
    list_filter = ('stream_type', 'status', 'project')

@admin.register(CCTVStreamLog)
class CCTVStreamLogAdmin(admin.ModelAdmin):
    list_display = ('camera', 'client_ip', 'viewed_at', 'duration_seconds')
    list_filter = ('camera', 'viewed_at')

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('worker_id', 'worker_name', 'worker_role', 'trade_category', 'shift_status', 'shift_duration_hours', 'labor_cost', 'status', 'project')
    search_fields = ('worker_id', 'worker_name', 'worker_role')
    list_filter = ('shift_status', 'status', 'project')

@admin.register(BoMComponent)
class BoMComponentAdmin(admin.ModelAdmin):
    list_display = ('part_number', 'component_name', 'workstation', 'target_line_rate_units_hr', 'actual_line_rate_units_hr', 'status', 'project')
    search_fields = ('part_number', 'component_name', 'workstation')
    list_filter = ('status', 'project')

@admin.register(DrydockBerth)
class DrydockBerthAdmin(admin.ModelAdmin):
    list_display = ('berth_code', 'vessel_name', 'hull_section', 'docking_status', 'completion_percentage', 'project')
    search_fields = ('berth_code', 'vessel_name', 'hull_section')
    list_filter = ('docking_status', 'project')

@admin.register(ITARVendorAudit)
class ITARVendorAuditAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'itar_registration_number', 'clearance_level', 'audit_status', 'compliance_score', 'project')
    search_fields = ('itar_registration_number', 'supplier__name')
    list_filter = ('clearance_level', 'audit_status', 'project')

@admin.register(TurnaroundShutdown)
class TurnaroundShutdownAdmin(admin.ModelAdmin):
    list_display = ('unit_name', 'shutdown_phase', 'hot_work_permits_count', 'flare_stack_status', 'hazard_level', 'completion_percentage', 'project')
    search_fields = ('unit_name', 'shutdown_phase')
    list_filter = ('shutdown_phase', 'hazard_level', 'project')



