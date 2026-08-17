from .extractors import DocumentExtractor


class DocumentExtractorRegistry:
    """Maps supported MIME types to document extractors."""

    def __init__(
        self,
        extractors: list[DocumentExtractor] | None = None,
    ) -> None:
        self._extractors: dict[str, DocumentExtractor] = {}

        for extractor in extractors or []:
            self.register(extractor)

    def register(self, extractor: DocumentExtractor) -> None:
        for mime_type in extractor.supported_mime_types:
            if mime_type in self._extractors:
                raise ValueError(
                    f"Extractor already registered for MIME type: {mime_type}"
                )

            self._extractors[mime_type] = extractor

    def get(self, mime_type: str) -> DocumentExtractor:
        try:
            return self._extractors[mime_type]
        except KeyError as exc:
            raise KeyError(
                f"No document extractor registered for MIME type: {mime_type}"
            ) from exc

    def has(self, mime_type: str) -> bool:
        return mime_type in self._extractors
