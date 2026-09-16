import logging

from django.core.exceptions import PermissionDenied, ValidationError

logger = logging.getLogger(__name__)


class SubscriptionLimitExceeded(ValidationError):
    pass


def apply_branch_scope(qs, request):
    """Staff users are limited to their assigned branch unless explicitly granted all branches."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return qs.none()

    if user.is_superadmin() or user.is_org_admin() or getattr(user, "can_access_all_branches", False):
        return qs

    field_names = {field.name for field in qs.model._meta.fields}
    if "branch" not in field_names:
        return qs

    if user.role == user.Role.STAFF and user.branch_id:
        return qs.filter(branch=user.branch)
    return qs


def assert_same_organization(*objects, organization=None):
    for obj in objects:
        if obj is None:
            continue
        obj_org_id = getattr(obj, "organization_id", None)
        if obj_org_id is None and hasattr(obj, "organization"):
            obj_org_id = getattr(getattr(obj, "organization", None), "pk", None)
        if organization is not None and obj_org_id and str(obj_org_id) != str(organization.pk):
            raise PermissionDenied("Cross-organization access is not allowed.")
        if organization is None:
            organization = getattr(obj, "organization", None)
    return organization


def get_or_create_settings(organization):
    from dashboard.models import SystemSetting

    if organization is None:
        return None
    setting, _ = SystemSetting.objects.get_or_create(
        organization=organization,
        defaults={
            "library_name": organization.name,
            "library_email": organization.email or "admin@smartlibrary.com",
            "library_phone": organization.phone or "",
            "library_address": organization.address or "",
            "fine_per_day": organization.default_fine_per_day,
        },
    )
    return setting


def get_usage_counts(organization):
    from accounts.models import User
    from books.models import Book
    from members.models import MemberProfile
    from organizations.models import Branch

    return {
        "members": MemberProfile.objects.filter(organization=organization).count(),
        "books": Book.objects.filter(organization=organization).count(),
        "staff": User.objects.filter(
            organization=organization,
            role__in=[User.Role.STAFF, User.Role.ORG_ADMIN],
        ).count(),
        "branches": Branch.objects.filter(organization=organization).count(),
    }


def assert_within_limit(organization, resource):
    """resource: members | books | staff | branches"""
    from subscriptions.services import get_limit_for

    if organization is None:
        return
    limit = get_limit_for(organization, resource)
    if limit is None:
        return
    usage = get_usage_counts(organization)[resource]
    if usage >= limit:
        raise SubscriptionLimitExceeded(
            f"Subscription limit reached for {resource}. Maximum allowed: {limit}."
        )


def log_org_event(request, action, module, description, organization=None):
    from audit.models import AuditLog

    user = getattr(request, "user", None)
    org = organization or getattr(request, "organization", None)
    ip = None
    if request is not None:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        organization=org,
        action=action,
        module=module,
        description=description,
        ip_address=ip,
    )
