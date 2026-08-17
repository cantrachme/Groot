from django.test import TestCase

from .models import Customer, Document, DocumentChunk, DocumentContent, Event, Integration, Membership, Organization, Project, Risk, Team, TeamMembership, Task, User


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


class IngestionServiceTests(TestCase):
    class FakeIntegrationService:
        def __init__(self, success=True):
            self.success = success

        def fetch_and_normalize(self, provider, credential_key, **kwargs):
            from .integrations import ConnectorResult, NormalizedEvent

            if not self.success:
                return (
                    ConnectorResult(
                        success=False,
                        error="Integration failed",
                    ),
                    [],
                )

            return (
                ConnectorResult(
                    success=True,
                    data=[{"name": "example"}],
                ),
                [
                    NormalizedEvent(
                        event_type="fake_event",
                        title="example",
                        source=provider,
                    )
                ],
            )

    def test_ingest_returns_normalized_events(self):
        from .ingestion import IngestionService

        service = IngestionService(
            self.FakeIntegrationService(),
        )

        result = service.ingest(
            "fake",
            "FAKE_TOKEN",
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.events), 1)
        self.assertEqual(
            result.events[0].event_type,
            "fake_event",
        )
        self.assertEqual(
            result.events[0].title,
            "example",
        )

    def test_ingest_propagates_integration_failure(self):
        from .ingestion import IngestionService

        service = IngestionService(
            self.FakeIntegrationService(success=False),
        )

        result = service.ingest(
            "fake",
            "FAKE_TOKEN",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.events, [])
        self.assertEqual(result.error, "Integration failed")

    def test_ingest_passes_arguments_to_integration_service(self):
        from unittest.mock import Mock

        from .ingestion import IngestionService
        from .integrations import ConnectorResult, NormalizedEvent

        integration_service = Mock()

        integration_service.fetch_and_normalize.return_value = (
            ConnectorResult(success=True),
            [
                NormalizedEvent(
                    event_type="repository",
                    title="GROOT",
                )
            ],
        )

        service = IngestionService(integration_service)

        service.ingest(
            "github",
            "GITHUB_TOKEN",
            endpoint="/user/repos",
        )

        integration_service.fetch_and_normalize.assert_called_once_with(
            "github",
            "GITHUB_TOKEN",
            endpoint="/user/repos",
        )


class IngestionTaskTests(TestCase):
    def test_ingestion_task_returns_failure_for_missing_credential(self):
        import os

        from .ingestion.tasks import ingest_integration

        organization = Organization.objects.create(
            name="Task Test Organization",
        )

        os.environ.pop("GITHUB_TOKEN", None)

        result = ingest_integration.apply(
            args=[
                "github",
                "GITHUB_TOKEN",
                organization.id,
            ],
        ).get()

        self.assertFalse(result["success"])
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["persisted_count"], 0)
        self.assertEqual(
            result["error"],
            "Credential not configured: GITHUB_TOKEN",
        )


class EventPersistenceServiceTests(TestCase):
    def setUp(self):
        from .ingestion import EventPersistenceService

        self.organization = Organization.objects.create(
            name="Persistence Organization",
        )
        self.service = EventPersistenceService()

    def test_persist_creates_event(self):
        from .integrations import NormalizedEvent

        from django.utils import timezone

        occurred_at = timezone.now()

        normalized_event = NormalizedEvent(
            event_type="github_repository",
            title="cantrachme/Groot",
            description="GROOT repository",
            source="github",
            occurred_at=occurred_at,
            metadata={
                "repository_id": 123,
            },
        )

        event = self.service.persist(
            self.organization,
            normalized_event,
        )

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(event.organization, self.organization)
        self.assertEqual(event.event_type, "github_repository")
        self.assertEqual(event.title, "cantrachme/Groot")
        self.assertEqual(event.description, "GROOT repository")
        self.assertEqual(event.source, "github")
        self.assertEqual(event.occurred_at, occurred_at)
        self.assertEqual(
            event.metadata["repository_id"],
            123,
        )

    def test_persist_uses_current_time_when_occurred_at_is_missing(self):
        from django.utils import timezone

        from .integrations import NormalizedEvent

        before = timezone.now()

        event = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="github_repository",
                title="GROOT",
                source="github",
            ),
        )

        after = timezone.now()

        self.assertIsNotNone(event.occurred_at)
        self.assertGreaterEqual(event.occurred_at, before)
        self.assertLessEqual(event.occurred_at, after)

    def test_persist_preserves_organization(self):
        from .integrations import NormalizedEvent

        event = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="repository",
                title="GROOT",
            ),
        )

        self.assertEqual(
            Event.objects.get(pk=event.pk).organization,
            self.organization,
        )

    def test_persist_many_creates_all_events(self):
        from .integrations import NormalizedEvent

        events = self.service.persist_many(
            self.organization,
            [
                NormalizedEvent(
                    event_type="repository",
                    title="Repository A",
                ),
                NormalizedEvent(
                    event_type="repository",
                    title="Repository B",
                ),
                NormalizedEvent(
                    event_type="repository",
                    title="Repository C",
                ),
            ],
        )

        self.assertEqual(len(events), 3)
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(
            list(
                Event.objects.values_list(
                    "title",
                    flat=True,
                )
            ),
            [
                "Repository A",
                "Repository B",
                "Repository C",
            ],
        )

    def test_persist_many_keeps_all_events_in_same_organization(self):
        from .integrations import NormalizedEvent

        events = self.service.persist_many(
            self.organization,
            [
                NormalizedEvent(
                    event_type="event_a",
                    title="Event A",
                ),
                NormalizedEvent(
                    event_type="event_b",
                    title="Event B",
                ),
            ],
        )

        self.assertTrue(
            all(
                event.organization_id
                == self.organization.id
                for event in events
            )
        )


