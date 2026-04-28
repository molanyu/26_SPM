from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from html import escape
from pathlib import Path

from fastapi.responses import HTMLResponse

TEMPLATE_ROOT = Path(__file__).resolve().parents[3] / "templates" / "admin"
_RAW_PATTERN = re.compile(r"{{{\s*([a-zA-Z0-9_]+)\s*}}}")
_ESCAPED_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def render_page(page_name: str, context: dict[str, object], *, status_code: int = 200) -> HTMLResponse:
    page_context = _build_page_context(page_name, context)
    body_html = _render_template(_load_template(f"{page_name}.html"), page_context)
    layout_context = {
        "page_title": context["page_title"],
        "current_admin_name": context["current_admin"].name,
        "current_admin_id": context["current_admin"].id,
        "current_admin_email": context["current_admin"].email or "-",
        "menu_items_html": _render_menu_items(context.get("menus", []), str(context.get("page_key", ""))),
        "success_notice_html": _render_notice("success", context.get("success_message")),
        "error_notice_html": _render_notice("error", context.get("error_message")),
        "body_html": body_html,
    }
    html = _render_template(_load_template("layout.html"), layout_context)
    return HTMLResponse(content=html, status_code=status_code)


@lru_cache(maxsize=None)
def _load_template(filename: str) -> str:
    return (TEMPLATE_ROOT / filename).read_text(encoding="utf-8")


def _render_template(template: str, context: dict[str, object]) -> str:
    rendered = _RAW_PATTERN.sub(lambda match: _stringify(context.get(match.group(1))), template)
    return _ESCAPED_PATTERN.sub(lambda match: escape(_stringify(context.get(match.group(1))), quote=True), rendered)


def _render_menu_items(menus: Iterable[dict[str, object]], page_key: str) -> str:
    return "".join(
        (
            f'<li><a href="{escape(str(menu["href"]), quote=True)}"'
            f' class="{"active" if str(menu["code"]) == page_key else ""}">'
            f'{escape(str(menu["label"]))}</a></li>'
        )
        for menu in menus
    )


def _render_notice(kind: str, message: object) -> str:
    if not message:
        return ""
    return f'<div class="notice {kind}">{escape(str(message))}</div>'


def _build_page_context(page_name: str, context: dict[str, object]) -> dict[str, object]:
    builders = {
        "home": _build_home_context,
        "roles": _build_roles_context,
        "user_roles": _build_user_roles_context,
        "rooms": _build_rooms_context,
        "seats": _build_seats_context,
        "system_configs": _build_system_configs_context,
        "reservation_actions": _build_reservation_actions_context,
        "violations": _build_violations_context,
    }
    return builders[page_name](context)


def _build_home_context(context: dict[str, object]) -> dict[str, object]:
    shortcuts_html = "".join(
        (
            f'<a class="card" href="{escape(str(shortcut["href"]), quote=True)}">'
            f'<strong>{escape(str(shortcut["label"]))}</strong>'
            f"<span>{escape(str(shortcut['description']))}</span>"
            "</a>"
        )
        for shortcut in context.get("shortcuts", [])
    )
    return {
        "hero_title": context["hero_title"],
        "hero_description": context["hero_description"],
        "shortcuts_html": shortcuts_html,
    }


def _build_roles_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    permissions = context["permissions"]
    roles = context["roles"]
    create_permissions_html = "".join(
        (
            "<label>"
            f'<input type="checkbox" name="permission_ids" value="{permission["id"]}"'
            f'{_checked(permission["id"] in create_form["permission_ids"])}>'
            f'{escape(str(permission["name"]))}'
            "</label>"
        )
        for permission in permissions
    )
    role_rows_html = "".join(_render_role_row(role, permissions) for role in roles)
    permission_rows_html = "".join(
        (
            "<tr>"
            f"<td>{permission['id']}</td>"
            f"<td>{escape(str(permission['name']))}</td>"
            f"<td><code>{escape(str(permission['code']))}</code></td>"
            f"<td>{escape(str(permission.get('description') or ''))}</td>"
            "</tr>"
        )
        for permission in permissions
    )
    return {
        "create_name": create_form["name"],
        "create_code": create_form["code"],
        "create_description": create_form["description"],
        "create_is_active_checked": _checked(create_form["is_active"]),
        "create_permissions_html": create_permissions_html,
        "role_rows_html": role_rows_html,
        "permission_rows_html": permission_rows_html,
    }


