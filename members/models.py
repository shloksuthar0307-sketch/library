from django.conf import settings
from django.db import models

from organizations.managers import TenantManager


class MemberProfile(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("SUSPENDED", "Suspended"),
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="member_profiles",
    )
    home_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    member_id = models.CharField(max_length=20)
    profile_image = models.ImageField(upload_to="members/profiles/", null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    membership_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    max_book_limit = models.PositiveIntegerField(default=3)

    objects = TenantManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "member_id"],
                name="uniq_member_id_per_organization",
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.member_id}"
