from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from accounts.models import User
from accounts.permissions import deny_members
from books.models import Book, Category
from members.models import MemberProfile
from organizations.models import Branch
from reservations.models import Reservation
from transactions.models import Transaction


@login_required
@deny_members
def index_view(request):
    books = Book.objects.for_request(request)
    members = MemberProfile.objects.for_request(request)
    transactions = Transaction.objects.for_request(request)
    if request.user.role == User.Role.STAFF and request.user.branch_id and not request.user.can_access_all_branches:
        transactions = transactions.filter(Q(branch=request.user.branch) | Q(branch__isnull=True))

    total_circulation = transactions.count()
    loans = transactions.filter(status="ISSUED").count()
    returns = transactions.filter(status__in=["RETURNED", "OVERDUE"]).count()
    context = {
        "total_circulation": total_circulation,
        "loans": loans,
        "returns": returns,
        "total_books": books.count(),
        "active_members": members.filter(status="ACTIVE").count(),
        "total_members": members.count(),
        "pending_fines": transactions.filter(fine_amount__gt=0, fine_paid=False).aggregate(
            total=Sum("fine_amount")
        )["total"]
        or 0,
        "reservations": Reservation.objects.for_request(request).count(),
        "branches": Branch.objects.for_request(request) if hasattr(Branch.objects, "for_request") else Branch.objects.filter(organization=request.organization),
        "top_categories": Category.objects.for_request(request).annotate(total=Count("books")).order_by("-total")[:6],
        "is_global": request.user.is_superadmin() and not request.impersonating_organization,
    }
    return render(request, "reports/index.html", context)
