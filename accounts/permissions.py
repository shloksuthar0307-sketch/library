from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import User


def super_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_superadmin():
            messages.error(request, "Super Admin access is required.")
            return redirect("accounts:forbidden")
        return view_func(request, *args, **kwargs)

    return _wrapped


def org_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_org_admin():
            messages.error(request, "Organization Admin access is required.")
            return redirect("accounts:forbidden")
        return view_func(request, *args, **kwargs)

    return _wrapped


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_staff_member():
            messages.error(request, "Staff access is required.")
            return redirect("accounts:forbidden")
        return view_func(request, *args, **kwargs)

    return _wrapped


def deny_members(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.is_member() and not request.user.is_staff_member():
            messages.error(request, "Members cannot access administration data.")
            return redirect("accounts:forbidden")
        return view_func(request, *args, **kwargs)

    return _wrapped


def require_organization(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if not request.user.is_superadmin() and not getattr(request, "organization", None):
            raise PermissionDenied("No organization context.")
        return view_func(request, *args, **kwargs)

    return _wrapped
