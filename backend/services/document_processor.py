import io
import hashlib
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import tempfile
import os


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )

    def process(self, content: bytes, filename: str, content_type: str) -> List[Dict[str, Any]]:
        if content_type == "application/pdf":
            text = self._extract_pdf(content, filename)
        elif content_type in ["text/plain", "text/markdown"]:
            text = content.decode("utf-8", errors="replace")
        elif "wordprocessingml" in content_type:
            text = self._extract_docx(content)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

        if not text.strip():
            raise ValueError("Document appears to be empty or unreadable")

        doc_id = hashlib.md5(content).hexdigest()[:16]
        raw_chunks = self.text_splitter.split_text(text)

        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk = {
                "id": f"{doc_id}-chunk-{i}",
                "text": chunk_text,
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(raw_chunks),
                    "content_type": content_type,
                    "char_count": len(chunk_text)
                }
            }
            chunks.append(chunk)
        return chunks

    def _extract_pdf(self, content: bytes, filename: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            full_text = "\n\n".join([
                f"[Page {page.metadata.get('page', i+1)}]\n{page.page_content}"
                for i, page in enumerate(pages)
            ])
            return full_text
        finally:
            os.unlink(tmp_path)

    def _extract_docx(self, content: bytes) -> str:
        from docx import Document
        doc = Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)
