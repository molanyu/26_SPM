from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import Request


class ParsedForm:
    def __init__(self, values: dict[str, list[str]]) -> None:
        self._values = values

    def get(self, name: str, default: object = None) -> object:
        values = self._values.get(name)
        if not values:
            return default
        return values[0]

    def getlist(self, name: str) -> list[str]:
        return list(self._values.get(name, []))


async def parse_simple_form(request: Request) -> ParsedForm:
    body = await request.body()
    values = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return ParsedForm(values)
