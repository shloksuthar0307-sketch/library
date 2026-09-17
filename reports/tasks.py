from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import ScheduledReport, ReportLog
from .services import ReportGenerationService, ExportService, EmailService

@shared_task
def dispatch_scheduled_reports():
    now = timezone.now()
    # Find active reports where next_run_at is due (or null for first run)
    due_reports = ScheduledReport.objects.filter(
        is_active=True,
        start_date__lte=now.date()
    ).exclude(next_run_at__gt=now)
    
    for report in due_reports:
        run_scheduled_report.delay(report.id)

@shared_task
def run_scheduled_report(report_id):
    try:
        report = ScheduledReport.objects.get(id=report_id)
    except ScheduledReport.DoesNotExist:
        return
        
    log = ReportLog.objects.create(
        report=report,
        report_name=report.name,
        format_generated=report.format,
        status=ReportLog.Status.GENERATING
    )
    
    try:
        # 1. Generate Data
        qs = ReportGenerationService.get_queryset('transactions', report.filters)
        log.record_count = qs.count() if qs else 0
        
        # 2. Export File
        if report.format == 'PDF':
            file_content = ExportService.generate_pdf(qs, 'transactions', title=report.name)
            file_name = f"{report.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
            mime = 'application/pdf'
        else:
            file_content = ExportService.generate_csv(qs, 'transactions')
            file_name = f"{report.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.csv"
            mime = 'text/csv'
            
        # 3. Email
        EmailService.send_report(report, file_content, file_name, mime)
        
        # 4. Update Status
        log.status = ReportLog.Status.SUCCESS
        log.save()
        
        # 5. Calculate next run
        report.last_sent_at = timezone.now()
        if report.frequency == 'DAILY':
            report.next_run_at = timezone.now() + timedelta(days=1)
        elif report.frequency == 'WEEKLY':
            report.next_run_at = timezone.now() + timedelta(weeks=1)
        elif report.frequency == 'MONTHLY':
            report.next_run_at = timezone.now() + timedelta(days=30)
        report.save()
        
    except Exception as e:
        log.status = ReportLog.Status.FAILED
        log.error_message = str(e)
        log.save()
