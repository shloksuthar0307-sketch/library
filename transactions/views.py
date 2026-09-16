import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User
from accounts.permissions import staff_required
from books.models import Book, BookCopy
from dashboard.models import SystemSetting
from organizations.mixins import get_tenant_object_or_404
from organizations.services import apply_branch_scope, get_or_create_settings, log_org_event

from .models import Fine, Transaction


def is_staff_or_above(user):
    return getattr(user, "is_superuser", False) or user.is_staff_member()


@login_required
@staff_required
def issue_book(request):
    org = request.organization
    books = apply_branch_scope(
        Book.objects.for_request(request).filter(available_copies__gt=0),
        request,
    )
    # Books may not have branch; copies do. Keep catalog filter org-scoped.
    books = Book.objects.for_request(request).filter(available_copies__gt=0)
    members = User.objects.filter(role=User.Role.MEMBER, organization=org) if org else User.objects.none()
    if request.user.is_superadmin() and org is None:
        members = User.objects.filter(role=User.Role.MEMBER)

    if request.method == "POST":
        member_id = request.POST.get("member_id")
        book_id = request.POST.get("book_id")
        try:
            member = User.objects.get(pk=member_id, role=User.Role.MEMBER)
            book = Book.objects.for_request(request).get(pk=book_id)
            if org and member.organization_id and str(member.organization_id) != str(org.pk):
                messages.error(request, "Member does not belong to this organization.")
                return redirect("transactions:issue")
            if book.available_copies <= 0:
                messages.error(request, "Book is not available.")
                return redirect("transactions:issue")

            setting = get_or_create_settings(org) or SystemSetting.objects.filter(organization=org).first()
            days = setting.default_borrow_days if setting else 14
            due = timezone.now().date() + timedelta(days=days)

            copy_qs = BookCopy.objects.for_request(request).filter(
                book=book,
                status=BookCopy.Status.AVAILABLE,
            )
            copy_qs = apply_branch_scope(copy_qs, request)
            book_copy = copy_qs.first()
            if request.user.role == User.Role.STAFF and request.user.branch_id and book_copy and book_copy.branch_id:
                if book_copy.branch_id != request.user.branch_id and not request.user.can_access_all_branches:
                    messages.error(request, "You cannot issue copies from another branch.")
                    return redirect("transactions:issue")

            with db_transaction.atomic():
                txn = Transaction.objects.create(
                    member=member,
                    book=book,
                    book_copy=book_copy,
                    due_date=due,
                    organization=org or book.organization,
                    branch=getattr(book_copy, "branch", None) or request.user.branch,
                    issued_by=request.user,
                )
                if book_copy:
                    book_copy.status = BookCopy.Status.ISSUED
                    book_copy.save(update_fields=["status", "is_available", "updated_at"])
                    book.sync_copy_counts()
                else:
                    book.available_copies -= 1
                    book.save()
            log_org_event(request, "Book Issued", "Circulation", f"Issued {book.title} to {member.username}", txn.organization)
            messages.success(request, f'"{book.title}" issued to {member.get_full_name() or member.username}!')
            return redirect("transactions:history")
        except User.DoesNotExist:
            messages.error(request, "Member not found.")
        except Book.DoesNotExist:
            messages.error(request, "Book not found.")
    members_data = {
        str(m.id): {
            "name": m.get_full_name() or m.username,
            "uid": getattr(m, 'member_profile', None).member_id if hasattr(m, 'member_profile') else m.email,
            "email": m.email,
            "max_limit": getattr(m, 'member_profile', None).max_book_limit if hasattr(m, 'member_profile') else 5,
        }
        for m in members
    }
    
    books_data = {
        str(b.id): {
            "title": b.title,
            "author": str(b.author.name) if getattr(b, 'author', None) and hasattr(b.author, 'name') else str(getattr(b, 'author', '')),
            "available": b.available_copies
        }
        for b in books
    }

    recent_transactions = Transaction.objects.for_request(request).select_related('book', 'member').order_by('-issue_date')[:5]
    return render(request, "transactions/issue_form.html", {
        "books": books, 
        "members": members,
        "recent_transactions": recent_transactions,
        "members_data_json": json.dumps(members_data),
        "books_data_json": json.dumps(books_data)
    })


