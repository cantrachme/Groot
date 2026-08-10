import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_dev")

app = Celery("groot")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(["core"], force=True)