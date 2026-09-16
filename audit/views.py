from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.permissions import org_admin_required

from .models import AuditLog


@login_required
@org_admin_required
def log_list(request):
    logs = AuditLog.objects.for_request(request)
    return render(request, "audit/log_list.html", {"logs": logs[:200]})
