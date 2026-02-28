import uuid
from pathlib import Path

from qdrant_client.http import models

from app.core.config import settings
from app.services.embedding import embedding_service
from app.services.vectorstore import get_qdrant_client, ensure_collection
from app.workers.celery_app import celery_app

