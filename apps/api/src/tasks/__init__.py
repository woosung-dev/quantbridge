"""Celery task package — celery_app re-export."""
from src.tasks.celery_app import celery_app

__all__ = ["celery_app"]
