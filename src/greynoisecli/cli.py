import argparse
import json
import sys
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, cast

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
from greynoisecli.models import JSONValue, QueryValue
from greynoisecli.output import (
    OutputFormat,
    StructuredOutputFormat,
    escape_control_characters,
    format_json,
    format_value,
)

_OUTPUT_FORMATS = ("auto", "json", "table", "toon")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="greynoise",
        description="Access every operation in the GreyNoise API.",
    )
    parser.add_argument("--config", type=Path, help="TOML config file")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="request timeout in seconds",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("operations", help="list supported API operations")
    for endpoint in ENDPOINTS:
        operation = subparsers.add_parser(
            endpoint.command,
            help=endpoint.summary,
            description=f"{endpoint.summary}\n\n{endpoint.method} {endpoint.path}",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        _configure_operation_parser(operation, endpoint)
    return parser


def _configure_operation_parser(
    parser: argparse.ArgumentParser, endpoint: Endpoint
) -> None:
    for parameter in endpoint.path_parameters:
        parser.add_argument(parameter, help=f"value for {{{parameter}}}")
    parser.add_argument(
        "-q",
        "--query",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="query parameter; repeat for multiple values",
    )
    parser.add_argument(
        "--data",
        metavar="JSON|@FILE",
        help="JSON request body, inline or read from @FILE",
    )
    parser.add_argument("-o", "--output", type=Path, help="write response to file")
    parser.add_argument(
        "--format",
        choices=_OUTPUT_FORMATS,
        default="auto",
        help="response format (default: auto)",
    )
    parser.add_argument(
        "--accept", help="override the response media type requested from the API"
    )
    parser.set_defaults(endpoint=endpoint)


def _parse_query(values: Sequence[str]) -> Mapping[str, QueryValue]:
    query: dict[str, list[str]] = {}
    for value in values:
        name, separator, item = value.partition("=")
        if not separator or not name:
            raise ValueError(f"Invalid query parameter {value!r}; expected NAME=VALUE")
        query.setdefault(name, []).append(item)
    return query


def _parse_body(value: str | None) -> JSONValue:
    if value is None:
        return None
    source = (
        Path(value[1:]).read_text(encoding="utf-8") if value.startswith("@") else value
    )
    return cast(JSONValue, json.loads(source))


def _format_response(
    response: GreyNoiseResponse, output_format: StructuredOutputFormat
) -> str:
    try:
        value = response.json()
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{output_format} output requires a JSON response") from error
    return format_value(value, output_format)


def _emit_response(
    response: GreyNoiseResponse, output_format: OutputFormat = "auto"
) -> None:
    if output_format != "auto":
        sys.stdout.write(_format_response(response, output_format))
        return
    content_type = response.content_type
    if content_type == "application/json" or content_type.endswith("+json"):
        sys.stdout.write(format_json(response.json()))
    elif content_type.startswith("text/") or content_type.endswith("xml"):
        sys.stdout.write(response.body.decode())
    else:
        sys.stdout.buffer.write(response.body)


@contextmanager
def _atomic_output(output: Path) -> Iterator[IO[bytes]]:
    with TemporaryDirectory(dir=output.parent, prefix=f".{output.name}.") as directory:
        temporary_path = Path(directory) / output.name
        with temporary_path.open("wb") as temporary:
            yield temporary
        temporary_path.replace(output)


def _list_operations() -> None:
    for endpoint in ENDPOINTS:
        print(f"{endpoint.command:45} {endpoint.method:6} {endpoint.path}")


def _write_formatted_response(
    response: GreyNoiseResponse,
    output_format: StructuredOutputFormat,
    output_path: Path,
) -> None:
    with _atomic_output(output_path) as output:
        output.write(_format_response(response, output_format).encode("utf-8"))


def run(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "operations":
        _list_operations()
        return 0

    endpoint: Endpoint = arguments.endpoint
    path = {name: getattr(arguments, name) for name in endpoint.path_parameters}
    client = GreyNoiseClient(
        load_api_key(arguments.config),
        base_url=arguments.base_url,
        timeout=arguments.timeout,
    )
    query = _parse_query(arguments.query)
    body = _parse_body(arguments.data)
    if arguments.output is not None and arguments.format == "auto":
        with _atomic_output(arguments.output) as output:
            client.stream(
                endpoint.operation_id,
                ResponseOptions(arguments.accept, output),
                path=path,
                query=query,
                body=body,
            )
        return 0
    response = client.call(
        endpoint.operation_id,
        path=path,
        query=query,
        body=body,
        accept=arguments.accept,
    )
    if arguments.output is not None:
        _write_formatted_response(
            response,
            cast(StructuredOutputFormat, arguments.format),
            arguments.output,
        )
    else:
        _emit_response(response, cast(OutputFormat, arguments.format))
    return 0


def main() -> int:
    try:
        return run()
    except (
        GreyNoiseAPIError,
        GreyNoiseTransportError,
        OSError,
        ValueError,
    ) as error:
        print(
            f"greynoise: error: {escape_control_characters(str(error))}",
            file=sys.stderr,
        )
        return 1
