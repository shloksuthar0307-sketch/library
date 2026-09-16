from django.contrib import admin
from .models import Category, Author, Publisher, Book

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_date')

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'nationality')

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number')

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn', 'author', 'category', 'status', 'available_copies')
    list_filter = ('status', 'category', 'author')
    search_fields = ('title', 'isbn')

from .models import DigitalAsset
admin.site.register(DigitalAsset)
