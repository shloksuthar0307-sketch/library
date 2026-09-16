from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404


class OrganizationScopedMixin:
    """CBV mixin that forces querysets through tenant-aware managers."""

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs, "for_request"):
            qs = qs.for_request(self.request)
        elif getattr(self.request, "organization", None):
            qs = qs.filter(organization=self.request.organization)
        elif not (self.request.user.is_authenticated and self.request.user.is_superadmin()):
            qs = qs.none()
        return self.apply_branch_scope(qs)

    def apply_branch_scope(self, qs):
        from organizations.services import apply_branch_scope

        return apply_branch_scope(qs, self.request)

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return super().get_object(queryset=queryset)


class TenantRequiredMixin(AccessMixin):
    """Require an authenticated user with an organization context (except super admins)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superadmin() and not getattr(request, "organization", None):
            raise PermissionDenied("No organization is associated with this account.")
        return super().dispatch(request, *args, **kwargs)


class SuperAdminRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superadmin():
            raise PermissionDenied("Super Admin access required.")
        return super().dispatch(request, *args, **kwargs)


def get_tenant_object_or_404(model, request, **kwargs):
    qs = model.objects.all()
    if hasattr(qs, "for_request"):
        qs = qs.for_request(request)
    from organizations.services import apply_branch_scope

    qs = apply_branch_scope(qs, request)
    return get_object_or_404(qs, **kwargs)
