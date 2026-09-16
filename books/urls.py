from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.book_list, name='list'),
    path('add/', views.book_create, name='add'),
    path('<int:pk>/', views.book_detail, name='detail'),
    path('<int:pk>/edit/', views.book_update, name='edit'),
    path('<int:pk>/delete/', views.book_delete, name='delete'),
    
    path('categories/', views.category_list, name='categories'),
    path('authors/', views.author_list, name='authors'),
    path('publishers/', views.publisher_list, name='publishers'),
    path('<int:pk>/borrow-digital/', views.borrow_digital, name='borrow_digital'),
    path('digital-asset/<uuid:token>/', views.serve_digital_asset, name='serve_digital_asset'),
]