def _render_role_row(role: dict[str, object], permissions: list[dict[str, object]]) -> str:
    role_permission_ids = {permission["id"] for permission in role["permissions"]}
    permission_names = "".join(f"<div>{escape(str(permission['name']))}</div>" for permission in role["permissions"])
    permission_checkboxes = "".join(
        (
            "<label>"
            f'<input type="checkbox" name="permission_ids" value="{permission["id"]}"'
            f'{_checked(permission["id"] in role_permission_ids)}>'
            f'{escape(str(permission["code"]))}'
            "</label>"
        )
        for permission in permissions
    )
    return f"""
<tr>
  <td>{role['id']}</td>
  <td>
    <strong>{escape(str(role['name']))}</strong><br>
    <span class="muted"><code>{escape(str(role['code']))}</code></span><br>
    <span class="muted">{escape(str(role.get('description') or ''))}</span>
  </td>
  <td>{permission_names}</td>
  <td>
    <form method="post" action="/admin/roles/page">
      <input type="hidden" name="form_action" value="update">
      <input type="hidden" name="role_id" value="{role['id']}">
      <div class="fields">
        <label>Name<input name="name" value="{escape(str(role['name']), quote=True)}"></label>
        <label>Code<input name="code" value="{escape(str(role['code']), quote=True)}"></label>
        <label>Description<input name="description" value="{escape(str(role.get('description') or ''), quote=True)}"></label>
      </div>
      <label class="inline-check"><input type="checkbox" name="is_active"{_checked(role['is_active'])}>Active</label>
      <div class="checkbox-group">{permission_checkboxes}</div>
      <div class="actions"><button class="secondary" type="submit">Update Role</button></div>
    </form>
  </td>
</tr>
"""


def _build_user_roles_context(context: dict[str, object]) -> dict[str, object]:
    selected_role_ids = set(context.get("selected_role_ids", []))
    role_checkboxes_html = "".join(
        (
            "<label>"
            f'<input type="checkbox" name="role_ids" value="{role["id"]}"'
            f'{_checked(role["id"] in selected_role_ids)}>'
            f'{escape(str(role["name"]))} <code>{escape(str(role["code"]))}</code>'
            "</label>"
        )
        for role in context["roles"]
    )
    return {
        "target_user_id": context["target_user_id"],
        "role_checkboxes_html": role_checkboxes_html,
    }


def _build_rooms_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    room_rows_html = "".join(_render_room_row(room) for room in context["rooms"])
    return {
        "create_name": create_form["name"],
        "create_location": create_form["location"],
        "create_department_id": create_form["department_id"],
        "create_open_time": create_form["open_time"],
        "create_close_time": create_form["close_time"],
        "create_department_only_checked": _checked(create_form["is_department_only"]),
        "create_active_checked": _checked(create_form["is_active"]),
        "room_rows_html": room_rows_html,
    }


