from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User
from books.models import Book
from organizations.mixins import get_tenant_object_or_404
from organizations.services import apply_branch_scope

from .models import Reservation


@login_required
def list_view(request):
    if request.user.is_member() and not request.user.is_staff_member():
        reservations = Reservation.objects.for_request(request).filter(member=request.user)
    else:
        reservations = apply_branch_scope(Reservation.objects.for_request(request), request)
    reservations = reservations.select_related("book", "member").order_by("-reservation_date")
    org = request.organization
    return render(
        request,
        "reservations/reservation_list.html",
        {
            "reservations": reservations,
            "total_count": reservations.count(),
            "pending_count": reservations.filter(status__in=["PENDING", "WAITING"]).count(),
            "ready_count": reservations.filter(status__in=["APPROVED", "AVAILABLE"]).count(),
            "cancelled_count": reservations.filter(status="CANCELLED").count(),
            "members_list": User.objects.filter(organization=org, role=User.Role.MEMBER)
            if org
            else User.objects.none(),
            "books_list": Book.objects.for_request(request),
        },
    )


@login_required
def create_reservation(request):
    if request.method != "POST":
        return redirect("reservations:list")

    org = request.organization
    member_id = request.POST.get("member_id")
    book_id = request.POST.get("book_id")
    expiry_date = request.POST.get("expiry_date") or None

    try:
        if request.user.is_member() and not request.user.is_staff_member():
            member = request.user
        else:
            member = User.objects.get(pk=member_id, organization=org)
        book = Book.objects.for_request(request).get(pk=book_id)
        if member.organization_id and org and str(member.organization_id) != str(org.pk):
            messages.error(request, "Reservation cannot cross organizations.")
            return redirect("reservations:list")
        queue = Reservation.objects.filter(
            organization=org or book.organization,
            book=book,
            status__in=["PENDING", "WAITING", "AVAILABLE", "APPROVED"],
        ).count()
        Reservation.objects.create(
            member=member,
            book=book,
            expiry_date=expiry_date or None,
            status="PENDING",
            organization=org or book.organization,
            branch=request.user.branch,
            queue_position=queue + 1,
        )
        messages.success(request, f'Reservation placed for "{book.title}".')
    except (User.DoesNotExist, Book.DoesNotExist):
        messages.error(request, "Invalid member or book selected.")
    return redirect("reservations:list")


@login_required
def update_status(request, pk):
    if request.user.is_member() and not request.user.is_staff_member():
        messages.error(request, "You cannot update reservation status.")
        return redirect("reservations:list")
    if request.method == "POST":
        reservation = get_tenant_object_or_404(Reservation, request, pk=pk)
        new_status = request.POST.get("status")
        allowed = {choice[0] for choice in Reservation.STATUS_CHOICES}
        if new_status in allowed:
            reservation.status = new_status
            if new_status in {"COLLECTED", "COMPLETED", "AVAILABLE", "APPROVED"}:
                reservation.fulfilled_at = timezone.now()
            reservation.save()
            messages.success(request, f"Reservation status updated to {new_status}.")
    return redirect("reservations:list")
