from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ORG_ADMIN = "ORG_ADMIN", "Organization Admin"
        STAFF = "STAFF", "Staff"
        MEMBER = "MEMBER", "Member"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    phone_number = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to="users/profiles/", null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    can_access_all_branches = models.BooleanField(
        default=False,
        help_text="When enabled, staff may manage transactions across all branches in their organization.",
    )

    def is_superadmin(self):
        return self.is_superuser or self.role == self.Role.SUPER_ADMIN

    def is_org_admin(self):
        return self.is_superadmin() or self.role == self.Role.ORG_ADMIN

    def is_staff_member(self):
        return (
            self.is_superadmin()
            or self.is_org_admin()
            or self.role == self.Role.STAFF
            or self.is_staff
        )

    def is_member(self):
        return self.role == self.Role.MEMBER and not (self.is_superuser or self.is_staff)

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != self.Role.SUPER_ADMIN:
            self.role = self.Role.SUPER_ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
