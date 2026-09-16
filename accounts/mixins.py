from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(AccessMixin):
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles and not request.user.is_superadmin():
            raise PermissionDenied("You do not have permission to access this resource.")
        return super().dispatch(request, *args, **kwargs)


class OrganizationQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(qs, "for_request"):
            return qs.for_request(self.request)
        organization = getattr(self.request, "organization", None)
        if organization:
            return qs.filter(organization=organization)
        if self.request.user.is_authenticated and self.request.user.is_superadmin():
            return qs
        return qs.none()
