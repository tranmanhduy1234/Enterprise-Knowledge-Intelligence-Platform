"""API route handler"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.core.cache import cache
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    IngestRequest, 
    IngestResponse,
    HealthResponse
)