from celery import shared_task


@shared_task
def health_check_task():
    return "GROOT Celery is working"