from django.conf import settings
from django.db import models

from books.models import Book
from organizations.managers import TenantManager


class Reservation(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("WAITING", "Waiting"),
        ("AVAILABLE", "Available"),
        ("APPROVED", "Approved"),
        ("COLLECTED", "Collected"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
        ("COMPLETED", "Completed"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reservations",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reservations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    queue_position = models.PositiveIntegerField(default=1)
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Reservation: {self.book.title} by {self.member.username}"