@login_required
@staff_required
def bulk_issue(request):
    org = request.organization
    books = apply_branch_scope(
        Book.objects.for_request(request).filter(available_copies__gt=0),
        request,
    )
    members = User.objects.filter(role=User.Role.MEMBER, organization=org) if org else User.objects.none()
    if request.user.is_superadmin() and org is None:
        members = User.objects.filter(role=User.Role.MEMBER)

    if request.method == "POST":
        member_id = request.POST.get("member_id")
        book_ids = request.POST.getlist("book_ids")
        if not member_id or not book_ids:
            messages.error(request, "Please select a member and at least one book.")
            return redirect("transactions:bulk_issue")
            
        try:
            member = User.objects.get(pk=member_id, role=User.Role.MEMBER)
            issued_count = 0
            
            with db_transaction.atomic():
                for book_id in book_ids:
                    book = Book.objects.for_request(request).get(pk=book_id)
                    if book.available_copies <= 0:
                        continue
                        
                    setting = get_or_create_settings(org) or SystemSetting.objects.filter(organization=org).first()
                    days = setting.default_borrow_days if setting else 14
                    due = timezone.now().date() + timedelta(days=days)

                    copy_qs = BookCopy.objects.for_request(request).filter(
                        book=book,
                        status=BookCopy.Status.AVAILABLE,
                    )
                    copy_qs = apply_branch_scope(copy_qs, request)
                    book_copy = copy_qs.first()
                    
                    txn = Transaction.objects.create(
                        member=member,
                        book=book,
                        book_copy=book_copy,
                        due_date=due,
                        organization=org or book.organization,
                        branch=getattr(book_copy, "branch", None) or request.user.branch,
                        issued_by=request.user,
                    )
                    if book_copy:
                        book_copy.status = BookCopy.Status.ISSUED
                        book_copy.save(update_fields=["status", "is_available", "updated_at"])
                        book.sync_copy_counts()
                    else:
                        book.available_copies -= 1
                        book.save()
                    issued_count += 1
                    
            log_org_event(request, "Bulk Issue", "Circulation", f"Issued {issued_count} books to {member.username}", org)
            messages.success(request, f'Successfully issued {issued_count} books to {member.get_full_name() or member.username}!')
            return redirect("transactions:history")
            
        except User.DoesNotExist:
            messages.error(request, "Member not found.")
            return redirect("transactions:bulk_issue")

    recent_transactions = Transaction.objects.for_request(request).select_related('book', 'member').order_by('-issue_date')[:5]
    return render(request, "transactions/bulk_issue_form.html", {
        "books": books, 
        "members": members,
        "recent_transactions": recent_transactions
    })


@login_required
@staff_required
def special_reserve(request):
    org = request.organization
    books = apply_branch_scope(
        Book.objects.for_request(request).filter(available_copies__gt=0),
        request,
    )
    members = User.objects.filter(role=User.Role.MEMBER, organization=org) if org else User.objects.none()
    if request.user.is_superadmin() and org is None:
        members = User.objects.filter(role=User.Role.MEMBER)

    if request.method == "POST":
        member_id = request.POST.get("member_id")
        book_id = request.POST.get("book_id")
        custom_due_date_str = request.POST.get("custom_due_date")
        
        if not member_id or not book_id or not custom_due_date_str:
            messages.error(request, "Please select a member, a book, and a custom due date.")
            return redirect("transactions:special_reserve")
            
        try:
            member = User.objects.get(pk=member_id, role=User.Role.MEMBER)
            book = Book.objects.for_request(request).get(pk=book_id)
            
            from django.utils.dateparse import parse_datetime
            custom_due_date = parse_datetime(custom_due_date_str)
            if not custom_due_date:
                messages.error(request, "Invalid date/time format.")
                return redirect("transactions:special_reserve")
                
            if book.available_copies <= 0:
                messages.error(request, "No copies available for this book.")
                return redirect("transactions:special_reserve")

            with db_transaction.atomic():
                copy_qs = BookCopy.objects.for_request(request).filter(
                    book=book,
                    status=BookCopy.Status.AVAILABLE,
                )
                copy_qs = apply_branch_scope(copy_qs, request)
                book_copy = copy_qs.first()
                
                txn = Transaction.objects.create(
                    member=member,
                    book=book,
                    book_copy=book_copy,
                    due_date=custom_due_date,
                    organization=org or book.organization,
                    branch=getattr(book_copy, "branch", None) or request.user.branch,
                    issued_by=request.user,
                )
                
                if book_copy:
                    book_copy.status = BookCopy.Status.ISSUED
                    book_copy.save(update_fields=["status", "is_available", "updated_at"])
                    book.sync_copy_counts()
                else:
                    book.available_copies -= 1
                    book.save()
                    
            log_org_event(request, "Special Reserve Issue", "Circulation", f"Issued {book.title} to {member.username} until {custom_due_date}", org)
            messages.success(request, f'Special Reserve: "{book.title}" issued to {member.get_full_name() or member.username} until {custom_due_date}!')
            return redirect("transactions:history")
            
        except User.DoesNotExist:
            messages.error(request, "Member not found.")
        except Book.DoesNotExist:
            messages.error(request, "Book not found.")
            
    recent_transactions = Transaction.objects.for_request(request).select_related('book', 'member').order_by('-issue_date')[:5]
    return render(request, "transactions/special_reserve_form.html", {
        "books": books, 
        "members": members,
        "recent_transactions": recent_transactions
    })


