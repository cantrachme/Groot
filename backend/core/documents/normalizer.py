import re


class DocumentTextNormalizer:
    """Performs deterministic, meaning-preserving text normalization."""

    def normalize(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\x00", "")

        lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in text.split("\n")
        ]

        while lines and not lines[0]:
            lines.pop(0)

        while lines and not lines[-1]:
            lines.pop()

        return "\n".join(
            line
            for line in lines
            if line
        )
