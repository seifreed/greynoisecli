from collections.abc import Sequence

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[
    str, JSONValue
]
type QueryScalar = str | int | float | bool
type QueryValue = QueryScalar | Sequence[QueryScalar]