def _render_room_row(room: dict[str, object]) -> str:
    department_id = "" if room["department_id"] is None else str(room["department_id"])
    return f"""
<tr>
  <td>{room['id']}</td>
  <td>
    <strong>{escape(str(room['name']))}</strong><br>
    <span class="muted">{escape(str(room['location']))}</span><br>
    <span class="muted">department_id={escape(department_id or 'None')}</span><br>
    <span class="muted">{escape(str(room['open_time']))} - {escape(str(room['close_time']))}</span>
  </td>
  <td>
    <form method="post" action="/admin/rooms/page">
      <input type="hidden" name="form_action" value="update">
      <input type="hidden" name="room_id" value="{room['id']}">
      <div class="fields">
        <label>Name<input name="name" value="{escape(str(room['name']), quote=True)}"></label>
        <label>Location<input name="location" value="{escape(str(room['location']), quote=True)}"></label>
        <label>Department ID<input name="department_id" value="{escape(department_id, quote=True)}"></label>
        <label>Open Time<input name="open_time" value="{escape(str(room['open_time']), quote=True)}"></label>
        <label>Close Time<input name="close_time" value="{escape(str(room['close_time']), quote=True)}"></label>
      </div>
      <div class="checkbox-group">
        <label><input type="checkbox" name="is_department_only"{_checked(room['is_department_only'])}>Department only</label>
        <label><input type="checkbox" name="is_active"{_checked(room['is_active'])}>Active</label>
      </div>
      <div class="actions"><button class="secondary" type="submit">Update</button></div>
    </form>
    <form method="post" action="/admin/rooms/page">
      <input type="hidden" name="form_action" value="deactivate">
      <input type="hidden" name="room_id" value="{room['id']}">
      <div class="actions"><button class="danger" type="submit">Deactivate</button></div>
    </form>
  </td>
</tr>
"""


def _build_seats_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    selected_room_id = context.get("selected_room_id")
    selected_room_text = "" if selected_room_id is None else str(selected_room_id)
    return {
        "filter_room_options_html": _render_room_options(context["rooms"], selected_room_text, include_all=True),
        "create_room_options_html": _render_room_options(context["rooms"], str(create_form["room_id"])),
        "create_seat_code": create_form["seat_code"],
        "create_seat_label": create_form["seat_label"],
        "create_active_checked": _checked(create_form["is_active"]),
        "create_window_side_checked": _checked(create_form["is_window_side"]),
        "create_power_socket_checked": _checked(create_form["has_power_socket"]),
        "create_track_socket_checked": _checked(create_form["has_track_socket"]),
        "selected_room_id": selected_room_text,
        "seat_rows_html": "".join(
            _render_seat_row(seat, context["rooms"], selected_room_text) for seat in context["seats"]
        ),
    }


def _render_seat_row(seat: dict[str, object], rooms: list[dict[str, object]], selected_room_id: str) -> str:
    room_options_html = _render_room_options(rooms, str(seat["room_id"]))
    return f"""
<tr>
  <td>{seat['id']}</td>
  <td>
    <strong>{escape(str(seat['seat_label']))}</strong><br>
    <span class="muted"><code>{escape(str(seat['seat_code']))}</code></span><br>
    <span class="muted">room_id={seat['room_id']}</span>
  </td>
  <td>
    <form method="post" action="/admin/seats/page">
      <input type="hidden" name="form_action" value="update">
      <input type="hidden" name="seat_id" value="{seat['id']}">
      <input type="hidden" name="filter_room_id" value="{escape(selected_room_id, quote=True)}">
      <div class="fields">
        <label>Room<select name="room_id">{room_options_html}</select></label>
        <label>Seat Code<input name="seat_code" value="{escape(str(seat['seat_code']), quote=True)}"></label>
        <label>Seat Label<input name="seat_label" value="{escape(str(seat['seat_label']), quote=True)}"></label>
      </div>
      <div class="checkbox-group">
        <label><input type="checkbox" name="is_active"{_checked(seat['is_active'])}>Active</label>
        <label><input type="checkbox" name="is_window_side"{_checked(seat['is_window_side'])}>Window side</label>
        <label><input type="checkbox" name="has_power_socket"{_checked(seat['has_power_socket'])}>Power socket</label>
        <label><input type="checkbox" name="has_track_socket"{_checked(seat['has_track_socket'])}>Track socket</label>
      </div>
      <div class="actions"><button class="secondary" type="submit">Update</button></div>
    </form>
    <form method="post" action="/admin/seats/page">
      <input type="hidden" name="form_action" value="deactivate">
      <input type="hidden" name="seat_id" value="{seat['id']}">
      <input type="hidden" name="filter_room_id" value="{escape(selected_room_id, quote=True)}">
      <div class="actions"><button class="danger" type="submit">Deactivate</button></div>
    </form>
  </td>
</tr>
"""


