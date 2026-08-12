from abc import ABC, abstractmethod


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs) -> object:
        raise NotImplementedError
