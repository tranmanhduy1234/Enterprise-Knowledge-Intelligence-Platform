from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

class DocumentChunk(BaseModel):
    """Single chunk of document content"""
    content: str
    metadata: dict = {}
    page: int | None = None
    
class BaseLoader(ABC):
    """Abstract base for document loaders"""
    @abstractmethod
    def load(self, path: Path) -> list[DocumentChunk]:
        ...
    
    @staticmethod
    def supports(path: Path) -> bool:
        return False