def _render_room_options(
    rooms: Iterable[dict[str, object]],
    selected_room_id: str,
    *,
    include_all: bool = False,
) -> str:
    options: list[str] = []
    if include_all:
        options.append(f'<option value=""{_selected(selected_room_id == "")}>All rooms</option>')
    for room in rooms:
        room_id = str(room["id"])
        options.append(
            f'<option value="{escape(room_id, quote=True)}"{_selected(room_id == selected_room_id)}>'
            f"{escape(room_id)} - {escape(str(room['name']))}</option>"
        )
    return "".join(options)


def _build_system_configs_context(context: dict[str, object]) -> dict[str, object]:
    config_rows_html = "".join(
        f"""
<tr>
  <td><code>{escape(str(config['config_key']))}</code></td>
  <td>{escape(str(config['config_value']))}</td>
  <td>{escape(str(config.get('description') or ''))}</td>
  <td>
    <form method="post" action="/admin/system-configs/page">
      <input type="hidden" name="config_key" value="{escape(str(config['config_key']), quote=True)}">
      <label>New Value<input name="config_value" value="{escape(str(config['config_value']), quote=True)}"></label>
      <div class="actions"><button type="submit">Update Config</button></div>
    </form>
  </td>
</tr>
"""
        for config in context["configs"]
    )
    return {"config_rows_html": config_rows_html}


def _build_reservation_actions_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    cancel_form = context["cancel_form"]
    create_result = context.get("create_result")
    cancel_result = context.get("cancel_result")
    return {
        "create_user_id": create_form["user_id"],
        "create_seat_id": create_form["seat_id"],
        "create_start_time": create_form["start_time"],
        "create_end_time": create_form["end_time"],
        "cancel_reservation_id": cancel_form["reservation_id"],
        "cancel_reason": cancel_form["reason"],
        "create_result_html": _render_reservation_result("Latest create result", create_result),
        "cancel_result_html": _render_reservation_result("Latest cancel result", cancel_result),
    }


def _render_reservation_result(title: str, payload: dict[str, object] | None) -> str:
    if not payload:
        return ""
    return (
        f'<p class="muted">{escape(title)}: reservation_id={payload["reservation_id"]}, '
        f'status={escape(str(payload["status"]))}</p>'
    )


def _build_violations_context(context: dict[str, object]) -> dict[str, object]:
    filters = context["filters"]
    violation_rows_html = "".join(
        f"""
<tr>
  <td>{item['violation_id']}</td>
  <td>{item['user_id']}</td>
  <td>{item['reservation_id']}</td>
  <td>{item['room_id']}</td>
  <td><code>{escape(str(item['violation_type']))}</code></td>
  <td>{escape(str(item['occurred_at']))}</td>
</tr>
"""
        for item in context["violations"]
    )
    return {
        "filter_user_id": _optional(filters.get("user_id")),
        "filter_room_id": _optional(filters.get("room_id")),
        "filter_date_from": _optional(filters.get("date_from")),
        "filter_date_to": _optional(filters.get("date_to")),
        "filter_page": _optional(filters.get("page")),
        "filter_page_size": _optional(filters.get("page_size")),
        "violations_total": context["total"],
        "violation_rows_html": violation_rows_html,
    }


def _checked(value: bool) -> str:
    return " checked" if value else ""


def _selected(value: bool) -> str:
    return " selected" if value else ""


def _optional(value: object) -> str:
    return "" if value is None else str(value)


def _stringify(value: object) -> str:
    return "" if value is None else str(value)
