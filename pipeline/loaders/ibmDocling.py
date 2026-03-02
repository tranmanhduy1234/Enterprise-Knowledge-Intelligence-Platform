from pathlib import Path
from typing import List

from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from pipeline.loaders.base import BaseLoader, DocumentChunk

class DoclingLoader(BaseLoader):
    def __init__(self):
        self.converter = DocumentConverter()
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4")
        ]
        
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False 
        )
    def load(self, path: Path) -> List[DocumentChunk]:
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file tại: {path}")
        if path.suffix.lower() == ".md":
            markdown_content = path.read_text(encoding="utf-8")
        else:
            result = self.converter.convert(str(path))
            markdown_content = result.document.export_to_markdown()
        md_header_splits = self.splitter.split_text(markdown_content)
        return [
            DocumentChunk(
                content=doc.page_content.strip(),
                metadata={
                    **doc.metadata,
                    "source": path.name,
                    "extension": path.suffix
                },
                page=None
            )
            for doc in md_header_splits
        ]
    @staticmethod
    def supports(path: Path) -> bool:
        supported_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".md", ".html"}
        return path.suffix.lower() in supported_extensions

if __name__ == "__main__":
    loader = DoclingLoader()
    file_path = Path(r"D:\chuyen_nganh\myEKIP\data\DANHSACHCHUADONGTIEN.xlsx")
    if loader.supports(file_path):
        final_chunks = loader.load(file_path)
        print(f"Tổng số lượng chunk: {len(final_chunks)}")
        print("-" * 50)
        for idx, chunk in enumerate(final_chunks[:5]):
            current_header = next(iter(chunk.metadata.values()), "No Header")
            print(f"[{idx}] {current_header}")
            print(f"    Length: {len(chunk.content)} characters")
            print(f"    Snippet: {chunk.content}...")
            print("-" * 30)