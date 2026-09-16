from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('create/', views.create_reservation, name='create'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
]
