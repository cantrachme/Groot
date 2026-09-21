from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserState:
    current_url: str
    title: str


@dataclass(frozen=True)
class BrowserResult:
    action: str
    data: dict
