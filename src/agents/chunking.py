from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    stripped_text: str = text.strip()
    if not stripped_text:
        return []

    if len(stripped_text) <= chunk_size:
        return [stripped_text]

    chunks: list[str] = []
    start_index: int = 0
    text_length: int = len(stripped_text)

    while start_index < text_length:
        end_index: int = min(start_index + chunk_size, text_length)
        chunk: str = stripped_text[start_index:end_index].strip()
        if chunk:
            chunks.append(chunk)
        if end_index >= text_length:
            break
        start_index = end_index - overlap

    return chunks
