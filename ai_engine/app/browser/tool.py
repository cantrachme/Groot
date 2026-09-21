from .models import BrowserResult, BrowserState


class BrowserTool:
    """Basic browser abstraction for page operations."""

    def __init__(self) -> None:
        self._state: BrowserState | None = None

    def open_page(self, url: str) -> BrowserState:
        self._state = BrowserState(
            current_url=url,
            title=url,
        )
        return self._state

    def navigate(self, url: str) -> BrowserState:
        self._state = BrowserState(
            current_url=url,
            title=url,
        )
        return self._state

    def extract_information(
        self,
        query: str,
    ) -> BrowserResult:
        return BrowserResult(
            action="extract_information",
            data={
                "query": query,
            },
        )

    def interact(
        self,
        *,
        target: str,
        action: str,
    ) -> BrowserResult:
        return BrowserResult(
            action="interact",
            data={
                "target": target,
                "action": action,
            },
        )

    def get_state(self) -> BrowserState | None:
        return self._state