class EventIdempotencyTests(TestCase):
    def setUp(self):
        from .ingestion import EventPersistenceService

        self.organization = Organization.objects.create(
            name="Idempotency Organization",
        )
        self.service = EventPersistenceService()

    def test_same_external_event_is_not_duplicated(self):
        from .integrations import NormalizedEvent

        normalized_event = NormalizedEvent(
            event_type="github_repository",
            title="GROOT",
            source="github",
            external_id="repository:123",
            metadata={"stars": 10},
        )

        first = self.service.persist(
            self.organization,
            normalized_event,
        )
        second = self.service.persist(
            self.organization,
            normalized_event,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Event.objects.count(), 1)

    def test_same_external_identity_updates_existing_event(self):
        from .integrations import NormalizedEvent

        first = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="github_repository",
                title="GROOT",
                source="github",
                external_id="repository:123",
                metadata={"stars": 10},
            ),
        )

        second = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="github_repository",
                title="GROOT",
                source="github",
                external_id="repository:123",
                metadata={"stars": 25},
            ),
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Event.objects.count(), 1)

        refreshed = Event.objects.get(pk=first.pk)

        self.assertEqual(
            refreshed.metadata["stars"],
            25,
        )

    def test_same_external_id_can_exist_for_different_organizations(self):
        from .integrations import NormalizedEvent

        other_organization = Organization.objects.create(
            name="Other Idempotency Organization",
        )

        event_a = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="github_repository",
                title="GROOT",
                source="github",
                external_id="repository:123",
            ),
        )

        event_b = self.service.persist(
            other_organization,
            NormalizedEvent(
                event_type="github_repository",
                title="GROOT",
                source="github",
                external_id="repository:123",
            ),
        )

        self.assertNotEqual(event_a.pk, event_b.pk)
        self.assertEqual(Event.objects.count(), 2)

    def test_events_without_external_id_are_not_forced_to_be_unique(self):
        from .integrations import NormalizedEvent

        event_a = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="manual",
                title="Same event",
                source="manual",
            ),
        )

        event_b = self.service.persist(
            self.organization,
            NormalizedEvent(
                event_type="manual",
                title="Same event",
                source="manual",
            ),
        )

        self.assertNotEqual(event_a.pk, event_b.pk)
        self.assertEqual(Event.objects.count(), 2)


class GitHubIntegrationEventTests(TestCase):
    def test_github_repository_normalizes_external_id(self):
        from core.integrations.providers.github import GitHubConnector

        connector = GitHubConnector("test-token")

        events = connector.normalize(
            [
                {
                    "id": 12345,
                    "full_name": "cantrachme/Groot",
                    "name": "Groot",
                    "description": "GROOT project",
                    "owner": {
                        "login": "cantrachme",
                    },
                    "html_url": "https://github.com/cantrachme/Groot",
                    "private": False,
                    "default_branch": "main",
                }
            ]
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0].external_id,
            "repository:12345",
        )
        self.assertEqual(
            events[0].source,
            "github",
        )
        self.assertEqual(
            events[0].event_type,
            "github_repository",
        )

    def test_github_repository_without_id_has_no_external_id(self):
        from core.integrations.providers.github import GitHubConnector

        connector = GitHubConnector("test-token")

        events = connector.normalize(
            [
                {
                    "full_name": "cantrachme/Groot",
                    "name": "Groot",
                }
            ]
        )

        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0].external_id)


