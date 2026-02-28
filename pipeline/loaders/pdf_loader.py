from pathlib import Path
from pypdf import PdfReader
from pipeline.loaders.base import BaseLoader, DocumentChunk

class PDFLoader(BaseLoader):
    
    @staticmethod
    def supports(path: Path) -> bool:
        return path.suffix.lower() == ".pdf"
    
    def load(self, path: Path) -> list[DocumentChunk]:
        reader = PdfReader(str(path))
        chunks: list[DocumentChunk] = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text.strip():
                chunks.append(
                    DocumentChunk(
                        content=text,
                        metadata={"source": str(path.name), "page": i + 1},
                        page=i + 1
                    )
                )
        return chunks