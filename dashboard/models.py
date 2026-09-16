from django.conf import settings
from django.db import models

from organizations.managers import TenantManager


class SystemSetting(models.Model):
    """Per-organization library settings (replaces global settings)."""

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="library_settings",
    )
    library_name = models.CharField(max_length=255, default="SmartLibrary")
    library_email = models.EmailField(default="admin@smartlibrary.com")
    library_phone = models.CharField(max_length=20, default="+1234567890")
    library_address = models.TextField(default="123 Library Street")

    max_books_per_member = models.PositiveIntegerField(default=3)
    default_borrow_days = models.PositiveIntegerField(default=14)
    renewal_limit = models.PositiveIntegerField(default=2)
    fine_per_day = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    allow_self_renewal = models.BooleanField(default=True)
    enable_late_fines = models.BooleanField(default=True)

    email_notifications = models.BooleanField(default=True)
    overdue_notifications = models.BooleanField(default=True)
    reservation_notifications = models.BooleanField(default=True)

    password_min_length = models.PositiveIntegerField(default=8)
    session_timeout_minutes = models.PositiveIntegerField(default=60)
    require_2fa = models.BooleanField(default=False)

    library_logo = models.ImageField(upload_to="settings/logo/", null=True, blank=True)
    primary_color = models.CharField(max_length=7, default="#111111")
    secondary_color = models.CharField(max_length=7, default="#10B981")

    objects = TenantManager()

    def __str__(self):
        if self.organization_id:
            return f"Settings — {self.organization.name}"
        return "Library System Settings"


class ActivityLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=255)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"