class GitHubEventPersistenceTests(TestCase):
    def test_github_events_persist_with_external_identity(self):
        from core.ingestion import EventPersistenceService
        from core.integrations.providers.github import GitHubConnector

        organization = Organization.objects.create(
            name="GitHub Persistence Organization",
        )

        connector = GitHubConnector("test-token")

        normalized_events = connector.normalize(
            [
                {
                    "id": 98765,
                    "full_name": "cantrachme/Groot",
                    "name": "Groot",
                    "description": "GROOT project",
                    "owner": {"login": "cantrachme"},
                    "html_url": "https://github.com/cantrachme/Groot",
                    "private": False,
                    "default_branch": "main",
                }
            ]
        )

        service = EventPersistenceService()

        events = service.persist_many(
            organization,
            normalized_events,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(
            events[0].external_id,
            "repository:98765",
        )
        self.assertEqual(
            events[0].source,
            "github",
        )

    def test_repeated_github_ingestion_does_not_duplicate_repository(self):
        from core.ingestion import EventPersistenceService
        from core.integrations.providers.github import GitHubConnector

        organization = Organization.objects.create(
            name="GitHub Idempotency Organization",
        )

        connector = GitHubConnector("test-token")

        payload = [
            {
                "id": 55555,
                "full_name": "cantrachme/Groot",
                "name": "Groot",
                "description": "GROOT project",
                "owner": {"login": "cantrachme"},
                "html_url": "https://github.com/cantrachme/Groot",
                "private": False,
                "default_branch": "main",
            }
        ]

        normalized_events = connector.normalize(payload)

        service = EventPersistenceService()

        first = service.persist_many(
            organization,
            normalized_events,
        )

        second = service.persist_many(
            organization,
            connector.normalize(payload),
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].pk, second[0].pk)
        self.assertEqual(Event.objects.count(), 1)


class GitHubIngestionTaskTests(TestCase):
    def test_ingestion_task_persists_github_events(self):
        from unittest.mock import patch

        organization = Organization.objects.create(
            name="Celery GitHub Organization",
        )

        github_payload = [
            {
                "id": 77777,
                "full_name": "cantrachme/Groot",
                "name": "Groot",
                "description": "GROOT project",
                "owner": {"login": "cantrachme"},
                "html_url": "https://github.com/cantrachme/Groot",
                "private": False,
                "default_branch": "main",
            }
        ]

        with patch.dict(
            "os.environ",
            {"GITHUB_TOKEN": "test-token"},
        ), patch(
            "core.integrations.providers.github.GitHubConnector.fetch",
            return_value=(
                type(
                    "ConnectorResult",
                    (),
                    {
                        "success": True,
                        "data": github_payload,
                        "error": None,
                    },
                )()
            ),
        ):
            from core.ingestion.tasks import ingest_integration

            result = ingest_integration.apply(
                args=[
                    "github",
                    "GITHUB_TOKEN",
                    organization.id,
                ],
            ).get()

        self.assertTrue(result["success"])
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["persisted_count"], 1)
        self.assertIsNone(result["error"])

        event = Event.objects.get(
            organization=organization,
        )

        self.assertEqual(
            event.external_id,
            "repository:77777",
        )
        self.assertEqual(
            event.source,
            "github",
        )
        self.assertEqual(
            event.title,
            "cantrachme/Groot",
        )


class IngestionTaskFailureTests(TestCase):
    def test_missing_organization_returns_failure(self):
        from .ingestion.tasks import ingest_integration

        result = ingest_integration.apply(
            args=[
                "github",
                "GITHUB_TOKEN",
                999999,
            ],
        ).get()

        self.assertFalse(result["success"])
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["persisted_count"], 0)
        self.assertEqual(
            result["error"],
            "Organization not found: 999999",
        )

    def test_unregistered_provider_returns_failure(self):
        from unittest.mock import patch

        from .ingestion.tasks import ingest_integration

        organization = Organization.objects.create(
            name="Unregistered Provider Organization",
        )

        with patch.dict(
            "os.environ",
            {"FAKE_TOKEN": "test-token"},
            clear=False,
        ):
            result = ingest_integration.apply(
                args=[
                    "unknown_provider",
                    "FAKE_TOKEN",
                    organization.id,
                ],
            ).get()

        self.assertFalse(result["success"])
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["persisted_count"], 0)
        self.assertEqual(
            result["error"],
            "Integration provider not registered: unknown_provider",
        )


