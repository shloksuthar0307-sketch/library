from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import User
from organizations.mixins import get_tenant_object_or_404
from organizations.services import SubscriptionLimitExceeded, assert_within_limit, log_org_event

from .forms import BookForm
from .models import Author, Book, BookCopy, Category, Publisher


def _books_qs(request):
    return Book.objects.for_request(request)


@login_required
def book_list(request):
    books = _books_qs(request)
    categories = Category.objects.for_request(request)

    query = request.GET.get("q", "").strip()
    if query:
        books = books.filter(
            Q(title__icontains=query) | Q(isbn__icontains=query) | Q(author__name__icontains=query)
        )

    category = request.GET.get("category")
    if category and category != "all":
        books = books.filter(category__id=category)

    availability = request.GET.get("availability")
    if availability and availability != "all":
        books = books.filter(status=availability.upper())

    sort = request.GET.get("sort", "-created_date")
    if sort == "title":
        books = books.order_by("title")
    elif sort == "author":
        books = books.order_by("author__name")
    else:
        books = books.order_by("-created_date")

    return render(
        request,
        "books/book_list.html",
        {
            "books": books,
            "categories": categories,
            "current_q": query,
            "current_category": category or "all",
            "current_availability": availability or "all",
            "current_sort": sort,
        },
    )


@login_required
def book_detail(request, pk):
    book = get_tenant_object_or_404(Book, request, pk=pk)
    copies = BookCopy.objects.for_request(request).filter(book=book)
    has_digital = hasattr(book, 'digital_asset')
    return render(request, "books/book_detail.html", {"book": book, "copies": copies, "has_digital": has_digital})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN, User.Role.STAFF])
def book_create(request):
    organization = request.organization
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, organization=organization)
        if form.is_valid():
            try:
                assert_within_limit(organization, "books")
            except SubscriptionLimitExceeded as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
                return redirect("books:list")
            book = form.save(commit=False)
            book.organization = organization
            posted_org = request.POST.get("organization") or request.POST.get("organization_id")
            if posted_org and organization and str(posted_org) != str(organization.pk) and not request.user.is_superadmin():
                messages.error(request, "Invalid organization.")
                return redirect("books:list")
            book.save()
            _ensure_copies(book, organization, request.user.branch)
            log_org_event(request, "Book Added", "Books", f"Added {book.title}", organization)
            messages.success(request, "Book added successfully!")
            return redirect("books:list")
    else:
        form = BookForm(organization=organization)
    return render(request, "books/book_form.html", {"form": form, "title": "Add Book"})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN, User.Role.STAFF])
def book_update(request, pk):
    book = get_tenant_object_or_404(Book, request, pk=pk)
    organization = request.organization or book.organization
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book, organization=organization)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.organization = book.organization
            updated.save()
            log_org_event(request, "Book Updated", "Books", f"Updated {book.title}", book.organization)
            messages.success(request, "Book updated successfully!")
            return redirect("books:detail", pk=book.pk)
    else:
        form = BookForm(instance=book, organization=organization)
    return render(request, "books/book_form.html", {"form": form, "title": "Edit Book", "book": book})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN])
def book_delete(request, pk):
    book = get_tenant_object_or_404(Book, request, pk=pk)
    if request.method == "POST":
        title = book.title
        org = book.organization
        book.delete()
        log_org_event(request, "Book Deleted", "Books", f"Deleted {title}", org)
        messages.success(request, "Book deleted successfully!")
        return redirect("books:list")
    return render(request, "books/book_confirm_delete.html", {"book": book})


@login_required
def category_list(request):
    categories = Category.objects.for_request(request)
    org = request.organization
    
    if request.method == "POST" and request.POST.get("action") == "add_category":
        if not (request.user.is_staff_member() or request.user.is_superadmin() or getattr(request.user, 'role', '') in ['SUPER_ADMIN', 'ORG_ADMIN', 'STAFF']):
            messages.error(request, "You do not have permission to add categories.")
            return redirect("books:categories")
            
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        if name:
            Category.objects.create(name=name, description=description, organization=org)
            messages.success(request, f'Category "{name}" created successfully!')
        else:
            messages.error(request, "Category name is required.")
        return redirect("books:categories")
        
    return render(request, "books/category_list.html", {"categories": categories})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN, User.Role.STAFF])
def author_list(request):
    return render(request, "books/author_list.html", {"authors": Author.objects.for_request(request)})


@login_required
@role_required([User.Role.SUPER_ADMIN, User.Role.ORG_ADMIN, User.Role.STAFF])
def publisher_list(request):
    return render(request, "books/publisher_list.html", {"publishers": Publisher.objects.for_request(request)})


def _ensure_copies(book, organization, branch):
    existing = book.copies.count()
    needed = max(int(book.total_copies or 1) - existing, 0)
    for index in range(needed):
        seq = existing + index + 1
        BookCopy.objects.create(
            book=book,
            organization=organization,
            branch=branch,
            barcode=f"{book.pk}-{seq:04d}",
            accession_number=f"ACC-{book.pk}-{seq:04d}",
            shelf_location=book.shelf_number,
            status=BookCopy.Status.AVAILABLE,
        )
    book.sync_copy_counts()

from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.utils import timezone
import datetime
from transactions.models import DigitalLoan

@login_required
def borrow_digital(request, pk):
    if request.method == "POST":
        book = get_tenant_object_or_404(Book, request, pk=pk)
        if not hasattr(book, 'digital_asset'):
            messages.error(request, "This book is not available digitally.")
            return redirect('books:detail', pk=pk)
        
        # Check if they already have an active loan
        existing = DigitalLoan.objects.filter(
            member=request.user,
            asset=book.digital_asset,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing:
            messages.info(request, "You already have an active digital loan for this book.")
            return redirect('books:detail', pk=pk)

        # Create 14-day loan
        expires_at = timezone.now() + datetime.timedelta(days=14)
        loan = DigitalLoan.objects.create(
            member=request.user,
            asset=book.digital_asset,
            organization=book.organization,
            expires_at=expires_at
        )
        messages.success(request, f"Successfully borrowed {book.title} digitally until {expires_at.strftime('%b %d, %Y')}.")
    
    return redirect('books:detail', pk=pk)

@login_required
def serve_digital_asset(request, token):
    loan = DigitalLoan.objects.filter(access_token=token).first()
    if not loan:
        raise Http404("Invalid access token")
    
    if loan.member != request.user:
        return HttpResponseForbidden("You are not authorized to view this file.")
        
    if loan.is_revoked or loan.expires_at < timezone.now():
        return HttpResponseForbidden("This digital loan has expired or been revoked.")
        
    asset = loan.asset
    if not asset.file:
        raise Http404("File not found")
        
    response = HttpResponse(asset.file.read(), content_type='application/pdf' if asset.format == 'PDF' else 'application/epub+zip')
    response['Content-Disposition'] = f'inline; filename="{asset.file.name.split("/")[-1]}"'
    return response
