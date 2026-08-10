from django.test import TestCase

from .models import Membership, Organization, User


class CoreModelTests(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword",
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, "testuser")

    def test_organization_creation(self):
        organization = Organization.objects.create(
            name="Test Organization",
        )

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(organization.name, "Test Organization")

    def test_membership_links_user_and_organization(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword",
        )
        organization = Organization.objects.create(
            name="Test Organization",
        )

        membership = Membership.objects.create(
            user=user,
            organization=organization,
        )

        self.assertEqual(membership.user, user)
        self.assertEqual(membership.organization, organization)

    def test_membership_role_persistence(self):
        user = User.objects.create_user(
            username="testuser",
            password="testpassword",
        )
        organization = Organization.objects.create(
            name="Test Organization",
        )

        membership = Membership.objects.create(
            user=user,
            organization=organization,
            role=Membership.Role.ADMIN,
        )

        membership.refresh_from_db()

        self.assertEqual(membership.role, Membership.Role.ADMIN)