class IntegrationNormalizationFailureTests(TestCase):
    def test_normalization_failure_returns_controlled_result(self):
        from unittest.mock import Mock

        from .ingestion import IngestionService
        from .integrations import ConnectorResult

        integration_service = Mock()
        integration_service.fetch_and_normalize.return_value = (
            ConnectorResult(
                success=False,
                error=(
                    "Failed to normalize github data: "
                    "invalid repository payload"
                ),
            ),
            [],
        )

        service = IngestionService(integration_service)

        result = service.ingest(
            "github",
            "GITHUB_TOKEN",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.events, [])
        self.assertEqual(
            result.error,
            "Failed to normalize github data: invalid repository payload",
        )


class DocumentIntelligenceModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Document Intelligence Organization",
        )
        self.user = User.objects.create_user(
            username="document-intelligence-user",
            password="testpassword",
        )
        self.document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            name="requirements.pdf",
            document_type="pdf",
            storage_key="documents/requirements.pdf",
            mime_type="application/pdf",
            size=1024,
        )

    def test_document_content_persists_extracted_text(self):
        from django.utils import timezone

        content = DocumentContent.objects.create(
            document=self.document,
            text="GROOT document intelligence content.",
            status=DocumentContent.Status.READY,
            extractor="text",
            extracted_at=timezone.now(),
        )

        self.assertEqual(content.document, self.document)
        self.assertEqual(
            content.text,
            "GROOT document intelligence content.",
        )
        self.assertEqual(
            content.status,
            DocumentContent.Status.READY,
        )
        self.assertEqual(content.extractor, "text")
        self.assertIsNotNone(content.extracted_at)
        self.assertEqual(self.document.content, content)

    def test_document_chunk_persists_order_and_metadata(self):
        chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=0,
            text="First document chunk.",
            character_count=21,
            metadata={
                "page": 1,
                "section": "Introduction",
            },
        )

        self.assertEqual(chunk.document, self.document)
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(
            chunk.text,
            "First document chunk.",
        )
        self.assertEqual(chunk.character_count, 21)
        self.assertEqual(
            chunk.metadata["page"],
            1,
        )
        self.assertEqual(
            chunk.metadata["section"],
            "Introduction",
        )

    def test_document_chunk_index_is_unique_per_document(self):
        from django.db import IntegrityError

        DocumentChunk.objects.create(
            document=self.document,
            chunk_index=0,
            text="First chunk.",
        )

        with self.assertRaises(IntegrityError):
            DocumentChunk.objects.create(
                document=self.document,
                chunk_index=0,
                text="Duplicate chunk.",
            )

    def test_same_chunk_index_is_allowed_for_different_documents(self):
        second_document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            name="architecture.pdf",
            document_type="pdf",
            storage_key="documents/architecture.pdf",
            mime_type="application/pdf",
            size=2048,
        )

        first_chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=0,
            text="First document.",
        )

        second_chunk = DocumentChunk.objects.create(
            document=second_document,
            chunk_index=0,
            text="Second document.",
        )

        self.assertEqual(first_chunk.chunk_index, 0)
        self.assertEqual(second_chunk.chunk_index, 0)
        self.assertNotEqual(
            first_chunk.document,
            second_chunk.document,
        )


class DocumentExtractorTests(TestCase):
    def test_plain_text_extractor_extracts_utf8_text(self):
        from .documents import PlainTextExtractor

        extractor = PlainTextExtractor()

        text = extractor.extract(
            "GROOT document intelligence".encode("utf-8")
        )

        self.assertEqual(
            text,
            "GROOT document intelligence",
        )

    def test_plain_text_extractor_supports_expected_mime_types(self):
        from .documents import PlainTextExtractor

        extractor = PlainTextExtractor()

        self.assertEqual(
            extractor.supported_mime_types,
            (
                "text/plain",
                "text/markdown",
                "text/csv",
            ),
        )

    def test_plain_text_extractor_name_is_stable(self):
        from .documents import PlainTextExtractor

        self.assertEqual(
            PlainTextExtractor.name,
            "plain_text",
        )

    def test_plain_text_extractor_rejects_invalid_utf8(self):
        from .documents import PlainTextExtractor

        extractor = PlainTextExtractor()

        with self.assertRaises(UnicodeDecodeError):
            extractor.extract(b"invalid-\xff-utf8")


