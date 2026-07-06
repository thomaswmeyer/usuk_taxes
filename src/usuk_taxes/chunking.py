"""Split extracted text into overlapping chunks for indexing."""

from dataclasses import dataclass

from .config import CHUNK_OVERLAP, CHUNK_SIZE
from .manifest import Source


@dataclass
class Chunk:
    id: str
    source_id: str
    title: str
    jurisdiction: str
    seq: int
    text: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "jurisdiction": self.jurisdiction,
            "seq": self.seq,
            "text": self.text,
        }


def _split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n")]
    return [p for p in paras if p]


def chunk_source(source: Source, text: str) -> list[Chunk]:
    """Greedy paragraph packing up to CHUNK_SIZE chars, with tail overlap."""
    paras = _split_paragraphs(text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    size = 0

    def flush():
        nonlocal buf, size
        if not buf:
            return
        body = "\n\n".join(buf)
        chunks.append(
            Chunk(
                id=f"{source.id}#{len(chunks)}",
                source_id=source.id,
                title=source.title,
                jurisdiction=source.jurisdiction,
                seq=len(chunks),
                text=body,
            )
        )
        # Seed the next chunk with the tail of this one for continuity.
        tail = body[-CHUNK_OVERLAP:]
        buf = [tail]
        size = len(tail)

    for para in paras:
        # Hard-split paragraphs that alone exceed the chunk size (dense PDFs
        # often extract as one giant block).
        while len(para) > CHUNK_SIZE:
            head, para = para[:CHUNK_SIZE], para[CHUNK_SIZE - CHUNK_OVERLAP:]
            if size:
                flush()
            buf, size = [head], len(head)
            flush()
        if size + len(para) > CHUNK_SIZE:
            flush()
        buf.append(para)
        size += len(para)
    if buf and size > CHUNK_OVERLAP:
        flush()
    return chunks
