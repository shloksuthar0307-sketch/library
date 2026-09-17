from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('export/', views.export_report_view, name='export'),
    path('schedule/create/', views.create_scheduled_report_view, name='schedule_create'),
    path('schedule/<int:pk>/toggle/', views.toggle_scheduled_report_view, name='schedule_toggle'),
    path('schedule/<int:pk>/run/', views.run_scheduled_report_view, name='schedule_run'),
    path('schedule/<int:pk>/delete/', views.delete_scheduled_report_view, name='schedule_delete'),
    path('custom/preview/', views.custom_report_preview_view, name='custom_preview'),
]
