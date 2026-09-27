"""Issue opaque knowledge credentials for an existing active membership."""

import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone

from .models import KnowledgeAccessToken, Membership


def issue_knowledge_token(membership: Membership, *, hours: int = 24) -> str:
    if not 1 <= hours <= 168:
        raise ValueError("Token lifetime must be between 1 and 168 hours.")
    if not membership.user.is_active:
        raise ValueError("An active user is required.")
    raw = secrets.token_urlsafe(32)
    KnowledgeAccessToken.objects.create(
        digest=hashlib.sha256(raw.encode()).hexdigest(),
        membership=membership,
        expires_at=timezone.now() + timedelta(hours=hours),
    )
    return raw
