"""Celery application factory.

Workers: `celery -A conf worker -l info`
Beat:    `celery -A conf beat -l info`
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conf.settings.dev")

app = Celery("r_crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    print(f"Celery request: {self.request!r}")
