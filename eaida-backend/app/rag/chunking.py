"""Text extraction + chunking for the knowledge base."""
from pathlib import Path


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(file_path).paragraphs)
    return Path(file_path).read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    words, chunks, start = text.split(), [], 0
    step = max(chunk_size - overlap, 1)
    while start < len(words):
        chunks.append(" ".join(words[start:start + chunk_size]))
        start += step
    return [c for c in chunks if c.strip()]