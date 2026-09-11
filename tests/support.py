import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from greynoisecli import GreyNoiseResponse

STREAM_BODY = bytes(range(256)) * 4096


def expect(condition: bool, message: str = "expectation failed") -> None:
    if not condition:
        raise AssertionError(message)


def json_object(response: GreyNoiseResponse) -> Mapping[str, object]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError("expected object response")
    return payload


def _set_environment(values: Mapping[str, str | None]) -> None:
    for name, value in values.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@contextmanager
def environment(**changes: str | None) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in changes}
    try:
        _set_environment(changes)
        yield
    finally:
        _set_environment(previous)
