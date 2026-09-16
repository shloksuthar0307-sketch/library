import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from books.models import Book, BookCopy
from organizations.managers import TenantManager


class Transaction(models.Model):
    STATUS_CHOICES = (
        ("ISSUED", "Issued"),
        ("RETURNED", "Returned"),
        ("OVERDUE", "Overdue"),
        ("LOST", "Lost"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="transactions",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="transactions")
    book_copy = models.ForeignKey(
        BookCopy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_transactions",
    )
    returned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_returns",
    )
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ISSUED")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    fine_paid = models.BooleanField(default=False)

    objects = TenantManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.transaction_id}"


class Fine(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="fines",
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    def __str__(self):
        return f"Fine {self.amount} for {self.member}"

class DigitalLoan(models.Model):
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="digital_loans")
    asset = models.ForeignKey("books.DigitalAsset", on_delete=models.CASCADE, related_name="loans")
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="digital_loans")
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_revoked = models.BooleanField(default=False)

    objects = TenantManager()

    def __str__(self):
        return f"Digital Loan: {self.asset.book.title} to {self.member.username}"
