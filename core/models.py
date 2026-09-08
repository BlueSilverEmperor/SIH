import json
import datetime
from django.db import models
from django.utils import timezone

class Project(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    total_budget = models.FloatField(default=0.0)
    start_date = models.DateField(blank=True, null=True)
    target_end_date = models.DateField(blank=True, null=True)
    baseline_duration_days = models.IntegerField(default=180)
    forecasted_end_date = models.DateField(blank=True, null=True)
    schedule_variance_days = models.IntegerField(default=0)
    field_velocity_rate = models.FloatField(default=0.0)
    supplier_risk_buffer_days = models.IntegerField(default=0)
    predictive_status = models.CharField(max_length=50, default='on_track')
    geofence_latitude = models.FloatField(default=37.7749)
    geofence_longitude = models.FloatField(default=-122.4194)
    geofence_radius_meters = models.FloatField(default=200.0)
    industry_sector = models.CharField(max_length=50, default='constructflow')
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'total_budget': self.total_budget,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'target_end_date': self.target_end_date.isoformat() if self.target_end_date else None,
            'baseline_duration_days': self.baseline_duration_days,
            'forecasted_end_date': self.forecasted_end_date.isoformat() if self.forecasted_end_date else None,
            'schedule_variance_days': self.schedule_variance_days,
            'field_velocity_rate': round(self.field_velocity_rate, 2) if self.field_velocity_rate else 0.0,
            'supplier_risk_buffer_days': self.supplier_risk_buffer_days,
            'predictive_status': self.predictive_status,
            'geofence_latitude': self.geofence_latitude,
            'geofence_longitude': self.geofence_longitude,
            'geofence_radius_meters': self.geofence_radius_meters,
            'industry_sector': self.industry_sector,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }



class Supplier(models.Model):
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, default='General')
    contact_email = models.EmailField(max_length=120, blank=True, null=True)
    tco_score = models.FloatField(default=80.0)
    delivery_score = models.FloatField(default=80.0)
    quality_score = models.FloatField(default=80.0)
    stability_score = models.FloatField(default=80.0)
    esg_score = models.FloatField(default=80.0)
    weighted_score = models.FloatField(default=0.0)
    softmax_probability = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def calculate_weighted_score(self):
        self.weighted_score = round(
            (0.30 * self.tco_score) +
            (0.25 * self.delivery_score) +
            (0.20 * self.quality_score) +
            (0.15 * self.stability_score) +
            (0.10 * self.esg_score),
            2
        )
        return self.weighted_score

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'contact_email': self.contact_email,
            'tco_score': self.tco_score,
            'delivery_score': self.delivery_score,
            'quality_score': self.quality_score,
            'stability_score': self.stability_score,
            'esg_score': self.esg_score,
            'weighted_score': self.weighted_score,
            'softmax_probability': round(self.softmax_probability, 4),
            'softmax_percentage': round(self.softmax_probability * 100.0, 2),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WBSTask(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    wbs_code = models.CharField(max_length=50)
    task_name = models.CharField(max_length=200)
    planned_quantity = models.FloatField(default=0.0)
    actual_quantity = models.FloatField(default=0.0)
    unit = models.CharField(max_length=50, default='units')
    unit_cost = models.FloatField(default=0.0)
    actual_cost = models.FloatField(default=0.0)
    planned_value = models.FloatField(default=0.0)
    earned_value = models.FloatField(default=0.0)
    completion_percentage = models.FloatField(default=0.0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    planned_start_date = models.DateField(blank=True, null=True)
    planned_end_date = models.DateField(blank=True, null=True)
    actual_start_date = models.DateField(blank=True, null=True)
    actual_end_date = models.DateField(blank=True, null=True)
    is_critical_path = models.BooleanField(default=False)
    milestone_name = models.CharField(max_length=100, blank=True, null=True)
    assigned_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_tasks')
    status = models.CharField(max_length=50, default='not_started')

    def __str__(self):
        return f"{self.wbs_code} - {self.task_name}"

    @property
    def schedule_variance(self):
        return self.earned_value - self.planned_value

    def calculate_evm(self):
        self.planned_value = float(self.planned_quantity) * float(self.unit_cost)
        self.earned_value = float(self.actual_quantity) * float(self.unit_cost)
        if self.planned_quantity > 0:
            self.completion_percentage = min(100.0, round((self.actual_quantity / self.planned_quantity) * 100.0, 2))
        else:
            self.completion_percentage = 0.0

        if self.completion_percentage >= 100.0:
            self.status = 'completed'
        elif self.completion_percentage > 0.0:
            self.status = 'in_progress'
        else:
            self.status = 'not_started'

    def to_dict(self):
        self.calculate_evm()
        return {
            'id': self.id,
            'project_id': self.project_id,
            'wbs_code': self.wbs_code,
            'task_name': self.task_name,
            'planned_quantity': self.planned_quantity,
            'actual_quantity': self.actual_quantity,
            'unit': self.unit,
            'unit_cost': self.unit_cost,
            'actual_cost': self.actual_cost,
            'planned_value': self.planned_value,
            'earned_value': self.earned_value,
            'completion_percentage': self.completion_percentage,
            'planned_start_date': self.planned_start_date.isoformat() if self.planned_start_date else None,
            'planned_end_date': self.planned_end_date.isoformat() if self.planned_end_date else None,
            'is_critical_path': self.is_critical_path,
            'milestone_name': self.milestone_name,
            'assigned_supplier_id': self.assigned_supplier_id,
            'assigned_supplier_name': self.assigned_supplier.name if self.assigned_supplier else None,
            'status': self.status
        }


class FieldInput(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='inputs')
    input_type = models.CharField(max_length=50)
    file_path = models.CharField(max_length=300)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    source_author = models.CharField(max_length=100, default='Site Inspector')
    status = models.CharField(max_length=50, default='pending_review')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.input_type} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'input_type': self.input_type,
            'file_path': self.file_path,
            'original_filename': self.original_filename,
            'notes': self.notes,
            'source_author': self.source_author,
            'status': self.status,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'extractions': [e.to_dict() for e in self.extractions.all()]
        }


