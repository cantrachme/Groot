from django.core.management.base import BaseCommand, CommandError

from core.knowledge_tokens import issue_knowledge_token
from core.models import Membership


class Command(BaseCommand):
    help = "Issue a short-lived knowledge token for an existing membership."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--organization-id", type=int, required=True)
        parser.add_argument("--hours", type=int, default=24)

    def handle(self, *args, **options):
        try:
            membership = Membership.objects.select_related("user").get(
                user__username=options["username"],
                organization_id=options["organization_id"],
            )
            return issue_knowledge_token(membership, hours=options["hours"])
        except Membership.DoesNotExist as exc:
            raise CommandError("Membership not found.") from exc
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
