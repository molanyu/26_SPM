from __future__ import annotations

from collections.abc import Iterable

from app.modules.identity.constants import MENU_DEFINITIONS


class MenuService:
    def build_menus(self, permission_codes: Iterable[str]) -> list[dict[str, str]]:
        granted = set(permission_codes)
        visible: list[dict[str, str]] = []
        for definition in MENU_DEFINITIONS:
            required = set(definition["required_permissions"])
            if required.issubset(granted):
                visible.append({"code": definition["code"], "label": definition["label"]})
        return visible

