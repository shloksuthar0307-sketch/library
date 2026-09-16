from django.contrib import admin

from .models import Branch, Organization


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization_type", "subscription_status", "is_active", "created_at")
    search_fields = ("name", "email", "slug")
    list_filter = ("organization_type", "is_active", "subscription_status")
    inlines = [BranchInline]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "is_main", "is_active")
    list_filter = ("is_active", "is_main")
    search_fields = ("name", "code")
