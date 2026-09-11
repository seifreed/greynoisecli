import json
import socket
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import pytest

from greynoisecli import (
    GreyNoiseAPIError,
    GreyNoiseClient,
    GreyNoiseResponse,
    GreyNoiseTransportError,
    ResponseOptions,
    create_client,
)
from tests.support import STREAM_BODY, environment, expect, json_object


def test_client_requires_https_for_api_keys_outside_loopback() -> None:
    for base_url in (
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
    ):
        GreyNoiseClient(api_key="secret", base_url=base_url)

    with pytest.raises(ValueError, match="HTTPS"):
        GreyNoiseClient(api_key="secret", base_url="http://api.greynoise.io")


@pytest.mark.parametrize("body", (b"NaN", b"Infinity", b"-Infinity"))
def test_response_rejects_non_standard_json_constants(body: bytes) -> None:
    with pytest.raises(json.JSONDecodeError):
        GreyNoiseResponse(200, {}, body).json()


def test_client_requests_and_errors(api_url: str) -> None:
    client = GreyNoiseClient(api_key="secret", base_url=f"{api_url}/", timeout=2)
    response = client.request(
        "POST",
        "/echo",
        query={"item": ["one", "two"], "enabled": True, "size": 2},
        body={"ok": True, "score": 1.5},
    )
    payload = json_object(response)
    expect(payload["method"] == "POST")
    expect(
        payload["query"] == {"item": ["one", "two"], "enabled": ["true"], "size": ["2"]}
    )
    expect(payload["key"] == "secret")
    expect(payload["accept"] == "application/json")
    expect(payload["content_type"] == "application/json")
    expect(payload["body"] == {"ok": True, "score": 1.5})

    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="Out of range float values"):
            client.request("POST", "/echo", body={"value": value})

    response = client.call("get-community-ip", path={"ip": "8.8.8.8"})
    payload = json_object(response)
    expect(payload["path"] == "/v3/community/8.8.8.8")
    expect(payload["body"] is None)

    response = client.call(
        "postPsychicModelDownload",
        body={"model": "internet_scanner_intelligence"},
        accept="application/vnd.maxmind.maxmind-db",
    )
    payload = json_object(response)
    expect(payload["accept"] == "application/vnd.maxmind.maxmind-db")

    response = client.request("GET", "/echo", accept="text/csv")
    payload = json_object(response)
    expect(payload["accept"] == "text/csv")

    with pytest.raises(GreyNoiseAPIError, match="bad request") as error:
        client.request("GET", "/error-json")
    expect(error.value.response.status == HTTPStatus.BAD_REQUEST)

    payload_error = GreyNoiseAPIError(
        GreyNoiseResponse(403, {}, b'{"error":"feature not allowed"}')
    )
    expect(str(payload_error) == "feature not allowed")
    list_error = GreyNoiseAPIError(GreyNoiseResponse(403, {}, b"[]"))
    expect(str(list_error) == "GreyNoise API returned HTTP 403")
    binary_error = GreyNoiseAPIError(GreyNoiseResponse(500, {}, b"\xff"))
    expect(str(binary_error) == "GreyNoise API returned HTTP 500")


def test_client_streams_response(api_url: str) -> None:
    output = BytesIO()
    response = GreyNoiseClient(base_url=api_url).stream(
        "ping", ResponseOptions(output=output), query={"stream": True}
    )
    expect(response.body == b"")
    expect(output.getvalue() == STREAM_BODY)


def test_client_loads_config_and_transport_error(tmp_path: Path, api_url: str) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[greynoise]\napi_key = "configured"\n', encoding="utf-8")
    with environment(GREYNOISE=None):
        client = create_client(config_path=config, base_url=api_url)
    payload = json_object(client.request("GET", "/echo"))
    expect(payload["key"] == "configured")

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    _, port = listener.getsockname()
    listener.close()
    unavailable = GreyNoiseClient(base_url=f"http://127.0.0.1:{port}", timeout=0.1)
    with pytest.raises(GreyNoiseTransportError, match="Cannot reach"):
        unavailable.request("GET", "/")
    with pytest.raises(ValueError, match="HTTP"):
        GreyNoiseClient(base_url="file:///tmp/data")
    with pytest.raises(ValueError, match="HTTP"):
        GreyNoiseClient(base_url="https://user:password@api.greynoise.io")
    for timeout in (0, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="timeout"):
            GreyNoiseClient(timeout=timeout)
    with pytest.raises(ValueError, match="slash"):
        client.request("GET", "relative")
