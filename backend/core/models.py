from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user."""


class Organization(models.Model):
    # Optional profile fields
    legal_name = models.CharField(max_length=255, blank=True)
    organization_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(max_length=200, blank=True)
    contact_email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    # Timestamp fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    """Represents an organization."""

    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Links a user to an organization with a role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_user_organization",
            )
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.organization.name} ({self.role})"