from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.permissions import org_admin_required
from books.models import Book, BookCopy, Category
from members.models import MemberProfile
from organizations.models import Branch
from organizations.services import get_or_create_settings, log_org_event
from reservations.models import Reservation
from transactions.models import Transaction


@login_required
def home(request):
    user = request.user
    if user.is_superadmin() and not request.impersonating_organization:
        return redirect("organizations:platform")

    org = request.organization
    books = Book.objects.for_request(request)
    members = MemberProfile.objects.for_request(request)
    transactions = Transaction.objects.for_request(request)
    reservations = Reservation.objects.for_request(request)

    is_member_view = user.is_member() and not user.is_staff_member()
    
    if is_member_view:
        transactions = transactions.filter(member=user)
        reservations = reservations.filter(member=user)

    selected_branch = None
    branch_id = request.GET.get("branch")
    if branch_id and org:
        selected_branch = Branch.objects.for_organization(org).filter(pk=branch_id).first()
        if selected_branch:
            transactions = transactions.filter(branch=selected_branch)
            copy_book_ids = BookCopy.objects.for_organization(org).filter(branch=selected_branch).values("book_id")
            books = books.filter(pk__in=copy_book_ids)

    today = timezone.now().date()
    issued = transactions.filter(status="ISSUED")
    overdue = transactions.filter(Q(status="OVERDUE") | Q(status="ISSUED", due_date__lt=today))
    pending_fines_qs = transactions.filter(fine_amount__gt=0, fine_paid=False)
    
    # Calculate Due Soon (next 3 days)
    due_soon_date = today + timezone.timedelta(days=3)
    due_soon = transactions.filter(status="ISSUED", due_date__gte=today, due_date__lte=due_soon_date)

    categories = (
        Category.objects.for_request(request)
        .annotate(book_count=Count("books"))
        .order_by("-book_count")[:8]
    )

    is_staff_only_view = user.role == "STAFF" and not user.is_superadmin() and not user.is_org_admin()
    
    context = {
        "total_books": books.count(),
        "total_members": members.filter(status="ACTIVE").count(),
        "books_issued": issued.count(),
        "overdue_books": overdue.count(),
        "due_soon_count": due_soon.count(),
        "pending_fines": pending_fines_qs.aggregate(total=Sum("fine_amount"))["total"] or 0,
        "reservation_count": reservations.exclude(
            status__in=["CANCELLED", "EXPIRED", "COMPLETED", "COLLECTED"]
        ).count(),
        "recent_transactions": transactions.select_related("book", "member").order_by("-issue_date")[:8],
        "categories": categories,
        "branches": Branch.objects.for_organization(org) if org else Branch.objects.none(),
        "selected_branch": selected_branch,
        "is_member_view": is_member_view,
        "is_staff_only_view": is_staff_only_view,
    }
    
    if is_member_view:
        # Additional context for Member Dashboard
        from transactions.models import DigitalLoan
        context["active_loans"] = issued.select_related("book").order_by("due_date")
        context["active_reservations"] = reservations.exclude(
            status__in=["CANCELLED", "EXPIRED", "COMPLETED", "COLLECTED"]
        ).select_related("book").order_by("-reservation_date")
        context["digital_loans"] = DigitalLoan.objects.filter(
            member=user, 
            is_revoked=False, 
            expires_at__gt=timezone.now()
        ).select_related("asset__book").order_by("expires_at")
        
        # Mock data for UI
        context["notifications"] = None # Mocked in template
        context["recommended_books"] = books.order_by("?")[:4]
        context["recently_viewed"] = books.order_by("-created_date")[:4]
        context["saved_books"] = books.order_by("?")[:3]
        
        # Reading Activity Mock
        context["activity_stats"] = {
            "borrowed_month": 4,
            "returned_month": 2,
            "renewals": 1,
            "reservations": context["reservation_count"]
        }
        
        # Announcements Mock
        context["announcements"] = [
            {"title": "Library Holiday Hours", "date": "10 Sep", "message": "The library will be closed this Friday."},
            {"title": "New Tech Books", "date": "08 Sep", "message": "15 new books added to the CS section!"}
        ]
        
        return render(request, "dashboard/member_home.html", context)

    if is_staff_only_view:
        # Calculate daily stats for Staff
        from transactions.models import Fine
        today_issued = transactions.filter(issue_date=today).count()
        today_returned = transactions.filter(return_date=today, status="RETURNED").count()
        today_fines = Fine.objects.for_request(request).filter(is_paid=True, paid_at__date=today).aggregate(total=Sum("amount"))["total"] or 0
        
        context["today_stats"] = {
            "issued": today_issued,
            "returned": today_returned,
            "renewals": 0, # Assuming no renewal tracking model for now
            "reservations": reservations.filter(reservation_date=today).count(),
            "fines": today_fines,
            "overdue": overdue.count(),
        }
        context["overdue_transactions"] = overdue[:5]
        return render(request, "dashboard/staff_home.html", context)

    return render(request, "dashboard/admin_home.html", context)


