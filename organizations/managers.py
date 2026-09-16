from django.db import models


class TenantQuerySet(models.QuerySet):
    """Organization-scoped queryset helpers used by every tenant-aware model."""

    def for_organization(self, organization):
        if organization is None:
            return self.none()
        return self.filter(organization=organization)

    def for_request(self, request):
        """
        Scope to the active tenant context.

        Super admins see all rows unless they have explicitly switched into
        an organization (request.organization is then set by middleware).
        Everyone else is always limited to their own organization.
        """
        user = getattr(request, "user", None)
        organization = getattr(request, "organization", None)

        if user is not None and getattr(user, "is_authenticated", False) and user.is_superadmin():
            if organization is not None:
                return self.filter(organization=organization)
            return self

        if organization is None and user is not None:
            organization = getattr(user, "organization", None)

        return self.for_organization(organization)

    def for_branch(self, branch):
        if branch is None:
            return self
        field_names = {field.name for field in self.model._meta.fields}
        if "branch" not in field_names:
            return self
        return self.filter(branch=branch)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    pass
