from pathlib import Path
from docx import Document

from pipeline.loaders.base import BaseLoader, DocumentChunk

class DocxLoader(BaseLoader):
    
    @staticmethod
    def supports(path: Path) -> bool:
        return path.suffix.lower() in (".docx")
    
    def load(self, path: Path) -> list[DocumentChunk]:
        doc = Document(str(path))
        chunks: list[DocumentChunk] = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text: 
                chunks.append(
                    DocumentChunk(
                        content=text,
                        metadata={"source": str(path.name)}
                    )
                )
        return chunks