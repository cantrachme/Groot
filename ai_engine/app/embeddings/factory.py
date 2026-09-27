import os

from .config import EmbeddingConfig
from .local import LocalEmbeddingProvider
from .ollama import OllamaEmbeddingProvider
from .provider import EmbeddingProvider


def build_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    if config.provider == "local":
        return LocalEmbeddingProvider(config)
    if config.provider == "ollama":
        return OllamaEmbeddingProvider(
            config, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
    raise ValueError(f"Unsupported embedding provider: {config.provider}")