@login_required
@org_admin_required
def settings_view(request):
    org = request.organization
    if request.user.is_superadmin() and org is None:
        messages.info(request, "Switch into an organization to edit tenant settings.")
        return redirect("organizations:list")

    setting = get_or_create_settings(org)
    if request.method == "POST":
        setting.library_name = request.POST.get("library_name", setting.library_name)
        setting.library_email = request.POST.get("library_email", setting.library_email)
        setting.library_phone = request.POST.get("library_phone", setting.library_phone)
        setting.library_address = request.POST.get("library_address", setting.library_address)
        setting.max_books_per_member = int(request.POST.get("max_books_per_member") or setting.max_books_per_member)
        setting.default_borrow_days = int(request.POST.get("default_borrow_days") or setting.default_borrow_days)
        setting.renewal_limit = int(request.POST.get("renewal_limit") or setting.renewal_limit)
        setting.fine_per_day = request.POST.get("fine_per_day") or setting.fine_per_day
        setting.enable_late_fines = request.POST.get("enable_late_fines") == "on"
        setting.allow_self_renewal = request.POST.get("allow_self_renewal") == "on"
        setting.email_notifications = request.POST.get("email_notifications") == "on"
        setting.overdue_notifications = request.POST.get("overdue_notifications") == "on"
        setting.reservation_notifications = request.POST.get("reservation_notifications") == "on"
        setting.require_2fa = request.POST.get("require_2fa") == "on"
        setting.session_timeout_minutes = int(
            request.POST.get("session_timeout_minutes") or setting.session_timeout_minutes
        )
        setting.primary_color = request.POST.get("primary_color") or setting.primary_color
        setting.secondary_color = request.POST.get("secondary_color") or setting.secondary_color
        if request.FILES.get("library_logo"):
            setting.library_logo = request.FILES["library_logo"]
        setting.save()
        org.name = setting.library_name or org.name
        org.email = setting.library_email or org.email
        org.save(update_fields=["name", "email", "updated_at"])
        log_org_event(request, "Settings Changed", "Settings", "Updated organization settings", org)
        messages.success(request, "Settings saved for this organization only.")
        return redirect("dashboard:settings")

    branches = Branch.objects.for_organization(org)
    return render(
        request,
        "dashboard/settings.html",
        {"library_settings": setting, "org": org, "branches": branches},
    )


@login_required
def help_center_view(request):
    return render(request, "dashboard/help_center.html")


@login_required
def guide_getting_started(request):
    return render(request, "dashboard/guides/getting_started.html")


@login_required
def guide_borrowing_returns(request):
    return render(request, "dashboard/guides/borrowing_returns.html")


@login_required
def guide_fines_policies(request):
    return render(request, "dashboard/guides/fines_policies.html")

