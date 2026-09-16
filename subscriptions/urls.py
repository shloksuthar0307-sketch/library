from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('billing/', views.billing_dashboard, name='dashboard'),
    path('billing/change-plan/', views.change_plan, name='change_plan'),
]