class ExtractedMetric(models.Model):
    field_input = models.ForeignKey(FieldInput, on_delete=models.CASCADE, related_name='extractions')
    wbs_task = models.ForeignKey(WBSTask, on_delete=models.SET_NULL, blank=True, null=True, related_name='extractions')
    extracted_quantity = models.FloatField(default=0.0)
    unit = models.CharField(max_length=50, default='units', blank=True, null=True)
    detected_material = models.CharField(max_length=150, blank=True, null=True)
    labor_count = models.IntegerField(default=0)
    incurred_cost = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0)
    ai_reasoning = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extraction #{self.id} ({self.detected_material or 'Metric'})"

    def to_dict(self):
        return {
            'id': self.id,
            'field_input_id': self.field_input_id,
            'wbs_task_id': self.wbs_task_id,
            'extracted_quantity': self.extracted_quantity,
            'unit': self.unit,
            'detected_material': self.detected_material,
            'labor_count': self.labor_count,
            'incurred_cost': self.incurred_cost,
            'confidence_score': self.confidence_score,
            'ai_reasoning': self.ai_reasoning,
            'status': self.status,
            'wbs_task_name': self.wbs_task.task_name if self.wbs_task else 'Unmapped',
            'wbs_code': self.wbs_task.wbs_code if self.wbs_task else 'N/A'
        }


class AnalyticsLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='analytics_logs')
    snapshot_date = models.DateTimeField(auto_now_add=True)
    total_pv = models.FloatField(default=0.0)
    total_ev = models.FloatField(default=0.0)
    total_ac = models.FloatField(default=0.0)
    schedule_variance = models.FloatField(default=0.0)
    cost_variance = models.FloatField(default=0.0)
    spi = models.FloatField(default=1.0)
    cpi = models.FloatField(default=1.0)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"AnalyticsLog #{self.id} - {self.snapshot_date.strftime('%Y-%m-%d')}"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'total_pv': round(self.total_pv, 2),
            'total_ev': round(self.total_ev, 2),
            'total_ac': round(self.total_ac, 2),
            'schedule_variance': round(self.schedule_variance, 2),
            'cost_variance': round(self.cost_variance, 2),
            'spi': round(self.spi, 2),
            'cpi': round(self.cpi, 2),
            'notes': self.notes
        }


