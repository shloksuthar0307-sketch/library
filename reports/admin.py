from django.contrib import admin
from .models import ScheduledReport, ReportLog

@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'frequency', 'format', 'next_run_at', 'is_active')
    list_filter = ('is_active', 'frequency', 'report_type', 'format')
    search_fields = ('name', 'recipients')
    
@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'status', 'generated_at', 'format_generated', 'record_count')
    list_filter = ('status', 'format_generated', 'generated_at')
    search_fields = ('report_name', 'error_message')
