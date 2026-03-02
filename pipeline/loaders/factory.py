from pathlib import Path

from pipeline.loaders.base import BaseLoader, DocumentChunk
from pipeline.loaders.ibmDocling import DoclingLoader

LOADERS: list[type[BaseLoader]] = [
    DoclingLoader
]

def load_document(path: str | Path) -> list[DocumentChunk]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    
    for loader_cls in LOADERS:
        if loader_cls.supports(path):
            loader = loader_cls()
            return loader.load(path)
    
    raise ValueError(
        f"Unsupported format: {path.suffix}. "
        f'Supported: ".pdf", ".docx", ".pptx", ".xlsx", ".md", ".html"'
    )