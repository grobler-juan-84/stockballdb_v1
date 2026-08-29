"""Deterministic FRED/ALFRED paginated response concatenation (full_concat_v1)."""

from __future__ import annotations

PAGE_BOUNDARY = b"---STOCKBALLDB_PAGE_BOUNDARY---\n"


def concat_pages(pages: list[tuple[int, bytes]]) -> bytes:
    """Concatenate paginated HTTP response bodies in ascending offset order."""
    if not pages:
        return b""
    parts: list[bytes] = []
    for offset, body in sorted(pages, key=lambda x: x[0]):
        parts.append(PAGE_BOUNDARY)
        parts.append(f"offset={offset}\n".encode("ascii"))
        parts.append(body)
    return b"".join(parts)


def split_pages(data: bytes) -> list[tuple[int, bytes]]:
    """Split a full_concat_v1 payload into (offset, body) pairs."""
    if not data:
        return []
    chunks = data.split(PAGE_BOUNDARY)
    pages: list[tuple[int, bytes]] = []
    for chunk in chunks:
        chunk = chunk.lstrip(b"\n")
        if not chunk:
            continue
        header, _, body = chunk.partition(b"\n")
        if not header.startswith(b"offset="):
            raise ValueError("invalid full_concat_v1 page header")
        offset = int(header.decode("ascii").split("=", 1)[1])
        pages.append((offset, body))
    return pages