@login_required
@staff_required
def return_book(request):
    active_transactions = apply_branch_scope(
        Transaction.objects.for_request(request).filter(status="ISSUED").select_related("book", "member"),
        request,
    )

    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        try:
            txn = apply_branch_scope(
                Transaction.objects.for_request(request).filter(status="ISSUED"),
                request,
            ).get(pk=transaction_id)
            txn.return_date = timezone.now().date()
            txn.status = "RETURNED"
            txn.returned_to = request.user

            setting = get_or_create_settings(txn.organization)
            fine_per_day = Decimal(str(setting.fine_per_day)) if setting else Decimal("5.00")
            enable_fines = setting.enable_late_fines if setting else True

            if txn.return_date > txn.due_date and enable_fines:
                days_late = (txn.return_date - txn.due_date).days
                txn.fine_amount = days_late * fine_per_day
                txn.status = "OVERDUE"
                Fine.objects.create(
                    organization=txn.organization,
                    member=txn.member,
                    transaction=txn,
                    amount=txn.fine_amount,
                    reason=f"Overdue by {days_late} day(s)",
                )

            txn.save()
            if txn.book_copy:
                txn.book_copy.status = BookCopy.Status.AVAILABLE
                txn.book_copy.save()
                txn.book.sync_copy_counts()
            else:
                txn.book.available_copies += 1
                txn.book.save()

            log_org_event(request, "Book Returned", "Circulation", f"Returned {txn.book.title}", txn.organization)
            fine_msg = f" Fine: ₹{txn.fine_amount}" if txn.fine_amount > 0 else ""
            messages.success(request, f"Book returned successfully!{fine_msg}")
            return redirect("transactions:history")
        except Transaction.DoesNotExist:
            messages.error(request, "Active transaction not found.")

    return render(request, "transactions/return_form.html", {"active_transactions": active_transactions})


@login_required
def transaction_history(request):
    if request.user.is_member() and not request.user.is_staff_member():
        transactions = Transaction.objects.for_request(request).filter(member=request.user)
    else:
        transactions = apply_branch_scope(Transaction.objects.for_request(request), request)
    transactions = transactions.select_related("book", "member").order_by("-issue_date")
    return render(request, "transactions/history.html", {"transactions": transactions})


@login_required
def fine_list(request):
    is_staff = is_staff_or_above(request.user)
    if request.user.is_member() and not is_staff:
        fines = Transaction.objects.for_request(request).filter(member=request.user, fine_amount__gt=0)
    else:
        fines = apply_branch_scope(
            Transaction.objects.for_request(request).filter(fine_amount__gt=0),
            request,
        )
    fines = fines.select_related("book", "member").order_by("-issue_date")
    total_outstanding = fines.filter(fine_paid=False).aggregate(total=Sum("fine_amount"))["total"] or Decimal("0.00")
    total_collected = fines.filter(fine_paid=True).aggregate(total=Sum("fine_amount"))["total"] or Decimal("0.00")
    return render(
        request,
        "transactions/fines.html",
        {
            "fines": fines,
            "total_outstanding": total_outstanding,
            "total_collected": total_collected,
            "unpaid_count": fines.filter(fine_paid=False).count(),
            "total_count": fines.count(),
            "is_staff": is_staff,
        },
    )


@login_required
@staff_required
def mark_fine_paid(request, pk):
    if request.method == "POST":
        txn = get_tenant_object_or_404(Transaction, request, pk=pk)
        txn.fine_paid = True
        txn.save(update_fields=["fine_paid"])
        Fine.objects.filter(transaction=txn, organization=txn.organization).update(
            is_paid=True,
            paid_at=timezone.now(),
        )
        messages.success(request, f"Fine of ₹{txn.fine_amount} marked as paid.")
    return redirect("transactions:fines")