class Blueprint3D(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='blueprints_3d')
    name = models.CharField(max_length=150)
    source_filename = models.CharField(max_length=255, blank=True, null=True)
    wall_count = models.IntegerField(default=12)
    column_count = models.IntegerField(default=16)
    slab_area_sqm = models.FloatField(default=450.0)
    model_file_path = models.CharField(max_length=300)
    format = models.CharField(max_length=20, default='obj')
    status = models.CharField(max_length=50, default='generated')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.format})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'source_filename': self.source_filename,
            'wall_count': self.wall_count,
            'column_count': self.column_count,
            'slab_area_sqm': self.slab_area_sqm,
            'model_file_path': self.model_file_path,
            'format': self.format,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ProjectAddOn(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='add_ons')
    addon_key = models.CharField(max_length=50)
    is_enabled = models.BooleanField(default=True)
    settings_json = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'addon_key')

    def __str__(self):
        return f"{self.project.code} - {self.addon_key} ({'Enabled' if self.is_enabled else 'Disabled'})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'addon_key': self.addon_key,
            'is_enabled': self.is_enabled,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DailyProgressAudit(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='daily_audits')
    audit_date = models.DateField(default=timezone.now)
    planned_velocity = models.FloatField(default=0.0)
    actual_velocity = models.FloatField(default=0.0)
    variance = models.FloatField(default=0.0)
    audit_status = models.CharField(max_length=50, default='on_track')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audit {self.audit_date} ({self.audit_status})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'audit_date': self.audit_date.isoformat() if self.audit_date else None,
            'planned_velocity': round(self.planned_velocity, 2),
            'actual_velocity': round(self.actual_velocity, 2),
            'variance': round(self.variance, 2),
            'audit_status': self.audit_status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FailSafeReorgLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='failsafe_reorgs')
    trigger_date = models.DateTimeField(auto_now_add=True)
    target_end_date = models.DateField()
    enforced_deadline = models.DateField()
    days_saved = models.IntegerField(default=0)
    crashed_tasks_count = models.IntegerField(default=0)
    details_json = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"FailSafeReorg {self.trigger_date.strftime('%Y-%m-%d')} (-{self.days_saved} days)"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'trigger_date': self.trigger_date.isoformat() if self.trigger_date else None,
            'target_end_date': self.target_end_date.isoformat() if self.target_end_date else None,
            'enforced_deadline': self.enforced_deadline.isoformat() if self.enforced_deadline else None,
            'days_saved': self.days_saved,
            'crashed_tasks_count': self.crashed_tasks_count,
            'details': json.loads(self.details_json) if self.details_json else []
        }


