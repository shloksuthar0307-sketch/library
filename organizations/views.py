from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User
from accounts.permissions import org_admin_required, super_admin_required
from books.models import Book
from dashboard.models import SystemSetting
from members.models import MemberProfile
from organizations.forms import (
    BranchForm,
    OnboardingAdminForm,
    OnboardingBrandingForm,
    OnboardingBranchForm,
    OnboardingOrganizationForm,
    OnboardingRulesForm,
    OrganizationForm,
)
from organizations.middleware import TenantContextMiddleware
from organizations.models import Branch, Organization
from organizations.services import (
    SubscriptionLimitExceeded,
    assert_within_limit,
    get_or_create_settings,
    get_usage_counts,
    log_org_event,
)
from subscriptions.models import OrganizationSubscription, SubscriptionPlan
from transactions.models import Transaction


def _onboarding_session(request):
    return request.session.setdefault("org_onboarding", {})


@super_admin_required
def platform_dashboard(request):
    organizations = Organization.objects.all()
    context = {
        "total_organizations": organizations.count(),
        "active_organizations": organizations.filter(is_active=True).count(),
        "suspended_organizations": organizations.filter(
            Q(is_active=False) | Q(subscription_status=Organization.SubscriptionStatus.SUSPENDED)
        ).count(),
        "total_users": User.objects.count(),
        "total_books": Book.objects.count(),
        "total_members": MemberProfile.objects.count(),
        "total_transactions": Transaction.objects.count(),
        "platform_revenue": OrganizationSubscription.objects.select_related("plan").aggregate(
            total=Sum("plan__monthly_price")
        )["total"]
        or Decimal("0.00"),
        "subscription_distribution": list(
            OrganizationSubscription.objects.values("plan__name").annotate(total=Count("id"))
        ),
        "recent_organizations": organizations.order_by("-created_at")[:8],
    }
    return render(request, "organizations/super_admin_dashboard.html", context)


@super_admin_required
def organization_list(request):
    qs = Organization.objects.all().annotate(
        user_count=Count("users", distinct=True),
        book_count=Count("books", distinct=True),
        member_count=Count("member_profiles", distinct=True),
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    org_type = request.GET.get("type", "all")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(slug__icontains=query))
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "suspended":
        qs = qs.filter(is_active=False)
    if org_type != "all":
        qs = qs.filter(organization_type=org_type)
    return render(
        request,
        "organizations/organization_list.html",
        {
            "organizations": qs.order_by("name"),
            "current_q": query,
            "current_status": status,
            "current_type": org_type,
            "org_types": Organization.OrganizationType.choices,
        },
    )


