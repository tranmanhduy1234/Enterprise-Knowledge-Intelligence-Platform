from pipeline.loaders.base import DocumentChunk

class RecursiveCharaterChunker:
    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, separators: list[str] | None = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        
    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []
        
        sep = self.separators[0]
        splits = text.split(sep) if sep else list(text)
        
        if len(splits) < 2:
            return self._split_text_with_next_sep(text)
        
        final_chunks: list[str] = []
        current_doc: list[str] = []
        current_length = 0
        
        for i, s in enumerate(splits):
            part = s + sep if (sep and i < len(splits) - 1) else s
            if not part: continue
            
            part_len = len(part)
            
            if part_len > self.chunk_size:
                if current_doc:
                    final_chunks.append("".join(current_doc).strip())
                    current_doc = []
                    current_length = 0
                
                sub_chunks = self._split_text_with_next_sep(part)
                final_chunks.extend(sub_chunks)
                continue

            if current_length + part_len > self.chunk_size:
                if current_doc:
                    final_chunks.append("".join(current_doc).strip())
                
                overlap_doc = []
                overlap_len = 0
                for prev_part in reversed(current_doc):
                    if overlap_len + len(prev_part) <= self.chunk_overlap:
                        overlap_doc.insert(0, prev_part)
                        overlap_len += len(prev_part)
                    else:
                        break
                current_doc = overlap_doc
                current_length = overlap_len
            
            current_doc.append(part)
            current_length += part_len

        if current_doc:
            res = "".join(current_doc).strip()
            if res: final_chunks.append(res)
                
        return final_chunks
        
    def _split_text_with_next_sep(self, text: str) -> list[str]:
        if len(self.separators) <= 1:
            return self._split_fixed(text)
        next_chunker = RecursiveCharaterChunker(
            self.chunk_size,
            self.chunk_overlap,
            self.separators[1:]
        )
        return next_chunker._split_text(text)
    
    def _split_fixed(self, text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        return chunks
        
    def chunk(self, doc: DocumentChunk) -> list[DocumentChunk]:
        texts = self._split_text(doc.content)
        return [
            DocumentChunk(
                content=t,
                metadata=doc.metadata.copy(),
                page=doc.page
            )
            for t in texts
        ]
        
if __name__=="__main__":
    from pathlib import Path
    from pipeline.loaders.factory import load_document

    def run_pipeline(file_path: str):
        print(f"--- Đang xử lý: {file_path} ---")
        try:
            initial_chunks = load_document(file_path)
            print(f"Số lượng đoạn lớn sau khi load: {len(initial_chunks)}")
        except Exception as e:
            print(f"Lỗi khi load tài liệu: {e}")
            return
        chunker = RecursiveCharaterChunker(chunk_size=2000, chunk_overlap=64)
        
        final_documents = []
        for big_chunk in initial_chunks:
            sub_chunks = chunker.chunk(big_chunk)
            final_documents.extend(sub_chunks)

        print(final_documents)
        exit(0)
        print(f"Số lượng mảnh (chunks) cuối cùng: {len(final_documents)}")
        
        for i, doc in enumerate(final_documents):
            print(f"\n--- Mảnh #{i+1} (Độ dài: {len(doc.content)}) ---")
            print(f"Metadata: {doc.metadata}")
            print(f"Nội dung: {doc.content}...")

    test_file = "D:\chuyen_nganh\myEKIP\data\AI-engineer.pdf" 
    
    if not Path(test_file).exists():
        Path("test_md.md").write_text("# Tiêu đề 1\nNội dung rất dài..." * 50, encoding="utf-8")
        test_file = "test_md.md"

    run_pipeline(test_file)