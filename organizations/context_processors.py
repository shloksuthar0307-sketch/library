def tenant_branding(request):
    organization = getattr(request, "organization", None)
    host_organization = getattr(request, "host_organization", None)
    branding_org = organization or host_organization
    settings_obj = None
    if branding_org is not None:
        settings_obj = getattr(branding_org, "library_settings", None)
        if settings_obj is None:
            from dashboard.models import SystemSetting

            settings_obj = SystemSetting.objects.filter(organization=branding_org).first()

    primary = "#111111"
    accent = "#10B981"
    if settings_obj:
        primary = settings_obj.primary_color or primary
        accent = settings_obj.secondary_color or accent

    return {
        "current_organization": organization,
        "host_organization": host_organization,
        "branding_organization": branding_org,
        "organization_settings": settings_obj,
        "impersonating_organization": getattr(request, "impersonating_organization", False),
        "brand_primary": primary,
        "brand_accent": accent,
        "brand_logo": getattr(settings_obj, "library_logo", None) or getattr(branding_org, "logo", None),
    }
