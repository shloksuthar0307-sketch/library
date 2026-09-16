from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponseForbidden

from .models import SubscriptionPlan, OrganizationSubscription, Invoice, Payment
from accounts.models import User
from books.models import Book
from organizations.models import Branch

@login_required
def billing_dashboard(request):
    if not request.user.is_org_admin():
        return HttpResponseForbidden("You do not have permission to view this page.")
    org = request.organization
    if not org:
        messages.error(request, "No organization context found.")
        return redirect('dashboard:home')
    
    # Get or create trial subscription
    subscription = getattr(org, 'subscription', None)
    if not subscription:
        free_plan = SubscriptionPlan.objects.filter(code=SubscriptionPlan.Code.FREE).first()
        if free_plan:
            subscription = OrganizationSubscription.objects.create(
                organization=org,
                plan=free_plan,
                status=OrganizationSubscription.Status.TRIAL
            )

    # Current usage stats
    members_count = User.objects.filter(organization=org, role=User.Role.MEMBER).count()
    books_count = Book.objects.filter(organization=org).count()
    staff_count = User.objects.filter(organization=org, role=User.Role.STAFF).count()
    branches_count = Branch.objects.filter(organization=org).count()

    usage = {
        'members': {'count': members_count, 'limit': subscription.plan.max_members},
        'books': {'count': books_count, 'limit': subscription.plan.max_books},
        'staff': {'count': staff_count, 'limit': subscription.plan.max_staff},
        'branches': {'count': branches_count, 'limit': subscription.plan.max_branches},
    }

    # Calculate percentages for progress bars
    for key, data in usage.items():
        if data['limit']:
            data['percent'] = min(100, int((data['count'] / data['limit']) * 100))
        else:
            data['percent'] = 0

    plans = SubscriptionPlan.objects.all().order_by('monthly_price')
    invoices = Invoice.objects.filter(organization=org).order_by('-issued_at')
    payments = Payment.objects.filter(organization=org).order_by('-created_at')

    context = {
        'subscription': subscription,
        'usage': usage,
        'plans': plans,
        'invoices': invoices,
        'payments': payments,
    }
    return render(request, 'subscriptions/billing_dashboard.html', context)

@login_required
def change_plan(request):
    if not request.user.is_org_admin():
        return HttpResponseForbidden("You do not have permission to perform this action.")
    if request.method == "POST":
        org = request.organization
        plan_id = request.POST.get('plan_id')
        try:
            new_plan = SubscriptionPlan.objects.get(pk=plan_id)
            sub = org.subscription
            sub.plan = new_plan
            sub.status = OrganizationSubscription.Status.ACTIVE
            sub.save()
            messages.success(request, f"Successfully upgraded to {new_plan.name} Plan!")
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, "Invalid plan selected.")
    return redirect('subscriptions:dashboard')
