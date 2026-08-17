from dataclasses import dataclass

from .similarity_search_service import SimilaritySearchResult


@dataclass(frozen=True)
class ContextItem:
    document_chunk_id: int
    text: str
    similarity: float


@dataclass(frozen=True)
class AssembledContext:
    items: tuple[ContextItem, ...]
    text: str


class ContextAssemblyService:
    """Builds a bounded LLM context from retrieved document chunks."""

    def __init__(self, max_characters: int = 12000) -> None:
        if max_characters <= 0:
            raise ValueError(
                "max_characters must be greater than zero."
            )

        self.max_characters = max_characters

    def assemble(
        self,
        results: list[SimilaritySearchResult],
        chunk_texts: dict[int, str],
    ) -> AssembledContext:
        items: list[ContextItem] = []
        context_parts: list[str] = []
        current_length = 0

        for result in results:
            chunk_id = result.embedding.document_chunk_id
            text = chunk_texts.get(chunk_id)

            if text is None or not text.strip():
                continue

            text = text.strip()

            formatted = (
                f"[Chunk {chunk_id} | "
                f"similarity={result.similarity:.4f}]\n"
                f"{text}"
            )

            additional_length = len(formatted)

            if current_length + additional_length > self.max_characters:
                remaining = self.max_characters - current_length

                if remaining <= 0:
                    break

                formatted = formatted[:remaining]

                if not formatted.strip():
                    break

                text = text[:remaining]

                items.append(
                    ContextItem(
                        document_chunk_id=chunk_id,
                        text=text,
                        similarity=result.similarity,
                    )
                )
                context_parts.append(formatted)
                current_length += len(formatted)
                break

            items.append(
                ContextItem(
                    document_chunk_id=chunk_id,
                    text=text,
                    similarity=result.similarity,
                )
            )
            context_parts.append(formatted)
            current_length += additional_length

        return AssembledContext(
            items=tuple(items),
            text="\n\n".join(context_parts),
        )
