from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    character_count: int


class DocumentTextChunker:
    """Splits normalized text into deterministic character-based chunks."""

    def __init__(self, chunk_size: int = 1000) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[TextChunk]:
        if not text:
            return []

        return [
            TextChunk(
                index=index,
                text=text[start:start + self.chunk_size],
                character_count=len(
                    text[start:start + self.chunk_size]
                ),
            )
            for index, start in enumerate(
                range(0, len(text), self.chunk_size)
            )
        ]
