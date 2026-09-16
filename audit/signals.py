from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import AuditLog

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        organization=user.organization if hasattr(user, 'organization') else None,
        action="Logged In",
        module="Authentication",
        description=f"User {user.username} successfully authenticated.",
        ip_address=request.META.get('REMOTE_ADDR')
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user:
        AuditLog.objects.create(
            user=user,
            organization=user.organization if hasattr(user, 'organization') else None,
            action="Logged Out",
            module="Authentication",
            description=f"User {user.username} logged out.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
