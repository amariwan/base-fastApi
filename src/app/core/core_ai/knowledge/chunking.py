"""Deterministic text chunking for knowledge ingestion."""


def chunk_text(text: str, *, chunk_size: int, overlap: int = 0) -> tuple[str, ...]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    cleaned = text.strip()
    if not cleaned:
        return ()
    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(cleaned), step):
        chunks.append(cleaned[start : start + chunk_size])
        if start + chunk_size >= len(cleaned):
            break
    return tuple(chunks)
