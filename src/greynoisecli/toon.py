import math
import re
from collections.abc import Collection
from decimal import Decimal
from typing import TypeIs, cast

from greynoisecli.models import JSONValue

type JSONPrimitive = None | bool | int | float | str
type FieldShape = tuple[tuple[str, FieldShape | None], ...]

_NUMBER = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?$", re.I)
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_MIN_KEYED_TABLE_SIZE = 2
_CONTROL_CHARACTER_LIMIT = 0x20


def encode_toon(value: JSONValue) -> str:
    """Encode the JSON data model using TOON specification 4.1."""
    if _is_primitive(value):
        return _encode_primitive(value)
    if isinstance(value, list):
        return "\n".join(_array_lines(value, None, 0))
    return "\n".join(_object_lines(value, 0, allow_keyed_table=True))


def _is_primitive(value: JSONValue) -> TypeIs[JSONPrimitive]:
    return not isinstance(value, (dict, list))


def _shape(objects: list[dict[str, JSONValue]]) -> FieldShape | None:
    if not objects or not objects[0]:
        return None
    fields = tuple(objects[0])
    expected = set(fields)
    if any(not item or set(item) != expected for item in objects[1:]):
        return None
    shape: list[tuple[str, FieldShape | None]] = []
    for field in fields:
        values = [item[field] for item in objects]
        if all(_is_primitive(value) for value in values):
            shape.append((field, None))
            continue
        nested = [value for value in values if isinstance(value, dict)]
        nested_shape = _shape(nested) if len(nested) == len(values) else None
        if nested_shape is None:
            return None
        shape.append((field, nested_shape))
    return tuple(shape)


def _tabular_shape(
    values: Collection[JSONValue], minimum_size: int = 0
) -> FieldShape | None:
    if len(values) < minimum_size:
        return None
    objects = [value for value in values if isinstance(value, dict)]
    return _shape(objects) if len(objects) == len(values) else None


def _encode_key(value: str) -> str:
    _validate_unicode(value)
    return value if _KEY.fullmatch(value) else _quote(value)


def _quote(value: str) -> str:
    escaped: list[str] = []
    replacements = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    for character in value:
        codepoint = ord(character)
        if character in replacements:
            escaped.append(replacements[character])
        elif codepoint < _CONTROL_CHARACTER_LIMIT:
            escaped.append(f"\\u{codepoint:04x}")
        else:
            escaped.append(character)
    return f'"{"".join(escaped)}"'


def _validate_unicode(value: str) -> None:
    if any("\ud800" <= character <= "\udfff" for character in value):
        raise ValueError("TOON cannot encode unpaired Unicode surrogates")


def _encode_string(value: str) -> str:
    _validate_unicode(value)
    must_quote = (
        not value
        or value != value.strip(" \t")
        or value in {"true", "false", "null"}
        or _NUMBER.fullmatch(value) is not None
        or any(character in value for character in ':"\\[]{},')
        or any(ord(character) < _CONTROL_CHARACTER_LIMIT for character in value)
        or value.startswith(("-", "#"))
    )
    return _quote(value) if must_quote else value


def _encode_number(value: int | float) -> str:
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        return "null"
    if value == 0:
        return "0"
    decimal = Decimal(str(value))
    if Decimal("1e-6") <= abs(decimal) < Decimal("1e21"):
        formatted = format(decimal, "f")
        return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted
    return format(decimal.normalize(), "e")


def _encode_primitive(value: JSONPrimitive) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return _encode_number(value)
    return _encode_string(value)


def _shape_fields(shape: FieldShape) -> str:
    return ",".join(
        _encode_key(field)
        + (f"{{{_shape_fields(nested)}}}" if nested is not None else "")
        for field, nested in shape
    )


def _flatten(value: dict[str, JSONValue], shape: FieldShape) -> list[JSONPrimitive]:
    flattened: list[JSONPrimitive] = []
    for field, nested in shape:
        item = value[field]
        if nested is None and _is_primitive(item):
            flattened.append(item)
        else:
            flattened.extend(
                _flatten(cast(dict[str, JSONValue], item), cast(FieldShape, nested))
            )
    return flattened


def _encode_row(value: dict[str, JSONValue], shape: FieldShape) -> str:
    return ",".join(_encode_primitive(cell) for cell in _flatten(value, shape))


