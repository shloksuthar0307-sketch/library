from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from accounts.models import User
from accounts.permissions import deny_members, staff_required
from organizations.mixins import get_tenant_object_or_404
from organizations.services import SubscriptionLimitExceeded, assert_within_limit, log_org_event

from .models import MemberProfile


@login_required
@deny_members
def list_view(request):
    base_qs = MemberProfile.objects.for_request(request).select_related("user")
    query = request.GET.get("q", "").strip()
    members = base_qs
    if query:
        members = members.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(member_id__icontains=query)
        )
    members = members.order_by("-membership_date")
    return render(
        request,
        "members/member_list.html",
        {
            "members": members,
            "current_q": query,
            "total_count": base_qs.count(),
            "active_count": base_qs.filter(status="ACTIVE").count(),
            "suspended_count": base_qs.filter(status="SUSPENDED").count(),
        },
    )


@login_required
@staff_required
def create_member(request):
    if request.method != "POST":
        return redirect("members:list")

    org = request.organization
    try:
        assert_within_limit(org, "members")
    except SubscriptionLimitExceeded as exc:
        messages.error(request, exc.messages[0] if exc.messages else str(exc))
        return redirect("members:list")

    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    member_id = request.POST.get("member_id", "").strip()

    if User.objects.filter(username=username).exists():
        messages.error(request, f'Username "{username}" already exists.')
        return redirect("members:list")
    if email and User.objects.filter(email=email).exists():
        messages.error(request, f'Email "{email}" is already registered.')
        return redirect("members:list")
    if MemberProfile.objects.filter(organization=org, member_id=member_id).exists():
        messages.error(request, "Member ID already exists in this organization.")
        return redirect("members:list")

    password = User.objects.make_random_password(length=12)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.MEMBER,
        organization=org,
        branch=request.user.branch,
    )
    MemberProfile.objects.create(
        user=user,
        member_id=member_id,
        status="ACTIVE",
        organization=org,
        home_branch=request.user.branch,
    )
    log_org_event(request, "Member Added", "Members", f"Registered {username}", org)
    messages.success(
        request,
        f'Member "{first_name} {last_name}" registered successfully! Temporary password: {password}',
    )
    return redirect("members:list")


@login_required
@deny_members
def member_detail(request, pk):
    member = get_tenant_object_or_404(MemberProfile, request, pk=pk)
    return render(request, "members/member_detail.html", {"member": member})


@login_required
@staff_required
def member_edit(request, pk):
    member = get_tenant_object_or_404(MemberProfile, request, pk=pk)
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        member_id = request.POST.get("member_id", "").strip()
        status = request.POST.get("status", "ACTIVE")
        user = member.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        member.member_id = member_id
        member.status = status
        member.save()
        messages.success(request, f'Member "{first_name} {last_name}" updated successfully!')
    return redirect("members:list")


@login_required
@staff_required
def member_delete(request, pk):
    member = get_tenant_object_or_404(MemberProfile, request, pk=pk)
    if request.method == "POST":
        name = member.user.get_full_name() or member.user.username
        org = member.organization
        log_org_event(request, "User Deleted", "Members", f"Deleted member {name}", org)
        member.user.delete()
        messages.success(request, f'Member "{name}" has been deleted.')
    return redirect("members:list")
