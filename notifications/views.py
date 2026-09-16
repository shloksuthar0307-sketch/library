from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Notification


@login_required
def list_view(request):
    notifications = Notification.objects.for_request(request).filter(user=request.user)
    return render(request, "notifications/index.html", {"notifications": notifications})


index_view = list_view