def _header(key: str | None, length: int, shape: FieldShape | None = None) -> str:
    name = _encode_key(key) if key is not None else ""
    fields = f"{{{_shape_fields(shape)}}}" if shape is not None else ""
    return f"{name}[{length}]{fields}:"


def _array_lines(
    value: list[JSONValue], key: str | None, depth: int, prefix: str = ""
) -> list[str]:
    indentation = "  " * depth
    if not value:
        token = f"{_encode_key(key)}: []" if key is not None else "[]"
        return [f"{indentation}{prefix}{token}"]
    primitives = [item for item in value if _is_primitive(item)]
    if len(primitives) == len(value):
        cells = ",".join(_encode_primitive(item) for item in primitives)
        return [f"{indentation}{prefix}{_header(key, len(value))} {cells}"]
    shape = _tabular_shape(value)
    if shape is not None and (key is not None or not prefix):
        return _tabular_array_lines(value, key, shape, depth, prefix)
    lines = [f"{indentation}{prefix}{_header(key, len(value))}"]
    content_depth = depth + (2 if key is not None and prefix else 1)
    for item in value:
        lines.extend(_list_item_lines(item, content_depth))
    return lines


def _tabular_array_lines(
    value: list[JSONValue],
    key: str | None,
    shape: FieldShape,
    depth: int,
    prefix: str,
) -> list[str]:
    lines = [f"{'  ' * depth}{prefix}{_header(key, len(value), shape)}"]
    row_depth = depth + (2 if key is not None and prefix else 1)
    for item in cast(list[dict[str, JSONValue]], value):
        lines.append(f"{'  ' * row_depth}{_encode_row(item, shape)}")
    return lines


def _list_item_lines(value: JSONValue, depth: int) -> list[str]:
    if _is_primitive(value):
        return [f"{'  ' * depth}- {_encode_primitive(value)}"]
    if isinstance(value, list):
        if not value:
            return [f"{'  ' * depth}- [0]:"]
        return _array_lines(value, None, depth, "- ")
    if not value:
        return [f"{'  ' * depth}-"]
    return _object_item_lines(value, depth)


def _object_item_lines(value: dict[str, JSONValue], depth: int) -> list[str]:
    fields = list(value.items())
    first_key, first_value = fields[0]
    lines = _field_lines(first_key, first_value, depth, "- ")
    for key, item in fields[1:]:
        lines.extend(_field_lines(key, item, depth + 1))
    return lines


def _object_lines(
    value: dict[str, JSONValue], depth: int, *, allow_keyed_table: bool
) -> list[str]:
    shape = (
        _tabular_shape(value.values(), _MIN_KEYED_TABLE_SIZE)
        if allow_keyed_table
        else None
    )
    if shape is not None:
        return _keyed_table_lines(value, None, shape, depth, "")
    lines: list[str] = []
    for key, item in value.items():
        lines.extend(_field_lines(key, item, depth))
    return lines


def _field_lines(key: str, value: JSONValue, depth: int, prefix: str = "") -> list[str]:
    if _is_primitive(value):
        line = f"{_encode_key(key)}: {_encode_primitive(value)}"
        return [f"{'  ' * depth}{prefix}{line}"]
    if isinstance(value, list):
        return _array_lines(value, key, depth, prefix)
    shape = _tabular_shape(value.values(), _MIN_KEYED_TABLE_SIZE)
    if shape is not None:
        return _keyed_table_lines(value, key, shape, depth, prefix)
    lines = [f"{'  ' * depth}{prefix}{_encode_key(key)}:"]
    child_depth = depth + (2 if prefix else 1)
    lines.extend(_object_lines(value, child_depth, allow_keyed_table=False))
    return lines


def _keyed_table_lines(
    value: dict[str, JSONValue],
    key: str | None,
    shape: FieldShape,
    depth: int,
    prefix: str,
) -> list[str]:
    name = _encode_key(key) if key is not None else ""
    header = f"{name}[{len(value)}:]{{{_shape_fields(shape)}}}:"
    lines = [f"{'  ' * depth}{prefix}{header}"]
    row_depth = depth + (2 if key is not None and prefix else 1)
    for entry, item in cast(dict[str, dict[str, JSONValue]], value).items():
        lines.append(
            f"{'  ' * row_depth}{_encode_key(entry)}: {_encode_row(item, shape)}"
        )
    return lines
