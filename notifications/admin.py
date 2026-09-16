from django.contrib import admin
from .models import Notification, EmailTemplate, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_date', 'organization')
    list_filter = ('notification_type', 'is_read', 'organization')
    search_fields = ('user__username', 'title', 'message')

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'subject', 'is_active', 'organization')
    list_filter = ('event_type', 'is_active', 'organization')
    search_fields = ('subject', 'body_text')

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_due_soon', 'email_overdue', 'email_reservation_ready')
    search_fields = ('user__username', 'user__email')