class DocumentProcessingServiceTests(TestCase):
    def setUp(self):
        from .documents import (
            DocumentExtractorRegistry,
            DocumentProcessingService,
            PlainTextExtractor,
        )

        self.organization = Organization.objects.create(
            name="Processing Organization",
        )
        self.user = User.objects.create_user(
            username="processing-user",
            password="testpassword",
        )
        self.document = Document.objects.create(
            organization=self.organization,
            uploaded_by=self.user,
            name="notes.txt",
            document_type="text",
            storage_key="documents/notes.txt",
            mime_type="text/plain",
            size=32,
        )

        registry = DocumentExtractorRegistry(
            [PlainTextExtractor()],
        )
        self.service = DocumentProcessingService(registry)

    def test_process_creates_ready_document_content(self):
        content = self.service.process(
            self.document,
            b"GROOT processing content.",
        )

        self.assertEqual(
            content.status,
            DocumentContent.Status.READY,
        )
        self.assertEqual(
            content.text,
            "GROOT processing content.",
        )
        self.assertEqual(
            content.extractor,
            "plain_text",
        )
        self.assertEqual(content.error, "")
        self.assertIsNotNone(content.extracted_at)

    def test_process_updates_existing_document_content(self):
        existing = DocumentContent.objects.create(
            document=self.document,
            text="old content",
            status=DocumentContent.Status.FAILED,
            error="previous error",
        )

        content = self.service.process(
            self.document,
            b"new content",
        )

        self.assertEqual(content.pk, existing.pk)
        self.assertEqual(content.text, "new content")
        self.assertEqual(
            content.status,
            DocumentContent.Status.READY,
        )
        self.assertEqual(content.error, "")

    def test_process_marks_content_failed_for_unsupported_mime_type(self):
        self.document.mime_type = "application/unknown"
        self.document.save(update_fields=["mime_type"])

        content = self.service.process(
            self.document,
            b"unsupported",
        )

        self.assertEqual(
            content.status,
            DocumentContent.Status.FAILED,
        )
        self.assertIn(
            "No document extractor registered",
            content.error,
        )
        self.assertEqual(content.text, "")
        self.assertIsNone(content.extracted_at)

    def test_process_marks_content_failed_for_invalid_text(self):
        content = self.service.process(
            self.document,
            b"invalid-\xff-utf8",
        )

        self.assertEqual(
            content.status,
            DocumentContent.Status.FAILED,
        )
        self.assertIn(
            "utf-8",
            content.error.lower(),
        )
        self.assertEqual(content.text, "")


class DocumentTextNormalizerTests(TestCase):
    def test_normalizer_normalizes_line_endings_and_whitespace(self):
        from .documents import DocumentTextNormalizer

        normalizer = DocumentTextNormalizer()

        result = normalizer.normalize(
            "  GROOT   document  \r\n"
            "\tintelligence\tplatform  \r"
            "\n\n"
        )

        self.assertEqual(
            result,
            "GROOT document\nintelligence platform",
        )

    def test_normalizer_removes_empty_boundary_lines(self):
        from .documents import DocumentTextNormalizer

        normalizer = DocumentTextNormalizer()

        result = normalizer.normalize(
            "\n\n  First line  \n\nSecond line\n\n"
        )

        self.assertEqual(
            result,
            "First line\nSecond line",
        )

    def test_normalizer_removes_null_characters(self):
        from .documents import DocumentTextNormalizer

        normalizer = DocumentTextNormalizer()

        result = normalizer.normalize(
            "GROOT\x00 document\x00 intelligence"
        )

        self.assertEqual(
            result,
            "GROOT document intelligence",
        )

    def test_normalizer_returns_empty_string_for_empty_input(self):
        from .documents import DocumentTextNormalizer

        normalizer = DocumentTextNormalizer()

        self.assertEqual(
            normalizer.normalize(""),
            "",
        )

    def test_normalizer_preserves_meaningful_line_boundaries(self):
        from .documents import DocumentTextNormalizer

        normalizer = DocumentTextNormalizer()

        result = normalizer.normalize(
            "Company Overview\n"
            "Revenue increased by 25%.\n"
            "Risk: customer concentration."
        )

        self.assertEqual(
            result,
            "Company Overview\n"
            "Revenue increased by 25%.\n"
            "Risk: customer concentration.",
        )
