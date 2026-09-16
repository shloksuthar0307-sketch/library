from subscriptions.models import OrganizationSubscription, SubscriptionPlan


RESOURCE_FIELD = {
    "members": "max_members",
    "books": "max_books",
    "staff": "max_staff",
    "branches": "max_branches",
}


def get_active_subscription(organization):
    if organization is None:
        return None
    return getattr(organization, "subscription", None)


def get_limit_for(organization, resource):
    field = RESOURCE_FIELD[resource]
    org_limit = getattr(organization, field, None)
    subscription = get_active_subscription(organization)
    plan_limit = getattr(subscription.plan, field, None) if subscription else None

    limits = [limit for limit in (org_limit, plan_limit) if limit not in (None, 0)]
    if not limits:
        if plan_limit is None and subscription:
            return None  # unlimited on plan
        return org_limit
    return min(limits)


def seed_default_plans():
    defaults = [
        {
            "name": "Free",
            "code": SubscriptionPlan.Code.FREE,
            "max_members": 100,
            "max_books": 500,
            "max_staff": 5,
            "max_branches": 1,
            "monthly_price": 0,
        },
        {
            "name": "Starter",
            "code": SubscriptionPlan.Code.STARTER,
            "max_members": 1000,
            "max_books": 5000,
            "max_staff": 25,
            "max_branches": 3,
            "monthly_price": 1999,
        },
        {
            "name": "Professional",
            "code": SubscriptionPlan.Code.PROFESSIONAL,
            "max_members": 10000,
            "max_books": None,
            "max_staff": 100,
            "max_branches": 10,
            "monthly_price": 7999,
        },
        {
            "name": "Enterprise",
            "code": SubscriptionPlan.Code.ENTERPRISE,
            "max_members": None,
            "max_books": None,
            "max_staff": None,
            "max_branches": None,
            "monthly_price": 0,
        },
    ]
    for payload in defaults:
        SubscriptionPlan.objects.get_or_create(code=payload["code"], defaults=payload)
