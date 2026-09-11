import pytest

from greynoisecli.models import JSONValue
from greynoisecli.output import format_json, format_table
from greynoisecli.toon import encode_toon
from tests.support import expect


def test_structured_output_formats() -> None:
    expect(format_json({"á": True}) == '{\n  "á": true\n}\n')
    expect(format_json("\ud800").encode() == b'"\\ud800"\n')

    object_table = format_table({"name": "Ada", "active": True})
    expect(all(value in object_table for value in ("Field", "Value", "Ada", "true")))
    rows_table = format_table([{"a": 1}, {"b": 2}])
    expect(all(value in rows_table for value in ("a", "b", "1", "2")))
    empty_object_table = format_table([{}])
    expect("{}" in empty_object_table)
    scalar_table = format_table("hello")
    expect("Value" in scalar_table and "hello" in scalar_table)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_json_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValueError, match="Out of range float values"):
        format_json(value)


def test_table_renders_untrusted_text_literally() -> None:
    table = format_table(
        [
            {
                "[bold]field[/bold]\x1b": "[red]value[/red]\n\u202e",
            }
        ]
    )

    expect("[bold]field[/bold]\\u001b" in table)
    expect("[red]value[/red]\\n\\u202e" in table)
    expect("\x1b" not in table)
    expect("\u202e" not in table)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (7, "7"),
        (-0.0, "0"),
        (1.5, "1.5"),
        (0.000001, "0.000001"),
        (0.0000001, "1e-7"),
        (1e20, "100000000000000000000"),
        (1e21, "1e+21"),
        (float("inf"), "null"),
        ("hello world", "hello world"),
        ("", '""'),
        (" true", '" true"'),
        ("true", '"true"'),
        ("+12", '"+12"'),
        ('a:"b"', '"a:\\"b\\""'),
        ("[a],b", '"[a],b"'),
        ("line\nnext", '"line\\nnext"'),
        ("-value", '"-value"'),
        ("#value", '"#value"'),
        ("control\x01", '"control\\u0001"'),
    ],
)
def test_toon_primitives(value: JSONValue, expected: str) -> None:
    expect(encode_toon(value) == expected)


def test_toon_structures() -> None:
    expect(encode_toon({}) == "")
    expect(encode_toon([]) == "[]")
    expect(encode_toon([1, "two"]) == "[2]: 1,two")
    expect(encode_toon([{}, {}]) == "[2]:\n  -\n  -")
    expect(
        encode_toon([{"data": {}}, {"data": {"id": 1}}])
        == "[2]:\n  - data:\n  - data:\n      id: 1"
    )
    expect(
        encode_toon(
            [
                {"id": 1, "profile": {"name": "Ada", "country": "UK"}},
                {"profile": {"country": "US", "name": "Bob"}, "id": 2},
            ]
        )
        == "[2]{id,profile{name,country}}:\n  1,Ada,UK\n  2,Bob,US"
    )
    expect(
        encode_toon(
            {
                "alice": {"id": 1, "active": True},
                "bob smith": {"active": False, "id": 2},
            }
        )
        == '[2:]{id,active}:\n  alice: 1,true\n  "bob smith": 2,false'
    )
    expect(
        encode_toon(
            {
                "items": [
                    {"id": 1, "tags": ["one", "two"]},
                    {},
                    [1, 2],
                    [],
                    [[1], [2, 3]],
                    None,
                ],
                "empty": [],
                "nested": {"value": "x"},
            }
        )
        == "items[6]:\n"
        "  - id: 1\n"
        "    tags[2]: one,two\n"
        "  -\n"
        "  - [2]: 1,2\n"
        "  - [0]:\n"
        "  - [2]:\n"
        "    - [1]: 1\n"
        "    - [2]: 2,3\n"
        "  - null\n"
        "empty: []\n"
        "nested:\n"
        "  value: x"
    )
    expect(
        encode_toon([{"nested": {"x": 1}, "name": "item"}, {"name": "plain"}])
        == "[2]:\n"
        "  - nested:\n"
        "      x: 1\n"
        "    name: item\n"
        "  - name: plain"
    )
    expect(
        encode_toon([{"rows": [{"id": 1}, {"id": 2}], "state": "ok"}, None]) == "[2]:\n"
        "  - rows[2]{id}:\n"
        "      1\n"
        "      2\n"
        "    state: ok\n"
        "  - null"
    )
    expect(
        encode_toon(
            {
                "teams": {
                    "red": {"score": 1},
                    "blue": {"score": 2},
                }
            }
        )
        == "teams[2:]{score}:\n  red: 1\n  blue: 2"
    )


@pytest.mark.parametrize("value", ["\ud800", {"\ud800": 1}])
def test_toon_rejects_unpaired_unicode_surrogates(value: JSONValue) -> None:
    with pytest.raises(ValueError, match="surrogates"):
        encode_toon(value)
