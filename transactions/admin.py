from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'book', 'member', 'status', 'due_date', 'fine_amount')
    list_filter = ('status', 'fine_paid')

from .models import DigitalLoan
admin.site.register(DigitalLoan)
