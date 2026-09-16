from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.settings_view, name='settings'),
    path('help/', views.help_center_view, name='help_center'),
    path('help/getting-started/', views.guide_getting_started, name='guide_getting_started'),
    path('help/borrowing-returns/', views.guide_borrowing_returns, name='guide_borrowing_returns'),
    path('help/fines-policies/', views.guide_fines_policies, name='guide_fines_policies'),
]