class AttendanceRecord(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attendance_records')
    worker_id = models.CharField(max_length=50, default='WRK-1001')
    worker_name = models.CharField(max_length=150)
    worker_role = models.CharField(max_length=100, default='Field Engineer')
    trade_category = models.CharField(max_length=100, default='General Labor')
    hourly_rate = models.FloatField(default=35.0)

    shift_type = models.CharField(max_length=50, default='morning_checkin') # 'morning_checkin' or 'evening_checkout'
    timestamp = models.DateTimeField(auto_now_add=True)
    checkin_time = models.DateTimeField(default=timezone.now)
    checkout_time = models.DateTimeField(blank=True, null=True)
    shift_duration_hours = models.FloatField(default=0.0)
    labor_cost = models.FloatField(default=0.0)

    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    distance_from_center_m = models.FloatField(default=0.0)

    checkin_lat = models.FloatField(default=0.0)
    checkin_lng = models.FloatField(default=0.0)
    checkin_distance_m = models.FloatField(default=0.0)

    checkout_lat = models.FloatField(default=0.0)
    checkout_lng = models.FloatField(default=0.0)
    checkout_distance_m = models.FloatField(default=0.0)

    is_geofence_valid = models.BooleanField(default=True)
    token_hash = models.CharField(max_length=128, blank=True, null=True)
    status = models.CharField(max_length=50, default='verified') # 'verified', 'out_of_bounds', 'flagged'
    shift_status = models.CharField(max_length=50, default='ACTIVE_ON_SITE') # 'ACTIVE_ON_SITE', 'COMPLETED', 'OUT_OF_BOUNDS', 'FLAGGED'
    associated_wbs_task = models.ForeignKey(WBSTask, on_delete=models.SET_NULL, blank=True, null=True, related_name='attendance_records')

    def __str__(self):
        return f"{self.worker_name} ({self.worker_id}) - {self.shift_status} ({self.status})"

    def calculate_shift_totals(self):
        if self.checkin_time and self.checkout_time:
            delta = self.checkout_time - self.checkin_time
            self.shift_duration_hours = round(max(0.1, delta.total_seconds() / 3600.0), 2)
            self.labor_cost = round(self.shift_duration_hours * self.hourly_rate, 2)
        return self.shift_duration_hours, self.labor_cost

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'worker_id': self.worker_id,
            'worker_name': self.worker_name,
            'worker_role': self.worker_role,
            'trade_category': self.trade_category,
            'hourly_rate': self.hourly_rate,
            'shift_type': self.shift_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'checkin_time': self.checkin_time.isoformat() if self.checkin_time else (self.timestamp.isoformat() if self.timestamp else None),
            'checkout_time': self.checkout_time.isoformat() if self.checkout_time else None,
            'shift_duration_hours': self.shift_duration_hours,
            'labor_cost': self.labor_cost,
            'latitude': self.latitude if self.latitude else self.checkin_lat,
            'longitude': self.longitude if self.longitude else self.checkin_lng,
            'distance_from_center_m': round(self.distance_from_center_m if self.distance_from_center_m else self.checkin_distance_m, 1),
            'checkin_lat': self.checkin_lat,
            'checkin_lng': self.checkin_lng,
            'checkin_distance_m': round(self.checkin_distance_m, 1),
            'checkout_lat': self.checkout_lat,
            'checkout_lng': self.checkout_lng,
            'checkout_distance_m': round(self.checkout_distance_m, 1),
            'is_geofence_valid': self.is_geofence_valid,
            'token_hash': self.token_hash,
            'status': self.status,
            'shift_status': self.shift_status,
            'associated_wbs_task_id': self.associated_wbs_task_id,
            'associated_wbs_task_name': self.associated_wbs_task.task_name if self.associated_wbs_task else None
        }



class WeatherRiskLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='weather_logs')
    log_date = models.DateField(default=timezone.now)
    forecast_condition = models.CharField(max_length=100, default='Clear')
    precipitation_chance_pct = models.FloatField(default=0.0)
    wind_speed_kmh = models.FloatField(default=0.0)
    temperature_c = models.FloatField(default=25.0)
    impacted_tasks_count = models.IntegerField(default=0)
    risk_severity = models.CharField(max_length=50, default='low')
    buffer_days_added = models.IntegerField(default=0)
    details_json = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WeatherRisk {self.log_date} ({self.risk_severity})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'log_date': self.log_date.isoformat() if self.log_date else None,
            'forecast_condition': self.forecast_condition,
            'precipitation_chance_pct': self.precipitation_chance_pct,
            'wind_speed_kmh': self.wind_speed_kmh,
            'temperature_c': self.temperature_c,
            'impacted_tasks_count': self.impacted_tasks_count,
            'risk_severity': self.risk_severity,
            'buffer_days_added': self.buffer_days_added,
            'details': json.loads(self.details_json) if self.details_json else []
        }


