from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import User
from members.models import MemberProfile
from organizations.models import Organization
from books.models import Book
from transactions.models import Transaction
from reservations.models import Reservation


def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        login_input = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Authenticate by either username or email
        user = User.objects.filter(Q(email=login_input) | Q(username=login_input)).first()
        if user and user.check_password(password):
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect_based_on_role(user)
        else:
            messages.error(request, 'Invalid username/email or password.')

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
            return render(request, 'accounts/register.html')

        if email and User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already registered.')
            return render(request, 'accounts/register.html')

        org = Organization.objects.filter(slug="default-smartlibrary-organization").first() or Organization.objects.filter(is_active=True).first()

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.MEMBER,
            organization=org
        )

        MemberProfile.objects.create(
            user=user,
            member_id=f"MEM-{user.id:04d}",
            organization=org
        )

        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('accounts:login')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


def forbidden_view(request):
    return render(request, '403.html', status=403)


def redirect_based_on_role(user):
    if user.is_superadmin() or user.is_org_admin():
        return redirect('dashboard:home')
    elif user.is_staff_member():
        return redirect('books:list')
    else:
        return redirect('books:list')


@login_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()

            # Check email uniqueness (excluding current user)
            if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'This email address is already in use by another account.')
                return redirect('accounts:profile')

            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.phone_number = phone_number

            if 'profile_image' in request.FILES:
                user.profile_image = request.FILES['profile_image']

            user.save()

            # Also update linked MemberProfile if it exists
            if hasattr(user, 'member_profile'):
                profile = user.member_profile
                profile.phone_number = phone_number
                if 'profile_image' in request.FILES:
                    profile.profile_image = request.FILES['profile_image']
                profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')

        elif action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('accounts:profile')

            if len(new_password) < 12:
                messages.error(request, 'New password must be at least 12 characters long.')
                return redirect('accounts:profile')

            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
                return redirect('accounts:profile')

            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # Prevents user from being logged out
            messages.success(request, 'Password updated successfully!')
            return redirect('accounts:profile')

    # Gather contextual stats
    is_admin = user.is_superadmin() or user.is_org_admin()
    is_staff = user.is_staff_member()

    stats = {}
    if is_admin:
        org = user.organization
        stats['books_count'] = Book.objects.for_request(request).count()
        stats['members_count'] = User.objects.filter(role=User.Role.MEMBER)
        if org and not user.is_superadmin():
            stats['members_count'] = stats['members_count'].filter(organization=org)
        stats['members_count'] = stats['members_count'].count()
        stats['active_loans'] = Transaction.objects.for_request(request).filter(status='ISSUED').count()
    else:
        stats['borrowed_books'] = Transaction.objects.filter(member=user, status='ISSUED').count()
        stats['total_history'] = Transaction.objects.filter(member=user).count()
        stats['active_reservations'] = Reservation.objects.filter(member=user, status__in=['PENDING', 'APPROVED']).count()
        stats['unpaid_fines'] = Transaction.objects.filter(member=user, fine_paid=False, fine_amount__gt=0).count()

    context = {
        'profile_user': user,
        'is_admin': is_admin,
        'is_staff': is_staff,
        'stats': stats,
    }
    return render(request, 'accounts/profile.html', context)
