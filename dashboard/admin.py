from django.contrib import admin
from .models import SystemSetting, ActivityLog

admin.site.register(SystemSetting)
admin.site.register(ActivityLog)
