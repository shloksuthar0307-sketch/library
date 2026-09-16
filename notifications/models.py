from django.conf import settings
from django.db import models
from django.utils import timezone

from organizations.managers import TenantManager

class Notification(models.Model):
    TYPE_CHOICES = (
        ("INFO", "Information"),
        ("WARNING", "Warning"),
        ("SUCCESS", "Success"),
        ("DANGER", "Danger"),
        ("EMAIL", "Email Sent"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="INFO")
    is_read = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return f"To {self.user.username}: {self.title}"


class EmailTemplate(models.Model):
    EVENT_CHOICES = (
        ("DUE_SOON", "Due Soon"),
        ("OVERDUE", "Overdue"),
        ("RESERVATION_READY", "Reservation Ready"),
        ("FINE_CREATED", "Fine Created"),
        ("PAYMENT_RECEIVED", "Payment Received"),
        ("WELCOME", "Welcome Email"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_templates",
    )
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    subject = models.CharField(max_length=255)
    body_html = models.TextField(help_text="Use {{ user.first_name }}, {{ book.title }}, etc. for variables.")
    body_text = models.TextField(help_text="Plain text fallback.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        unique_together = ('organization', 'event_type')

    def __str__(self):
        return f"{self.get_event_type_display()} Template for {self.organization.name if self.organization else 'Global'}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    email_due_soon = models.BooleanField(default=True)
    email_overdue = models.BooleanField(default=True)
    email_reservation_ready = models.BooleanField(default=True)
    email_fines = models.BooleanField(default=True)
    
    in_app_due_soon = models.BooleanField(default=True)
    in_app_overdue = models.BooleanField(default=True)
    in_app_reservation_ready = models.BooleanField(default=True)
    in_app_fines = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.user.username}"
