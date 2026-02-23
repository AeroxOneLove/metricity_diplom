import os

from celery import Celery
from django.conf import settings

# Ensure Django settings are available to Celery workers
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.project.settings")

app = Celery("core")

# Read CELERY_* settings from Django settings (env-driven)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks.py in installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Keep timezones consistent
app.conf.timezone = settings.TIME_ZONE


@app.task
def ping():
    return "pong"
