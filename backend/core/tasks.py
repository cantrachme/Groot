from celery import shared_task

from .documents.tasks import embed_document, process_document
from .ingestion.tasks import ingest_integration

__all__ = ["embed_document", "health_check_task", "ingest_integration", "process_document"]


@shared_task
def health_check_task():
    return "GROOT Celery is working"
