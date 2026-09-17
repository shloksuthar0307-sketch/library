import json
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django_ratelimit.decorators import ratelimit

from accounts.models import User
from accounts.permissions import deny_members
from books.models import Book, Category
from members.models import MemberProfile
from organizations.models import Branch
from reservations.models import Reservation
from transactions.models import Transaction
from .models import ScheduledReport, ReportLog
from .services import ReportGenerationService, ExportService
from .tasks import run_scheduled_report

@login_required
@deny_members
def index_view(request):
    books = Book.objects.for_request(request)
    members = MemberProfile.objects.for_request(request)
    transactions = Transaction.objects.for_request(request)
    if request.user.role == User.Role.STAFF and request.user.branch_id and not request.user.can_access_all_branches:
        transactions = transactions.filter(Q(branch=request.user.branch) | Q(branch__isnull=True))

    context = {
        "total_circulation": transactions.count(),
        "loans": transactions.filter(status="ISSUED").count(),
        "returns": transactions.filter(status__in=["RETURNED", "OVERDUE"]).count(),
        "total_books": books.count(),
        "active_members": members.filter(status="ACTIVE").count(),
        "total_members": members.count(),
        "pending_fines": transactions.filter(fine_amount__gt=0, fine_paid=False).aggregate(total=Sum("fine_amount"))["total"] or 0,
        "reservations": Reservation.objects.for_request(request).count(),
        "branches": Branch.objects.for_request(request) if hasattr(Branch.objects, "for_request") else Branch.objects.filter(organization=request.organization),
        "scheduled_reports": ScheduledReport.objects.all().order_by('-created_at'),
        "report_logs": ReportLog.objects.all().order_by('-generated_at')[:10],
    }
    return render(request, "reports/index.html", context)


@login_required
@deny_members
@ratelimit(key='user', rate='5/m', block=True)
def export_report_view(request):
    # Determine format and filters from GET params
    fmt = request.GET.get('format', 'CSV').upper()
    data_source = request.GET.get('source', 'transactions')
    
    # Extract arbitrary filters (e.g., date_range, status)
    filters = {k: v for k, v in request.GET.items() if k not in ['format', 'source']}
    
    qs = ReportGenerationService.get_queryset(data_source, filters, request_user=request.user)
    
    if fmt == 'PDF':
        pdf_content = ExportService.generate_pdf(qs, data_source)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="report.pdf"'
        return response
    else:
        csv_content = ExportService.generate_csv(qs, data_source)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="report.csv"'
        return response


@login_required
@deny_members
@require_POST
@ratelimit(key='user', rate='10/m', block=True)
def create_scheduled_report_view(request):
    try:
        data = json.loads(request.body)
        report = ScheduledReport.objects.create(
            name=data.get('name', 'Custom Scheduled Report'),
            report_type=data.get('report_type', 'CUSTOM'),
            recipients=data.get('recipients', request.user.email),
            frequency=data.get('frequency', 'WEEKLY'),
            format=data.get('format', 'CSV'),
            filters=data.get('filters', {}),
            created_by=request.user
        )
        return JsonResponse({"status": "success", "id": report.id, "message": "Schedule saved successfully."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
@deny_members
@require_POST
def toggle_scheduled_report_view(request, pk):
    report = get_object_or_404(ScheduledReport, pk=pk)
    report.is_active = not report.is_active
    report.save()
    status_text = "resumed" if report.is_active else "paused"
    return JsonResponse({"status": "success", "message": f"Report schedule {status_text}."})


@login_required
@deny_members
@require_POST
@ratelimit(key='user', rate='5/m', block=True)
def run_scheduled_report_view(request, pk):
    report = get_object_or_404(ScheduledReport, pk=pk)
    # Trigger celery task asynchronously
    run_scheduled_report.delay(report.id)
    return JsonResponse({"status": "success", "message": "Report generation started. You will receive an email shortly."})


@login_required
@deny_members
@require_http_methods(["DELETE"])
def delete_scheduled_report_view(request, pk):
    report = get_object_or_404(ScheduledReport, pk=pk)
    report.delete()
    return JsonResponse({"status": "success", "message": "Scheduled report deleted successfully."})

@login_required
@deny_members
@require_POST
@ratelimit(key='user', rate='20/m', block=True)
def custom_report_preview_view(request):
    try:
        data = json.loads(request.body)
        data_source = data.get('source', 'transactions')
        filters = data.get('filters', {})
        qs = ReportGenerationService.get_queryset(data_source, filters, request_user=request.user)
        # return basic counts/preview
        return JsonResponse({
            "status": "success",
            "total_records": qs.count() if qs else 0,
            "sample_data": "Preview data ready."
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)