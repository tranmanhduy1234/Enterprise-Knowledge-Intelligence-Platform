from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel

class DocumentChunk(BaseModel):
    content: str
    metadata: dict = {}
    page: int | None = None
    
class BaseLoader(ABC):
    @abstractmethod
    def load(self, path: Path) -> list[DocumentChunk]:
        ...
    
    @staticmethod
    def supports(path: Path) -> bool:
        return False