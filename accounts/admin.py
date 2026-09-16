from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'organization', 'branch', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'organization')
    fieldsets = UserAdmin.fieldsets + (
        ('Tenant & Role', {'fields': ('role', 'organization', 'branch', 'phone_number', 'profile_image', 'is_verified', 'can_access_all_branches')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Tenant & Role', {'fields': ('role', 'organization', 'branch')}),
    )

admin.site.register(User, CustomUserAdmin)
