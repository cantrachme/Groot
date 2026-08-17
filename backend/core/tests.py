from django.test import TestCase

from .models import Customer, Document, Event, Integration, Membership, Organization, Project, Risk, Team, TeamMembership, Task, User


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
        organization = Organization.objects.create(
            name="Org Update Test",
        )

        initial_updated_at = organization.updated_at

        organization.legal_name = "New Legal"
        organization.save()
        organization.refresh_from_db()

        self.assertEqual(organization.legal_name, "New Legal")
        self.assertGreaterEqual(organization.updated_at, initial_updated_at)


class CompanyDomainModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="domainuser",
            password="testpassword",
        )
        self.organization = Organization.objects.create(
            name="Domain Organization",
        )

    def test_team_and_team_membership(self):
        team = Team.objects.create(
            organization=self.organization,
            name="Engineering",
        )
        membership = TeamMembership.objects.create(
            user=self.user,
            team=team,
            role=TeamMembership.Role.LEAD,
        )

        self.assertEqual(team.organization, self.organization)
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.team, team)

    def test_customer_project_and_task(self):
        customer = Customer.objects.create(
            organization=self.organization,
            name="Acme",
        )
        project = Project.objects.create(
            organization=self.organization,
            name="Acme Platform",
        )
        task = Task.objects.create(
            organization=self.organization,
            project=project,
            title="Build API",
            assignee=self.user,
        )

        self.assertEqual(customer.organization, self.organization)
        self.assertEqual(project.organization, self.organization)
        self.assertEqual(task.project, project)
        self.assertEqual(task.assignee, self.user)

    def test_event_and_risk(self):
        from django.utils import timezone

        event = Event.objects.create(
            organization=self.organization,
            event_type="deployment",
            title="Production deployment",
            occurred_at=timezone.now(),
            metadata={"environment": "production"},
        )
        risk = Risk.objects.create(
            organization=self.organization,
            title="Deployment risk",
            identified_at=timezone.now(),
            severity=Risk.Severity.HIGH,
        )

        self.assertEqual(event.organization, self.organization)
        self.assertEqual(event.metadata["environment"], "production")
        self.assertEqual(risk.organization, self.organization)
        self.assertEqual(risk.severity, Risk.Severity.HIGH)

    def test_document_and_integration(self):
        document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            name="requirements.pdf",
            storage_key="documents/requirements.pdf",
        )
        integration = Integration.objects.create(
            organization=self.organization,
            provider=Integration.Provider.GITHUB,
            name="GitHub",
        )

        self.assertEqual(document.organization, self.organization)
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(integration.organization, self.organization)
        self.assertEqual(integration.provider, Integration.Provider.GITHUB)

    def test_company_data_is_organization_scoped(self):
        other_organization = Organization.objects.create(
            name="Other Organization",
        )

        Team.objects.create(
            organization=self.organization,
            name="Engineering",
        )
        Team.objects.create(
            organization=other_organization,
            name="Engineering",
        )

        self.assertEqual(
            self.organization.teams.count(),
            1,
        )
        self.assertEqual(
            other_organization.teams.count(),
            1,
        )
