import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from http.client import (
    HTTPConnection,
    HTTPException,
    HTTPResponse,
    HTTPSConnection,
    IncompleteRead,
)
from importlib.metadata import version
from ipaddress import ip_address
from math import isfinite
from typing import IO, Never, cast
from urllib.parse import urlencode, urlsplit

from greynoisecli.endpoints import get_endpoint
from greynoisecli.models import JSONValue, QueryValue

DEFAULT_BASE_URL = "https://api.greynoise.io"
DEFAULT_TIMEOUT = 30.0

_CONNECTIONS: Mapping[str, type[HTTPConnection]] = {
    "http": HTTPConnection,
    "https": HTTPSConnection,
}
_USER_AGENT = f"greynoisecli/{version('greynoisecli')}"


def _reject_json_constant(value: str) -> Never:
    raise json.JSONDecodeError("Invalid JSON constant", value, 0)


@dataclass(frozen=True, slots=True)
class GreyNoiseResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> JSONValue:
        return cast(
            JSONValue,
            json.loads(self.body, parse_constant=_reject_json_constant),
        )

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").partition(";")[0].lower()


@dataclass(frozen=True, slots=True)
class ResponseOptions:
    accept: str | None = None
    output: IO[bytes] | None = None


@dataclass(frozen=True, slots=True)
class _PreparedRequest:
    path: str
    body: bytes | None
    headers: Mapping[str, str]


class GreyNoiseAPIError(RuntimeError):
    def __init__(self, response: GreyNoiseResponse) -> None:
        self.response = response
        try:
            payload = response.json()
            message = (
                payload.get("message") or payload.get("error")
                if isinstance(payload, dict)
                else None
            )
        except UnicodeDecodeError, json.JSONDecodeError:
            message = None
        super().__init__(message or f"GreyNoise API returned HTTP {response.status}")


class GreyNoiseTransportError(RuntimeError):
    pass


def _query_pairs(query: Mapping[str, QueryValue]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for name, value in query.items():
        values = (
            value
            if isinstance(value, Sequence) and not isinstance(value, str)
            else (value,)
        )
        for item in values:
            pairs.append(
                (name, str(item).lower() if isinstance(item, bool) else str(item))
            )
    return pairs


def _read_response_body(response: HTTPResponse, output: IO[bytes] | None) -> bytes:
    if output is None or response.status >= HTTPStatus.BAD_REQUEST:
        return response.read()
    expected_length = response.length
    downloaded = 0
    while chunk := response.read(64 * 1024):
        output.write(chunk)
        downloaded += len(chunk)
    if expected_length is not None and downloaded != expected_length:
        raise IncompleteRead(b"", expected_length - downloaded)
    return b""


class GreyNoiseClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        parsed_url = urlsplit(base_url)
        if (
            parsed_url.scheme not in _CONNECTIONS
            or parsed_url.hostname is None
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.path.rstrip("/")
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError("base_url must be an HTTP(S) origin")
        if api_key and parsed_url.scheme == "http":
            try:
                loopback = ip_address(parsed_url.hostname).is_loopback
            except ValueError:
                loopback = parsed_url.hostname == "localhost"
            if not loopback:
                raise ValueError("api_key requires HTTPS outside loopback hosts")
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and greater than zero")
        self.api_key = api_key
        self._scheme = parsed_url.scheme
        self._host = parsed_url.hostname
        self._port = parsed_url.port
        self._timeout = timeout

    def call(
        self,
        operation: str,
        *,
        path: Mapping[str, str] | None = None,
        query: Mapping[str, QueryValue] | None = None,
        body: JSONValue = None,
        accept: str | None = None,
    ) -> GreyNoiseResponse:
        return self.stream(
            operation,
            ResponseOptions(accept=accept),
            path=path,
            query=query,
            body=body,
        )

    def stream(
        self,
        operation: str,
        response_options: ResponseOptions,
        *,
        path: Mapping[str, str] | None = None,
        query: Mapping[str, QueryValue] | None = None,
        body: JSONValue = None,
    ) -> GreyNoiseResponse:
        endpoint = get_endpoint(operation)
        return self._execute(
            endpoint.method,
            endpoint.format_path(path or {}),
            query=query,
            body=body,
            response_options=ResponseOptions(
                accept=response_options.accept or endpoint.accept,
                output=response_options.output,
            ),
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, QueryValue] | None = None,
        body: JSONValue = None,
        accept: str = "application/json",
    ) -> GreyNoiseResponse:
        return self._execute(
            method,
            path,
            query=query,
            body=body,
            response_options=ResponseOptions(accept=accept),
        )

    def _execute(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, QueryValue] | None,
        body: JSONValue,
        response_options: ResponseOptions,
    ) -> GreyNoiseResponse:
        request = self._prepare_request(path, query, body, response_options.accept)
        connection = _CONNECTIONS[self._scheme](
            self._host, self._port, timeout=self._timeout
        )
        try:
            connection.request(
                method, request.path, body=request.body, headers=request.headers
            )
            raw_response = connection.getresponse()
            response = GreyNoiseResponse(
                raw_response.status,
                {name.lower(): value for name, value in raw_response.getheaders()},
                _read_response_body(raw_response, response_options.output),
            )
        except (HTTPException, OSError) as error:
            raise GreyNoiseTransportError(
                f"Cannot reach GreyNoise API: {error}"
            ) from error
        finally:
            connection.close()
        if response.status >= HTTPStatus.BAD_REQUEST:
            raise GreyNoiseAPIError(response)
        return response

    def _prepare_request(
        self,
        path: str,
        query: Mapping[str, QueryValue] | None,
        body: JSONValue,
        accept: str | None,
    ) -> _PreparedRequest:
        if not path.startswith("/"):
            raise ValueError("path must start with a slash")
        query_string = urlencode(_query_pairs(query or {}))
        if query_string:
            path = f"{path}?{query_string}"
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        headers = {
            "Accept": accept or "application/json",
            "User-Agent": _USER_AGENT,
        }
        if self.api_key:
            headers["key"] = self.api_key
        if data is not None:
            headers["Content-Type"] = "application/json"
        return _PreparedRequest(path, data, headers)
