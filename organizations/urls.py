from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("super-admin/", views.platform_dashboard, name="platform"),
    path("super-admin/organizations/", views.organization_list, name="list"),
    path("super-admin/organizations/onboard/", views.onboarding_wizard, name="onboard"),
    path("super-admin/organizations/<uuid:pk>/", views.organization_detail, name="detail"),
    path("super-admin/organizations/<uuid:pk>/edit/", views.organization_edit, name="edit"),
    path("super-admin/organizations/<uuid:pk>/toggle/", views.organization_toggle, name="toggle"),
    path("super-admin/switch/<uuid:pk>/", views.switch_organization, name="switch"),
    path("super-admin/switch/clear/", views.clear_organization_switch, name="switch_clear"),
    path("organization/profile/", views.organization_profile, name="profile"),
    path("organization/branches/", views.branch_list, name="branches"),
]
