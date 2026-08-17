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


class IntegrationRegistryTests(TestCase):
    class FakeConnector:
        provider = "fake"

    def test_register_and_get_connector(self):
        from .integrations import IntegrationRegistry

        registry = IntegrationRegistry()
        connector = self.FakeConnector()

        registry.register(connector)

        self.assertTrue(registry.has("fake"))
        self.assertIs(registry.get("fake"), connector)
        self.assertEqual(registry.providers(), ("fake",))

    def test_duplicate_provider_is_rejected(self):
        from .integrations import IntegrationRegistry

        registry = IntegrationRegistry()
        registry.register(self.FakeConnector())

        with self.assertRaises(ValueError):
            registry.register(self.FakeConnector())

    def test_unknown_provider_is_rejected(self):
        from .integrations import IntegrationRegistry

        registry = IntegrationRegistry()

        with self.assertRaises(KeyError):
            registry.get("unknown")


class CredentialProviderTests(TestCase):
    def test_environment_provider_returns_credential(self):
        import os

        from .integrations import EnvironmentCredentialProvider

        os.environ["GROOT_TEST_TOKEN"] = "test-secret"

        try:
            provider = EnvironmentCredentialProvider()

            self.assertTrue(provider.has("GROOT_TEST_TOKEN"))
            self.assertEqual(
                provider.get("GROOT_TEST_TOKEN"),
                "test-secret",
            )
        finally:
            os.environ.pop("GROOT_TEST_TOKEN", None)

    def test_environment_provider_returns_none_for_missing_credential(self):
        import os

        from .integrations import EnvironmentCredentialProvider

        os.environ.pop("GROOT_MISSING_TOKEN", None)

        provider = EnvironmentCredentialProvider()

        self.assertFalse(provider.has("GROOT_MISSING_TOKEN"))
        self.assertIsNone(provider.get("GROOT_MISSING_TOKEN"))

    def test_environment_provider_ignores_empty_credentials(self):
        import os

        from .integrations import EnvironmentCredentialProvider

        os.environ["GROOT_EMPTY_TOKEN"] = "   "

        try:
            provider = EnvironmentCredentialProvider()

            self.assertFalse(provider.has("GROOT_EMPTY_TOKEN"))
            self.assertIsNone(provider.get("GROOT_EMPTY_TOKEN"))
        finally:
            os.environ.pop("GROOT_EMPTY_TOKEN", None)


class GitHubConnectorTests(TestCase):
    def test_empty_token_is_rejected(self):
        from .integrations.providers.github import GitHubConnector

        with self.assertRaises(ValueError):
            GitHubConnector("   ")

    def test_headers_use_bearer_authentication(self):
        from .integrations.providers.github import GitHubConnector

        connector = GitHubConnector("test-token")

        self.assertEqual(
            connector._headers()["Authorization"],
            "Bearer test-token",
        )
        self.assertEqual(
            connector._headers()["Accept"],
            "application/vnd.github+json",
        )

    def test_test_connection_success(self):
        from unittest.mock import Mock, patch

        from .integrations.providers.github import GitHubConnector

        response = Mock()
        response.ok = True
        response.json.return_value = {
            "login": "test-user",
        }

        connector = GitHubConnector("test-token")

        with patch(
            "core.integrations.providers.github.requests.get",
            return_value=response,
        ) as mock_get:
            result = connector.test_connection()

        self.assertTrue(result.success)
        self.assertEqual(result.data[0]["login"], "test-user")
        mock_get.assert_called_once()

    def test_test_connection_failure(self):
        from unittest.mock import Mock, patch

        from .integrations.providers.github import GitHubConnector

        response = Mock()
        response.ok = False
        response.status_code = 401

        connector = GitHubConnector("test-token")

        with patch(
            "core.integrations.providers.github.requests.get",
            return_value=response,
        ):
            result = connector.test_connection()

        self.assertFalse(result.success)
        self.assertIn("401", result.error)

    def test_disconnect_succeeds(self):
        from .integrations.providers.github import GitHubConnector

        result = GitHubConnector("test-token").disconnect()

        self.assertTrue(result.success)


class GitHubNormalizationTests(TestCase):
    def test_repository_is_normalized_to_event(self):
        from .integrations.providers.github import GitHubConnector

        connector = GitHubConnector("test-token")

        events = connector.normalize(
            [
                {
                    "id": 123,
                    "name": "groot",
                    "full_name": "cantrachme/Groot",
                    "description": "Operational intelligence platform",
                    "html_url": "https://github.com/cantrachme/Groot",
                    "private": True,
                    "default_branch": "main",
                    "owner": {"login": "cantrachme"},
                }
            ]
        )

        self.assertEqual(len(events), 1)

        event = events[0]

        self.assertEqual(event.event_type, "github_repository")
        self.assertEqual(event.title, "cantrachme/Groot")
        self.assertEqual(event.source, "github")
        self.assertEqual(
            event.metadata["repository_id"],
            123,
        )
        self.assertEqual(
            event.metadata["owner"],
            "cantrachme",
        )

    def test_invalid_github_item_is_skipped(self):
        from .integrations.providers.github import GitHubConnector

        connector = GitHubConnector("test-token")

        events = connector.normalize(
            [
                {"id": 123},
                {"name": "valid-repo"},
            ]
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "valid-repo")


class IntegrationServiceTests(TestCase):
    class FakeConnector:
        provider = "fake"

        def test_connection(self):
            from .integrations import ConnectorResult

            return ConnectorResult(
                success=True,
                data=[{"connected": True}],
            )

        def fetch(self, **kwargs):
            from .integrations import ConnectorResult

            return ConnectorResult(
                success=True,
                data=[{"name": "example"}],
            )

        def normalize(self, data):
            from .integrations import NormalizedEvent

            return [
                NormalizedEvent(
                    event_type="fake_event",
                    title=item["name"],
                    source="fake",
                )
                for item in data
            ]

    class FakeCredentials:
        def __init__(self, token="fake-token"):
            self.token = token

        def get(self, key):
            if key == "FAKE_TOKEN":
                return self.token
            return None

    def setUp(self):
        from .integrations import IntegrationRegistry, IntegrationService

        self.registry = IntegrationRegistry()
        self.connector = self.FakeConnector()
        self.registry.register(self.connector)

        self.service = IntegrationService(
            registry=self.registry,
            credentials=self.FakeCredentials(),
        )

    def test_get_connector(self):
        connector = self.service.get_connector("fake")

        self.assertIs(connector, self.connector)

    def test_test_connection_uses_registered_connector(self):
        result = self.service.test_connection(
            "fake",
            "FAKE_TOKEN",
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.data,
            [{"connected": True}],
        )

    def test_missing_credential_prevents_connection(self):
        from .integrations import IntegrationService

        service = IntegrationService(
            registry=self.registry,
            credentials=self.FakeCredentials(token=""),
        )

        result = service.test_connection(
            "fake",
            "FAKE_TOKEN",
        )

        self.assertFalse(result.success)
        self.assertIn("Credential not configured", result.error)

    def test_fetch_and_normalize(self):
        result, events = self.service.fetch_and_normalize(
            "fake",
            "FAKE_TOKEN",
        )

        self.assertTrue(result.success)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "fake_event")
        self.assertEqual(events[0].title, "example")