class ProcurementReviewItem(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='procurement_reviews')
    material_name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, default='General')
    quantity = models.FloatField(default=0.0)
    unit = models.CharField(max_length=50, default='units')
    estimated_unit_cost = models.FloatField(default=0.0)
    total_estimated_cost = models.FloatField(default=0.0)
    recommended_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, blank=True, null=True)
    softmax_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, default='pending_approval') # pending_approval, approved, rejected
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Procurement {self.material_name} ({self.status})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'material_name': self.material_name,
            'category': self.category,
            'quantity': self.quantity,
            'unit': self.unit,
            'estimated_unit_cost': self.estimated_unit_cost,
            'total_estimated_cost': self.total_estimated_cost,
            'recommended_supplier_id': self.recommended_supplier_id,
            'recommended_supplier_name': self.recommended_supplier.name if self.recommended_supplier else 'Unassigned',
            'softmax_score': round(self.softmax_score, 4),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CCTVCamera(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='cctv_cameras')
    name = models.CharField(max_length=150)
    camera_code = models.CharField(max_length=50, unique=True)
    location_tag = models.CharField(max_length=100, default='Zone A')
    rtsp_url = models.CharField(max_length=255, default='rtsp://admin:pass@192.168.1.100:554/stream1')
    stream_type = models.CharField(max_length=50, default='mjpg') # mjpg, hls, webrtc, simulated
    status = models.CharField(max_length=50, default='online') # online, offline, maintenance
    resolution = models.CharField(max_length=50, default='1080p')
    fps = models.IntegerField(default=30)
    associated_wbs_task = models.ForeignKey(WBSTask, on_delete=models.SET_NULL, blank=True, null=True, related_name='cctv_cameras')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.camera_code}) - {self.location_tag}"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'camera_code': self.camera_code,
            'location_tag': self.location_tag,
            'rtsp_url': self.rtsp_url,
            'stream_type': self.stream_type,
            'status': self.status,
            'resolution': self.resolution,
            'fps': self.fps,
            'associated_wbs_task_id': self.associated_wbs_task_id,
            'associated_wbs_task_name': self.associated_wbs_task.task_name if self.associated_wbs_task else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CCTVStreamLog(models.Model):
    camera = models.ForeignKey(CCTVCamera, on_delete=models.CASCADE, related_name='stream_logs')
    token_hash = models.CharField(max_length=128)
    client_ip = models.CharField(max_length=45, default='127.0.0.1')
    viewed_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.IntegerField(default=0)

    def __str__(self):
        return f"StreamLog {self.camera.camera_code} at {self.viewed_at}"

    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'token_hash': self.token_hash,
            'client_ip': self.client_ip,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'duration_seconds': self.duration_seconds
        }


# ==================== MULTI-INDUSTRY SUB-APPLICATION DOMAIN MODELS ====================

