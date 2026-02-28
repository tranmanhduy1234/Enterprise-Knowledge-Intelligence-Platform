from pathlib import Path
from pipeline.loaders.base import BaseLoader, DocumentChunk

class MarkdownLoader(BaseLoader):
    
    @staticmethod
    def supports(path: Path) -> bool:
        return path.suffix.lower() in (".md", ".markdown")
    
    def load(self, path: Path) -> list[DocumentChunk]:
        text = path.read_text(encoding="utf-8")
        return [
            DocumentChunk(
                content=text,
                metadata={"source": str(path.name)}
            )
        ]