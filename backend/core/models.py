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

class Team(models.Model):
    """Represents a team within an organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_team_organization_name",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class TeamMembership(models.Model):
    """Links a user to a team with a team-level role."""

    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        MEMBER = "member", "Member"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    team = models.ForeignKey(
        Team,
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
                fields=["user", "team"],
                name="unique_user_team",
            )
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.team.name} ({self.role})"


class Customer(models.Model):
    """Represents a customer belonging to an organization."""

    class Status(models.TextChoices):
        PROSPECT = "prospect", "Prospect"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(max_length=254, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROSPECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_customer_organization_name",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class Project(models.Model):
    """Represents a project belonging to an organization."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_project_organization_name",
            )
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class Task(models.Model):
    """Represents a task within an organization project."""

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"
        BLOCKED = "blocked", "Blocked"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "title"],
                name="unique_task_project_title",
            )
        ]

    def __str__(self):
        return f"{self.project.name} / {self.title}"


class Event(models.Model):
    """Represents a normalized event within an organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    occurred_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "source", "external_id"],
                name="unique_event_external_identity",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "occurred_at"],
                name="event_org_occurred_idx",
            ),
            models.Index(
                fields=["organization", "event_type"],
                name="event_org_type_idx",
            ),
            models.Index(
                fields=["organization", "source", "external_id"],
                name="event_org_source_external_idx",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.event_type} / {self.title}"


class Risk(models.Model):
    """Represents a risk associated with an organization."""

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MITIGATED = "mitigated", "Mitigated"
        RESOLVED = "resolved", "Resolved"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="risks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    source = models.CharField(max_length=100, blank=True)
    identified_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "severity"],
                name="risk_org_severity_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="risk_org_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.title}"


class Document(models.Model):
    """Represents a document belonging to an organization."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        PROCESSING = "processing", "Processing"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100, blank=True)
    storage_key = models.CharField(max_length=500, unique=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="document_org_status_idx",
            ),
            models.Index(
                fields=["organization", "document_type"],
                name="document_org_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class Integration(models.Model):
    """Represents an external system integration for an organization."""

    class Provider(models.TextChoices):
        GITHUB = "github", "GitHub"
        JIRA = "jira", "Jira"
        SLACK = "slack", "Slack"
        CRM = "crm", "CRM"
        GOOGLE_DRIVE = "google_drive", "Google Drive"
        AWS = "aws", "AWS"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DISCONNECTED = "disconnected", "Disconnected"
        CONNECTING = "connecting", "Connecting"
        ACTIVE = "active", "Active"
        ERROR = "error", "Error"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DISCONNECTED,
    )
    external_account_id = models.CharField(
        max_length=255,
        blank=True,
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider", "name"],
                name="unique_integration_org_provider_name",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "provider"],
                name="integration_org_provider_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="integration_org_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"