class BoMComponent(models.Model):
    """
    PlantFlow (Heavy Manufacturing): Bill of Materials & Line-Rate Routing Component.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bom_components')
    part_number = models.CharField(max_length=50)
    component_name = models.CharField(max_length=150)
    workstation = models.CharField(max_length=100, default='Assembly Line A')
    active_phase = models.CharField(max_length=100, default='Stator Winding Active')
    daily_target_units = models.FloatField(default=500.0)
    daily_actual_units = models.FloatField(default=485.0)
    bom_quantity = models.FloatField(default=100.0)
    target_line_rate_units_hr = models.FloatField(default=50.0)
    actual_line_rate_units_hr = models.FloatField(default=48.5)
    status = models.CharField(max_length=50, default='optimal') # optimal, bottleneck, delayed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.part_number} - {self.component_name} ({self.workstation})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'part_number': self.part_number,
            'component_name': self.component_name,
            'workstation': self.workstation,
            'active_phase': self.active_phase,
            'daily_target_units': self.daily_target_units,
            'daily_actual_units': self.daily_actual_units,
            'bom_quantity': self.bom_quantity,
            'target_line_rate_units_hr': self.target_line_rate_units_hr,
            'actual_line_rate_units_hr': self.actual_line_rate_units_hr,
            'efficiency_pct': round((self.actual_line_rate_units_hr / max(1.0, self.target_line_rate_units_hr)) * 100.0, 1),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DrydockBerth(models.Model):
    """
    DockFlow (Shipbuilding & Maritime Logistics): Drydock Berth & Hull Section Telemetry.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='drydock_berths')
    berth_code = models.CharField(max_length=50)
    vessel_name = models.CharField(max_length=150)
    hull_number = models.CharField(max_length=50, default='Hull #409')
    hull_section = models.CharField(max_length=100, default='Section H-04 Bow')
    steel_tonnage = models.FloatField(default=800.0)
    steel_grade = models.CharField(max_length=50, default='DH36 Structural Steel')
    main_deck_welding_pct = models.FloatField(default=74.0)
    docking_status = models.CharField(max_length=50, default='docked') # docked, outfitting, launched
    completion_percentage = models.FloatField(default=74.0)
    telemetry_camera = models.ForeignKey(CCTVCamera, on_delete=models.SET_NULL, blank=True, null=True, related_name='drydock_berths')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.berth_code} - {self.vessel_name} ({self.hull_number})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'berth_code': self.berth_code,
            'vessel_name': self.vessel_name,
            'hull_number': self.hull_number,
            'hull_section': self.hull_section,
            'steel_tonnage': self.steel_tonnage,
            'steel_grade': self.steel_grade,
            'main_deck_welding_pct': self.main_deck_welding_pct,
            'docking_status': self.docking_status,
            'completion_percentage': self.completion_percentage,
            'telemetry_camera_id': self.telemetry_camera_id,
            'telemetry_camera_name': self.telemetry_camera.name if self.telemetry_camera else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ITARVendorAudit(models.Model):
    """
    AeroGuard (Defense & Aerospace): ITAR Compliance & Security Clearance Audit.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='itar_audits')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='itar_audits')
    batch_code = models.CharField(max_length=50, default='Batch VII')
    component_housing = models.CharField(max_length=150, default='Avionic Telemetry Housing')
    itar_registration_number = models.CharField(max_length=100)
    itar_level = models.CharField(max_length=50, default='ITAR Level 3')
    material_billet_type = models.CharField(max_length=100, default='Titanium Ti-6Al-4V Billets')
    clearance_level = models.CharField(max_length=50, default='Top Secret (TS/SCI)') # Top Secret, Secret, Confidential
    metallurgical_audit_status = models.CharField(max_length=50, default='Passed')
    audit_status = models.CharField(max_length=50, default='compliant') # compliant, under_review, non_compliant
    compliance_score = models.FloatField(default=99.8)
    last_audit_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"ITAR {self.supplier.name} - {self.batch_code} ({self.audit_status})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else 'Unknown',
            'batch_code': self.batch_code,
            'component_housing': self.component_housing,
            'itar_registration_number': self.itar_registration_number,
            'itar_level': self.itar_level,
            'material_billet_type': self.material_billet_type,
            'clearance_level': self.clearance_level,
            'metallurgical_audit_status': self.metallurgical_audit_status,
            'audit_status': self.audit_status,
            'compliance_score': self.compliance_score,
            'last_audit_date': self.last_audit_date.isoformat() if self.last_audit_date else None
        }


class TurnaroundShutdown(models.Model):
    """
    TurnaroundOS (Energy & Refineries): Plant Shutdown Critical-Path Management.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='turnarounds')
    unit_name = models.CharField(max_length=150) # Crude Distillation Unit (CDU) Catalyst Regeneration
    catalyst_regeneration_task = models.CharField(max_length=150, default='CDU Catalyst Regeneration')
    turnaround_window_hours = models.IntegerField(default=96)
    catalyst_pellet_type = models.CharField(max_length=100, default='Type-V Catalyst Pellets')
    purge_status = models.CharField(max_length=50, default='Reactor Purge Complete')
    shutdown_phase = models.CharField(max_length=50, default='overhaul') # decontamination, overhaul, testing, restart
    hot_work_permits_count = models.IntegerField(default=8)
    flare_stack_status = models.CharField(max_length=50, default='normal') # normal, flaring, shutdown
    hazard_level = models.CharField(max_length=50, default='low') # low, medium, critical
    completion_percentage = models.FloatField(default=58.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.unit_name} - {self.shutdown_phase} ({self.hazard_level})"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'unit_name': self.unit_name,
            'catalyst_regeneration_task': self.catalyst_regeneration_task,
            'turnaround_window_hours': self.turnaround_window_hours,
            'catalyst_pellet_type': self.catalyst_pellet_type,
            'purge_status': self.purge_status,
            'shutdown_phase': self.shutdown_phase,
            'hot_work_permits_count': self.hot_work_permits_count,
            'flare_stack_status': self.flare_stack_status,
            'hazard_level': self.hazard_level,
            'completion_percentage': self.completion_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }





