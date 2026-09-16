from django.db.models import Q

from organizations.models import Organization


class TenantContextMiddleware:
    """
    Attach request.organization from the authenticated user.

    Organization IDs in query strings or form bodies are never trusted.
    Super admins may switch tenant context via session, which is always
    surfaced in the UI.
    """

    SESSION_ORG_KEY = "active_organization_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.tenant_branch = None
        request.impersonating_organization = False
        request.host_organization = self._organization_from_host(request)

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if user.is_superadmin():
                switched_id = request.session.get(self.SESSION_ORG_KEY)
                if switched_id:
                    organization = Organization.objects.filter(pk=switched_id, is_active=True).first()
                    if organization:
                        request.organization = organization
                        request.impersonating_organization = True
                    else:
                        request.session.pop(self.SESSION_ORG_KEY, None)
            else:
                request.organization = getattr(user, "organization", None)
                request.tenant_branch = getattr(user, "branch", None)

        return self.get_response(request)

    def _organization_from_host(self, request):
        host = request.get_host().split(":")[0].lower()
        if not host or host in {"localhost", "127.0.0.1", "testserver"}:
            return None
        slug_host = host.split(".")[0]
        return (
            Organization.objects.filter(is_active=True)
            .filter(Q(domain__iexact=host) | Q(slug__iexact=slug_host))
            .first()
        )