@super_admin_required
def organization_detail(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    usage = get_usage_counts(organization)
    return render(
        request,
        "organizations/organization_detail.html",
        {
            "org": organization,
            "usage": usage,
            "branches": organization.branches.all(),
            "users": organization.users.all()[:50],
            "settings": get_or_create_settings(organization),
            "audit_logs": organization.audit_logs.all()[:25],
        },
    )


@super_admin_required
def organization_edit(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        form = OrganizationForm(request.POST, request.FILES, instance=organization)
        if form.is_valid():
            form.save()
            log_org_event(request, "Organization Updated", "Organizations", f"Updated {organization.name}", organization)
            messages.success(request, "Organization updated.")
            return redirect("organizations:detail", pk=organization.pk)
    else:
        form = OrganizationForm(instance=organization)
    return render(request, "organizations/organization_form.html", {"form": form, "org": organization})


@super_admin_required
def organization_toggle(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        organization.is_active = not organization.is_active
        if not organization.is_active:
            organization.subscription_status = Organization.SubscriptionStatus.SUSPENDED
        elif organization.subscription_status == Organization.SubscriptionStatus.SUSPENDED:
            organization.subscription_status = Organization.SubscriptionStatus.ACTIVE
        organization.save(update_fields=["is_active", "subscription_status", "updated_at"])
        state = "activated" if organization.is_active else "suspended"
        log_org_event(request, f"Organization {state.title()}", "Organizations", f"{organization.name} {state}", organization)
        messages.success(request, f"Organization {state}.")
    return redirect("organizations:detail", pk=organization.pk)


@super_admin_required
def switch_organization(request, pk):
    organization = get_object_or_404(Organization, pk=pk)
    request.session[TenantContextMiddleware.SESSION_ORG_KEY] = str(organization.pk)
    messages.info(request, f"Now viewing organization: {organization.name}")
    return redirect("dashboard:home")


@super_admin_required
def clear_organization_switch(request):
    request.session.pop(TenantContextMiddleware.SESSION_ORG_KEY, None)
    messages.info(request, "Returned to platform view.")
    return redirect("organizations:platform")


@super_admin_required
def onboarding_wizard(request):
    data = request.session.get("org_onboarding", {})
    step = int(request.GET.get("step") or data.get("step") or 1)
    if request.method == "POST":
        step = int(request.POST.get("step", step))
        forms_by_step = {
            1: OnboardingOrganizationForm,
            2: OnboardingBranchForm,
            3: OnboardingAdminForm,
            4: OnboardingRulesForm,
            5: OnboardingBrandingForm,
        }
        if step < 6:
            form = forms_by_step[step](request.POST, request.FILES)
            if form.is_valid():
                payload = {k: str(v) if k != "logo" else v for k, v in form.cleaned_data.items()}
                if step == 5 and request.FILES.get("logo"):
                    request.session["onboarding_logo_name"] = request.FILES["logo"].name
                data.update(form.cleaned_data)
                # Store non-file fields in session
                serializable = {k: (str(v) if v is not None else "") for k, v in form.cleaned_data.items() if k != "logo"}
                data.update(serializable)
                data["step"] = step + 1
                request.session["org_onboarding"] = data
                request.session.modified = True
                if step == 5:
                    logo = request.FILES.get("logo")
                    return _complete_onboarding(request, data, logo)
                return redirect(f"{request.path}?step={step + 1}")
        else:
            return _complete_onboarding(request, data, None)
    else:
        forms_by_step = {
            1: OnboardingOrganizationForm,
            2: OnboardingBranchForm,
            3: OnboardingAdminForm,
            4: OnboardingRulesForm,
            5: OnboardingBrandingForm,
        }
        initial = {k: v for k, v in data.items() if k != "step"}
        form = forms_by_step.get(min(step, 5), OnboardingOrganizationForm)(initial=initial)

    return render(
        request,
        "organizations/onboarding.html",
        {"form": form, "step": min(step, 6), "data": data},
    )


def _complete_onboarding(request, data, logo):
    with transaction.atomic():
        org = Organization.objects.create(
            name=data["name"],
            organization_type=data.get("organization_type") or Organization.OrganizationType.OTHER,
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            country=data.get("country", ""),
            currency=data.get("currency") or "INR",
            default_fine_per_day=Decimal(str(data.get("fine_per_day") or "5")),
            is_active=True,
            subscription_status=Organization.SubscriptionStatus.TRIAL,
        )
        if logo:
            org.logo = logo
            org.save(update_fields=["logo"])

        branch = Branch.objects.create(
            organization=org,
            name=data.get("branch_name") or "Main Branch",
            code=(data.get("branch_code") or "MAIN").upper(),
            address=data.get("branch_address", ""),
            is_main=True,
        )
        admin = User.objects.create_user(
            username=data["admin_username"],
            email=data["admin_email"],
            password=data["admin_password"],
            first_name=data.get("admin_first_name", ""),
            last_name=data.get("admin_last_name", ""),
            role=User.Role.ORG_ADMIN,
            organization=org,
            branch=branch,
            is_verified=True,
        )
        settings = get_or_create_settings(org)
        settings.max_books_per_member = int(data.get("borrow_limit") or 3)
        settings.default_borrow_days = int(data.get("borrow_duration") or 14)
        settings.fine_per_day = Decimal(str(data.get("fine_per_day") or "5"))
        settings.primary_color = data.get("primary_color") or "#111111"
        settings.secondary_color = data.get("secondary_color") or "#10B981"
        if logo:
            settings.library_logo = logo
        settings.library_name = org.name
        settings.library_email = org.email
        settings.save()

        plan = SubscriptionPlan.objects.filter(code=SubscriptionPlan.Code.FREE).first()
        if plan:
            OrganizationSubscription.objects.create(
                organization=org,
                plan=plan,
                status=OrganizationSubscription.Status.TRIAL,
            )

        log_org_event(request, "Organization Created", "Organizations", f"Onboarded {org.name}", org)
        log_org_event(request, "User Created", "Accounts", f"Created org admin {admin.username}", org)
        log_org_event(request, "Branch Created", "Organizations", f"Created branch {branch.code}", org)

    request.session.pop("org_onboarding", None)
    messages.success(request, f'Organization "{org.name}" successfully created.')
    return redirect("organizations:detail", pk=org.pk)


@login_required
@org_admin_required
def branch_list(request):
    organization = request.organization
    if request.user.is_superadmin() and organization is None:
        messages.error(request, "Select an organization first.")
        return redirect("organizations:list")
    branches = Branch.objects.for_organization(organization)
    if request.method == "POST":
        try:
            assert_within_limit(organization, "branches")
        except SubscriptionLimitExceeded as exc:
            messages.error(request, exc.messages[0] if exc.messages else str(exc))
            return redirect("organizations:branches")
        form = BranchForm(request.POST, organization=organization)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.organization = organization
            branch.code = branch.code.upper()
            branch.save()
            log_org_event(request, "Branch Created", "Organizations", f"Created {branch.name}", organization)
            messages.success(request, "Branch created.")
            return redirect("organizations:branches")
    else:
        form = BranchForm(organization=organization)
    return render(request, "organizations/branch_list.html", {"branches": branches, "form": form})


@login_required
@org_admin_required
def organization_profile(request):
    organization = request.organization
    if organization is None:
        messages.error(request, "No organization context.")
        return redirect("dashboard:home")
    if request.method == "POST":
        form = OrganizationForm(request.POST, request.FILES, instance=organization)
        if form.is_valid():
            # Org admins cannot toggle platform-level active flag via this form
            instance = form.save(commit=False)
            instance.is_active = organization.is_active
            instance.save()
            log_org_event(request, "Organization Updated", "Organizations", "Updated organization profile", organization)
            messages.success(request, "Organization profile saved.")
            return redirect("organizations:profile")
    else:
        form = OrganizationForm(instance=organization)
    return render(request, "organizations/organization_form.html", {"form": form, "org": organization, "tenant_mode": True})
