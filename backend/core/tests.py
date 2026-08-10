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

    def test_organization_profile_optional_fields(self):
        org = Organization.objects.create(
            name="Test Org",
            legal_name="Legal Co",
            organization_type="Nonprofit",
            description="A description",
            website="https://example.com",
            contact_email="contact@example.com",
            phone="123-456-7890",
            address="123 Main St",
            city="Metropolis",
            state="NY",
            country="USA",
        )
        self.assertEqual(org.legal_name, "Legal Co")
        self.assertEqual(org.organization_type, "Nonprofit")
        self.assertEqual(org.description, "A description")
        self.assertEqual(org.website, "https://example.com")
        self.assertEqual(org.contact_email, "contact@example.com")
        self.assertEqual(org.phone, "123-456-7890")
        self.assertEqual(org.address, "123 Main St")
        self.assertEqual(org.city, "Metropolis")
        self.assertEqual(org.state, "NY")
        self.assertEqual(org.country, "USA")

    def test_organization_profile_update_and_timestamp(self):
        from django.utils import timezone
        org = Organization.objects.create(name="Org Update Test")
        created_at = org.created_at
        updated_at_initial = org.updated_at
        # Ensure initial timestamps are set
        self.assertIsNotNone(created_at)
        self.assertIsNotNone(updated_at_initial)
        # Wait a short time to ensure timestamp difference
        import time; time.sleep(1)
        org.legal_name = "New Legal"
        org.save()
        org.refresh_from_db()
        self.assertEqual(org.legal_name, "New Legal")
        # updated_at should have changed
        self.assertNotEqual(org.updated_at, updated_at_initial)
        self.assertTrue(org.updated_at > updated_at_initial)
