from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import User
from .models import Notification

@login_required
def list_view(request):
    org = getattr(request, 'organization', None)

    if request.method == "POST" and request.user.is_staff_member():
        member_id = request.POST.get("member_id")
        title = request.POST.get("title", "").strip()
        message = request.POST.get("message", "").strip()
        notification_type = request.POST.get("notification_type", "INFO")
        
        if title and message:
            if member_id == "ALL":
                # Send to all members in org
                members = User.objects.filter(role=User.Role.MEMBER)
                if org:
                    members = members.filter(organization=org)
                    
                notifications_to_create = [
                    Notification(
                        organization=org,
                        user=m,
                        title=title,
                        message=message,
                        notification_type=notification_type
                    ) for m in members
                ]
                Notification.objects.bulk_create(notifications_to_create)
                messages.success(request, f"Notification sent to {members.count()} members.")
            else:
                try:
                    member = User.objects.get(pk=member_id, role=User.Role.MEMBER)
                    if org and member.organization_id != org.id:
                        raise User.DoesNotExist
                        
                    Notification.objects.create(
                        organization=org,
                        user=member,
                        title=title,
                        message=message,
                        notification_type=notification_type
                    )
                    messages.success(request, f"Notification sent to {member.get_full_name() or member.username}.")
                except User.DoesNotExist:
                    messages.error(request, "Selected member not found.")
        else:
            messages.error(request, "Title and message are required.")
            
        return redirect("notifications:list")

    notifications = Notification.objects.for_request(request).filter(user=request.user)
    
    context = {"notifications": notifications}
    if request.user.is_staff_member():
        members_qs = User.objects.filter(role=User.Role.MEMBER)
        if org:
            members_qs = members_qs.filter(organization=org)
        context["members"] = members_qs.order_by("first_name", "username")
        
    return render(request, "notifications/index.html", context)

index_view = list_view
