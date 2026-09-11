import json
from io import StringIO
from typing import Literal

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from greynoisecli.models import JSONValue
from greynoisecli.toon import encode_toon

type OutputFormat = Literal["auto", "json", "table", "toon"]
type StructuredOutputFormat = Literal["json", "table", "toon"]


def format_json(value: JSONValue) -> str:
    output = json.dumps(
        value, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True
    )
    return output.encode(errors="backslashreplace").decode() + "\n"


def format_table(value: JSONValue) -> str:
    columns, rows = _table_data(value)
    table = Table(box=box.ROUNDED)
    for column in columns:
        table.add_column(Text(escape_control_characters(column)))
    for row in rows:
        table.add_row(*(Text(item) for item in row))
    output = StringIO()
    Console(file=output, color_system=None, width=120).print(table)
    return output.getvalue()


def format_value(value: JSONValue, output_format: StructuredOutputFormat) -> str:
    if output_format == "json":
        return format_json(value)
    if output_format == "table":
        return format_table(value)
    return encode_toon(value)


def escape_control_characters(value: str) -> str:
    return "".join(
        character if character.isprintable() else json.dumps(character)[1:-1]
        for character in value
    )


def _table_data(value: JSONValue) -> tuple[list[str], list[list[str]]]:
    if isinstance(value, dict):
        return ["Field", "Value"], [
            [key, _display_value(item)] for key, item in value.items()
        ]
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, dict) for item in value)
    ):
        objects = [item for item in value if isinstance(item, dict)]
        columns = list(dict.fromkeys(key for item in objects for key in item))
        if columns:
            return columns, [
                [_display_value(item.get(column)) for column in columns]
                for item in objects
            ]
    items = value if isinstance(value, list) else [value]
    return ["Value"], [[_display_value(item)] for item in items]


def _display_value(value: JSONValue) -> str:
    displayed = (
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    )
    return escape_control_characters(displayed)
