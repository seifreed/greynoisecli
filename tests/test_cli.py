import json
import runpy
import sys
from pathlib import Path

import pytest

from greynoisecli import (
    ENDPOINTS,
    GreyNoiseAPIError,
    GreyNoiseResponse,
    GreyNoiseTransportError,
)
from greynoisecli.cli import _emit_response, _parse_body, _parse_query, main, run
from greynoisecli.endpoints import Endpoint
from tests.support import expect


def test_cli_parsing_and_output(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    expect(_parse_query(["a=1", "a=2", "empty="]) == {"a": ["1", "2"], "empty": [""]})
    with pytest.raises(ValueError, match="NAME=VALUE"):
        _parse_query(["broken"])
    expect(_parse_body(None) is None)
    expect(_parse_body('{"value": 1}') == {"value": 1})
    body_file = tmp_path / "body.json"
    body_file.write_text('["value"]', encoding="utf-8")
    expect(_parse_body(f"@{body_file}") == ["value"])

    _emit_response(
        GreyNoiseResponse(200, {"content-type": "application/json"}, b'{"b":1}')
    )
    expect(json.loads(capfd.readouterr().out) == {"b": 1})
    _emit_response(
        GreyNoiseResponse(
            200, {"content-type": "application/problem+json"}, b'"problem"'
        ),
    )
    expect(json.loads(capfd.readouterr().out) == "problem")
    _emit_response(GreyNoiseResponse(200, {"content-type": "text/plain"}, b"text"))
    expect(capfd.readouterr().out == "text")
    _emit_response(
        GreyNoiseResponse(200, {"content-type": "application/xml"}, b"<xml/>")
    )
    expect(capfd.readouterr().out == "<xml/>")
    _emit_response(GreyNoiseResponse(200, {}, b"\x00\x01"))
    expect(capfd.readouterr().out.encode() == b"\x00\x01")

    _emit_response(GreyNoiseResponse(200, {}, b'{"name":"Ada"}'), "json")
    expect(capfd.readouterr().out == '{\n  "name": "Ada"\n}\n')
    _emit_response(GreyNoiseResponse(200, {}, b"[1,2]"), "table")
    table = capfd.readouterr().out
    expect("Value" in table and "1" in table and "2" in table)
    _emit_response(GreyNoiseResponse(200, {}, b'{"users":[1,2]}'), "toon")
    expect(capfd.readouterr().out == "users[2]: 1,2")
    with pytest.raises(ValueError, match="requires a JSON response"):
        _emit_response(GreyNoiseResponse(200, {}, b"not-json"), "toon")


def test_cli_end_to_end(api_url: str, capfd: pytest.CaptureFixture[str]) -> None:
    expect(run(["operations"]) == 0)
    operations_output = capfd.readouterr().out
    expect(len(operations_output.splitlines()) == len(ENDPOINTS))

    previous_argv = sys.argv
    try:
        sys.argv = ["greynoise", "operations"]
        expect(main() == 0)
        capfd.readouterr()
        sys.argv = ["greynoise", "--base-url", api_url, "ping", "--query", "broken"]
        expect(main() == 1)
        expect("NAME=VALUE" in capfd.readouterr().err)
        sys.argv = [
            "greynoise",
            "--base-url",
            api_url,
            "ping",
            "--query",
            "failure=terminal",
        ]
        expect(main() == 1)
        expect(
            capfd.readouterr().err == "greynoise: error: bad\\u001b]0;title\\n\\u202e\n"
        )
        sys.argv = ["greynoise", "operations"]
        with pytest.raises(SystemExit) as exit_status:
            runpy.run_module("greynoisecli.__main__", run_name="__main__")
        expect(exit_status.value.code == 0)
    finally:
        sys.argv = previous_argv


def test_cli_output_is_atomic(
    tmp_path: Path, api_url: str, capfd: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "download.bin"
    output.write_bytes(b"original")

    expect(run(["--base-url", api_url, "ping", "--output", str(output)]) == 0)
    expect(json.loads(output.read_bytes())["path"] == "/ping")
    expect(capfd.readouterr().out == "")

    expect(
        run(
            [
                "--base-url",
                api_url,
                "ping",
                "--format",
                "toon",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    expect(output.read_text(encoding="utf-8").startswith("method: GET\n"))

    output.write_bytes(b"original")
    with pytest.raises(GreyNoiseAPIError, match="download failed"):
        run(
            [
                "--base-url",
                api_url,
                "ping",
                "--query",
                "failure=http",
                "--output",
                str(output),
            ]
        )
    expect(output.read_bytes() == b"original")
    expect(not list(tmp_path.glob(f".{output.name}.*")))

    with pytest.raises(GreyNoiseTransportError):
        run(
            [
                "--base-url",
                api_url,
                "ping",
                "--query",
                "failure=truncated",
                "--output",
                str(output),
            ]
        )
    expect(output.read_bytes() == b"original")
    expect(not list(tmp_path.glob(f".{output.name}.*")))

    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(OSError):
        run(["--base-url", api_url, "ping", "--output", str(directory)])
    expect(directory.is_dir())
    expect(not list(tmp_path.glob(f".{directory.name}.*")))

    missing_output = tmp_path / "missing" / "download.bin"
    with pytest.raises(OSError):
        run(["--base-url", api_url, "ping", "--output", str(missing_output)])
    expect(not missing_output.exists())


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda endpoint: endpoint.command)
def test_every_cli_operation(
    endpoint: Endpoint,
    api_url: str,
    capfd: pytest.CaptureFixture[str],
) -> None:
    path_values = {
        parameter: f"{parameter} value" for parameter in endpoint.path_parameters
    }
    arguments = ["--base-url", api_url, endpoint.command, *path_values.values()]
    arguments.extend(
        [
            "--query",
            "probe=one",
            "--query",
            "probe=two",
            "--data",
            '{"tested":true}',
        ]
    )

    expect(run(arguments) == 0)
    payload = json.loads(capfd.readouterr().out)
    expect(payload["method"] == endpoint.method)
    expect(payload["path"] == endpoint.format_path(path_values))
    expect(payload["query"] == {"probe": ["one", "two"]})
    expect(payload["body"] == {"tested": True})
    expect(payload["accept"] == endpoint.accept)
