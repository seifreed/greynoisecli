from importlib.metadata import version
from pathlib import Path

from greynoisecli.client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    GreyNoiseAPIError,
    GreyNoiseClient,
    GreyNoiseResponse,
    GreyNoiseTransportError,
    ResponseOptions,
)
from greynoisecli.config import load_api_key
from greynoisecli.endpoints import ENDPOINTS, Endpoint

__all__ = [
    "ENDPOINTS",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "Endpoint",
    "GreyNoiseAPIError",
    "GreyNoiseClient",
    "GreyNoiseResponse",
    "GreyNoiseTransportError",
    "ResponseOptions",
    "create_client",
]

__version__ = version("greynoisecli")


def create_client(
    *,
    config_path: Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
) -> GreyNoiseClient:
    return GreyNoiseClient(
        load_api_key(config_path),
        base_url=base_url,
        timeout=timeout,
    )
