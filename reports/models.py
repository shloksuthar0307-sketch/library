from django.db import models
from django.utils import timezone
from accounts.models import User

class ScheduledReport(models.Model):
    # Defining choices here for encapsulation
    class ReportType(models.TextChoices):
        DAILY_CIRCULATION = 'DAILY_CIRCULATION', 'Daily Circulation'
        WEEKLY_SUMMARY = 'WEEKLY_SUMMARY', 'Weekly Library Summary'
        MONTHLY_SUMMARY = 'MONTHLY_SUMMARY', 'Monthly Library Summary'
        OVERDUE_BOOKS = 'OVERDUE_BOOKS', 'Overdue Books'
        OUTSTANDING_FINES = 'OUTSTANDING_FINES', 'Outstanding Fines'
        NEW_MEMBERS = 'NEW_MEMBERS', 'New Members'
        POPULAR_BOOKS = 'POPULAR_BOOKS', 'Popular Books'
        INVENTORY_STATUS = 'INVENTORY_STATUS', 'Inventory Status'
        CUSTOM = 'CUSTOM', 'Custom Report'

    class Frequency(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'

    class Format(models.TextChoices):
        CSV = 'CSV', 'CSV'
        PDF = 'PDF', 'PDF'
        BOTH = 'BOTH', 'CSV + PDF'

    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50, choices=ReportType.choices, default=ReportType.CUSTOM)
    recipients = models.TextField(help_text="Comma separated email addresses")
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    format = models.CharField(max_length=10, choices=Format.choices, default=Format.CSV)
    
    # Store JSON representation of filters for custom reports
    filters = models.JSONField(default=dict, blank=True)
    
    start_date = models.DateField(default=timezone.now)
    scheduled_time = models.TimeField(default=timezone.now)
    
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class ReportLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        EMAIL_FAILED = 'EMAIL_FAILED', 'Email Failed'
        GENERATING = 'GENERATING', 'Generating'

    report = models.ForeignKey(ScheduledReport, on_delete=models.SET_NULL, null=True, blank=True)
    report_name = models.CharField(max_length=255)
    generated_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATING)
    error_message = models.TextField(blank=True, null=True)
    format_generated = models.CharField(max_length=10)
    record_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.report_name} - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"
