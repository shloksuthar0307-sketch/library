from django.contrib import admin
from .models import MemberProfile

@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'member_id', 'status', 'membership_date')
    list_filter = ('status',)
