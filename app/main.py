from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.cache import cache
from app.api.routes import router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.disconnect()
    
app = FastAPI(
    title=settings.app_name,
    description="Enterprise Knowledge Intelligence Platform",   
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)