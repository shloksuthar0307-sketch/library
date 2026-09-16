from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('issue/', views.issue_book, name='issue'),
    path('issue/bulk/', views.bulk_issue, name='bulk_issue'),
    path('issue/special/', views.special_reserve, name='special_reserve'),
    path('return/', views.return_book, name='return'),
    path('history/', views.transaction_history, name='history'),
    path('fines/', views.fine_list, name='fines'),
    path('fines/<int:pk>/paid/', views.mark_fine_paid, name='fine_paid'),
]
