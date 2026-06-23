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
    body_html = _render_template(_load_asset(f"{page_name}.html"), page_context)
    layout_context = {
        "page_title": context["page_title"],
        "page_intro": context.get("page_intro", ""),
        "current_admin_name": context["current_admin"].name,
        "current_admin_id": context["current_admin"].id,
        "current_admin_email": context["current_admin"].email or "-",
        "menu_items_html": _render_menu_items(context.get("menus", []), str(context.get("page_key", ""))),
        "success_notice_html": _render_notice("success", context.get("success_message")),
        "error_notice_html": _render_notice("error", context.get("error_message")),
        "body_html": body_html,
        **_shared_assets_context(),
    }
    html = _render_template(_load_asset("layout.html"), layout_context)
    return HTMLResponse(content=html, status_code=status_code)


def render_public_page(template_name: str, context: dict[str, object], *, status_code: int = 200) -> HTMLResponse:
    merged_context = {**context, **_shared_assets_context()}
    html = _render_template(_load_asset(f"{template_name}.html"), merged_context)
    return HTMLResponse(content=html, status_code=status_code)


@lru_cache(maxsize=None)
def _load_asset(filename: str) -> str:
    return (TEMPLATE_ROOT / filename).read_text(encoding="utf-8")


def _shared_assets_context() -> dict[str, object]:
    return {
        "admin_theme_css": _load_asset("admin_theme.css"),
        "admin_theme_script": _load_asset("admin_theme.js"),
    }


def _render_template(template: str, context: dict[str, object]) -> str:
    rendered = _RAW_PATTERN.sub(lambda match: _stringify(context.get(match.group(1))), template)
    return _ESCAPED_PATTERN.sub(lambda match: escape(_stringify(context.get(match.group(1))), quote=True), rendered)


def _render_menu_items(menus: Iterable[dict[str, object]], page_key: str) -> str:
    return "".join(
        (
            '<li class="nav-item">'
            f'<a href="{escape(str(menu["href"]), quote=True)}"'
            f' class="{"active" if str(menu["code"]) == page_key else ""}">'
            f'<span>{escape(str(menu["label"]))}</span>'
            "</a>"
            "</li>"
        )
        for menu in menus
    )


def _render_notice(kind: str, message: object) -> str:
    if not message:
        return ""
    icon = "成功" if kind == "success" else "提示"
    return (
        f'<div class="notice {kind}">'
        f"<strong>{icon}</strong>"
        f"<span>{escape(str(message))}</span>"
        "</div>"
    )


def _build_page_context(page_name: str, context: dict[str, object]) -> dict[str, object]:
    builders = {
        "home": _build_home_context,
        "roles": _build_roles_context,
        "departments": _build_departments_context,
        "user_roles": _build_user_roles_context,
        "user_create": _build_user_create_context,
        "rooms": _build_rooms_context,
        "seats": _build_seats_context,
        "system_configs": _build_system_configs_context,
        "reservation_records": _build_reservation_records_context,
        "reservation_actions": _build_reservation_actions_context,
        "checkins": _build_checkins_context,
        "statistics": _build_statistics_context,
        "violations": _build_violations_context,
        "notifications": _build_notifications_context,
    }
    return builders[page_name](context)


def _build_home_context(context: dict[str, object]) -> dict[str, object]:
    shortcuts = list(context.get("shortcuts", []))
    shortcuts_html = "".join(
        (
            f'<a class="shortcut-card" href="{escape(str(shortcut["href"]), quote=True)}">'
            f"<strong>{escape(str(shortcut['label']))}</strong>"
            f"<span>{escape(str(shortcut['description']))}</span>"
            "</a>"
        )
        for shortcut in shortcuts
    )
    if not shortcuts_html:
        shortcuts_html = '<div class="empty-state">当前账号暂时没有可见的后台入口，请先确认权限配置。</div>'
    return {
        "hero_title": context["hero_title"],
        "hero_description": context["hero_description"],
        "shortcuts_html": shortcuts_html,
    }


def _build_roles_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    permissions = context["permissions"]
    roles = context["roles"]
    return {
        "role_count": context["role_count"],
        "active_role_count": context["active_role_count"],
        "inactive_role_count": context["inactive_role_count"],
        "permission_count": context["permission_count"],
        "create_name": create_form["name"],
        "create_code": create_form["code"],
        "create_description": create_form["description"],
        "create_is_active_checked": _checked(create_form["is_active"]),
        "create_permissions_html": _render_permission_options(permissions, set(create_form["permission_ids"])),
        "role_cards_html": _render_role_cards(roles),
        "edit_panel_html": _render_role_editor_panel(
            context["edit_form"],
            permissions,
            bool(context.get("selected_role_missing")),
        ),
        "target_lookup_value": context["target_lookup_value"],
        "permission_reference_html": _render_permission_reference(permissions),
    }


def _build_departments_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    department_cards_html = "".join(_render_department_card(department) for department in context["departments"])
    if not department_cards_html:
        department_cards_html = '<div class="empty-state">当前还没有院系，先从左侧表单创建一个。</div>'
    return {
        "department_count": context["department_count"],
        "active_department_count": context["active_department_count"],
        "inactive_department_count": context["inactive_department_count"],
        "create_name": create_form["name"],
        "create_code": create_form["code"],
        "create_active_toggle_html": _render_switch_field(
            "is_active",
            "创建后立即启用",
            "启用后会出现在用户创建和院系专属自习室的下拉列表中。",
            bool(create_form["is_active"]),
            data_purpose="immediate-activation",
        ),
        "department_cards_html": department_cards_html,
    }


def _render_department_card(department: dict[str, object]) -> str:
    return f"""
<article class="record-card">
  <div class="record-main">
    <div class="record-head">
      <div>
        <h4>{escape(str(department['name']))}</h4>
        <p class="muted"><code>{escape(str(department['code']))}</code></p>
      </div>
      <span class="status-badge{' inactive' if not department['is_active'] else ''}">{escape(str(department['status_label']))}</span>
    </div>
    <dl class="meta-list">
      <div><dt>院系 ID</dt><dd>{department['id']}</dd></div>
      <div><dt>院系编码</dt><dd>{escape(str(department['code']))}</dd></div>
    </dl>
  </div>
  <form method="post" action="/admin/departments/page" class="form-shell form-shell--compact">
    <input type="hidden" name="form_action" value="{escape(str(department['action']), quote=True)}">
    <input type="hidden" name="department_id" value="{department['id']}">
    <div class="form-actions">
      <button class="{escape(str(department['action_button_class']), quote=True)}" type="submit">{escape(str(department['action_label']))}</button>
    </div>
  </form>
</article>
"""


def _render_permission_options(
    permissions: list[dict[str, object]],
    selected_permission_ids: set[int],
) -> str:
    return "".join(
        (
            '<label class="selection-row">'
            f'<input type="checkbox" name="permission_ids" value="{permission["id"]}"'
            f'{_checked(int(permission["id"]) in selected_permission_ids)}>'
            '<span class="selection-copy">'
            f"<strong>{escape(str(permission['display_name']))}</strong>"
            f"<span>{escape(str(permission['display_description']))}</span>"
            "</span>"
            f"<code>{escape(str(permission['code']))}</code>"
            "</label>"
        )
        for permission in permissions
    )


def _render_role_cards(roles: list[dict[str, object]]) -> str:
    cards_html = "".join(_render_role_card(role) for role in roles)
    if cards_html:
        return cards_html
    return '<div class="empty-state">当前还没有角色，先从上方的创建表单开始。</div>'


def _render_role_card(role: dict[str, object]) -> str:
    permission_summary = "、".join(role["permission_display_names"]) if role["permission_display_names"] else "未配置权限"
    deactivate_action_html = (
        f"""
<form method="post" action="/admin/roles/page" class="form-shell form-shell--compact">
  <input type="hidden" name="form_action" value="deactivate">
  <input type="hidden" name="role_id" value="{role['id']}">
  <div class="form-actions"><button class="danger" type="submit">停用角色</button></div>
</form>
"""
        if role["is_active"]
        else '<p class="muted">该角色已停用，历史分配会保留，但不会继续生效。</p>'
    )
    delete_action_html = f"""
<form method="post" action="/admin/roles/page" class="form-shell form-shell--compact">
  <input type="hidden" name="form_action" value="delete">
  <input type="hidden" name="role_id" value="{role['id']}">
  <div class="form-actions"><button class="danger" type="submit">删除角色</button></div>
</form>
"""
    return f"""
<article class="record-card" data-role-card="true">
  <div class="record-main">
    <div class="record-head">
      <div>
        <h4>{escape(str(role['name']))}</h4>
        <p class="muted"><code>{escape(str(role['code']))}</code></p>
      </div>
      <span class="status-badge{' inactive' if not role['is_active'] else ''}">{escape(str(role['status_label']))}</span>
    </div>
    <p class="muted">{escape(str(role['description']))}</p>
    <dl class="meta-list">
      <div><dt>角色 ID</dt><dd>{role['id']}</dd></div>
      <div><dt>权限数量</dt><dd>{role['permission_count']} 项</dd></div>
      <div><dt>已含权限</dt><dd>{escape(permission_summary)}</dd></div>
    </dl>
  </div>
  <div class="actions">
    <a class="action-link secondary-link" href="/admin/roles?edit_role_id={role['id']}#role-editor">编辑角色</a>
  </div>
  {deactivate_action_html}
  {delete_action_html}
</article>
"""


def _render_role_editor_panel(
    edit_form: dict[str, object] | None,
    permissions: list[dict[str, object]],
    selected_role_missing: bool,
) -> str:
    if selected_role_missing:
        return '<div class="empty-state">没有找到要编辑的角色，请从左侧角色列表重新选择。</div>'
    if edit_form is None:
        return '<div class="empty-state">从左侧角色卡片点击“编辑角色”后，这里会出现独立的编辑表单。</div>'

    permission_options_html = _render_permission_options(permissions, set(edit_form["permission_ids"]))
    activation_switch = _render_switch_field(
        "is_active",
        "启用此角色",
        "停用后不会删除历史分配，但新权限不会继续生效。",
        bool(edit_form["is_active"]),
    )
    return f"""
<div class="panel-copy">
  <h3>编辑角色</h3>
  <p class="muted">在独立编辑区调整角色名称、编码、状态和权限组合，避免在列表里处理高密度表单。</p>
</div>
<form method="post" action="/admin/roles/page" id="role-editor-form" class="form-shell" data-form-variant="admin-shared">
  <input type="hidden" name="form_action" value="update">
  <input type="hidden" name="role_id" value="{escape(str(edit_form['role_id']), quote=True)}">
  <div class="fields">
    <label>角色名称<input name="name" value="{escape(str(edit_form['name']), quote=True)}" required></label>
    <label>角色编码<input name="code" value="{escape(str(edit_form['code']), quote=True)}" required></label>
    <label>角色说明<input name="description" value="{escape(str(edit_form['description']), quote=True)}"></label>
  </div>
  <div class="form-section">
    <div class="form-section-head">
      <div>
        <h4>角色状态</h4>
        <p>启用状态与权限组合分开处理，减少误操作。</p>
      </div>
    </div>
    {activation_switch}
  </div>
  <div class="form-section">
    <div class="form-section-head">
      <div>
        <h4>权限范围</h4>
        <p>只保留这个角色真正需要的权限，避免默认放大授权范围。</p>
      </div>
    </div>
    <div class="selection-list">{permission_options_html}</div>
  </div>
  <div class="form-actions"><button class="secondary" type="submit">保存角色设置</button></div>
</form>
"""


def _render_permission_reference(permissions: list[dict[str, object]]) -> str:
    return "".join(
        (
            '<article class="reference-row">'
            f"<strong>{escape(str(permission['display_name']))}</strong>"
            f"<p>{escape(str(permission['display_description']))}</p>"
            f"<code>{escape(str(permission['code']))}</code>"
            "</article>"
        )
        for permission in permissions
    )


def _build_user_roles_context(context: dict[str, object]) -> dict[str, object]:
    selected_role_ids = set(context.get("selected_role_ids", []))
    current_roles_html = "".join(
        (
            '<article class="reference-row">'
            f"<strong>{escape(str(role['name']))}</strong>"
            f"<p>{escape(str(role['description']))}</p>"
            f"<code>{escape(str(role['code']))}</code>"
            "</article>"
        )
        for role in context["current_roles"]
    )
    if not current_roles_html:
        current_roles_html = '<div class="empty-state">当前用户还没有分配任何角色。</div>'

    assignable_roles = context.get("assignable_roles", context["roles"])
    if context["target_user_exists"]:
        role_assignment_panel_html = f"""
<form method="post" action="/admin/users/{context['target_user_id']}/roles/page" class="form-shell" data-form-variant="admin-shared">
  <div class="selection-list">
    {_render_role_assignment_options(assignable_roles, selected_role_ids)}
  </div>
  <div class="form-actions"><button type="submit">保存角色分配</button></div>
</form>
"""
    else:
        role_assignment_panel_html = '<div class="empty-state">没有找到该用户，请返回角色管理页重新定位要分配的对象。</div>'

    return {
        "target_user_id": context["target_user_id"],
        "target_lookup_value": context["target_lookup_value"],
        "target_user_summary_html": _render_target_user_summary(context["target_user"]),
        "current_roles_html": current_roles_html,
        "role_assignment_panel_html": role_assignment_panel_html,
    }


def _build_user_create_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    created_user_summary = context.get("created_user")
    current_account_type = str(create_form["account_type"])
    is_student_account = current_account_type == "student"
    return {
        "current_account_type": current_account_type,
        "account_type_student_checked": _checked(str(create_form["account_type"]) == "student"),
        "account_type_admin_checked": _checked(str(create_form["account_type"]) == "admin"),
        "account_type_current_hint": (
            "当前要创建学生账号，请填写学生学号；管理员账号字段不会参与提交。"
            if is_student_account
            else "当前要创建管理员账号，请填写管理员登录标识；学生学号字段不会参与提交。"
        ),
        "student_identifier_state": "active" if is_student_account else "inactive",
        "admin_identifier_state": "inactive" if is_student_account else "active",
        "notification_email_state": "active" if is_student_account else "inactive",
        "student_group_hidden_attr": _bool_attr(not is_student_account, "hidden"),
        "admin_group_hidden_attr": _bool_attr(is_student_account, "hidden"),
        "notification_email_hidden_attr": _bool_attr(not is_student_account, "hidden"),
        "student_identifier_required_attr": _bool_attr(is_student_account, "required"),
        "admin_identifier_required_attr": _bool_attr(not is_student_account, "required"),
        "student_identifier_disabled_attr": _bool_attr(not is_student_account, "disabled"),
        "admin_identifier_disabled_attr": _bool_attr(is_student_account, "disabled"),
        "notification_email_disabled_attr": _bool_attr(not is_student_account, "disabled"),
        "create_name": create_form["name"],
        "create_student_no": create_form["student_no"],
        "create_email": create_form["email"],
        "create_notification_email": create_form["notification_email"],
        "create_password": create_form["password"],
        "create_department_options_html": _render_department_options(
            context["departments"],
            create_form["department_id"],
        ),
        "create_active_toggle_html": _render_switch_field(
            "is_active",
            "创建后立即启用",
            "保存后账号会直接进入可登录状态；管理员账号仍需后续分配角色才能进入后台。",
            bool(create_form["is_active"]),
            data_purpose="immediate-activation",
        ),
        "created_user_summary_html": _render_created_user_summary(created_user_summary),
    }


def _render_target_user_summary(target_user: dict[str, object]) -> str:
    notification_email_html = (
        f"<div><dt>通知邮箱</dt><dd>{escape(str(target_user['notification_email']))}</dd></div>"
        if target_user.get("show_notification_email")
        else ""
    )
    return f"""
<article class="record-card">
  <div class="record-main">
    <div class="record-head">
      <div>
        <h4>{escape(str(target_user['name']))}</h4>
        <p class="muted">用户 ID：{target_user['id']}</p>
      </div>
      <span class="status-badge{' inactive' if not target_user['is_active'] else ''}">{escape(str(target_user['status_label']))}</span>
    </div>
    <dl class="meta-list">
      <div><dt>{escape(str(target_user['login_label']))}</dt><dd>{escape(str(target_user['login_value']))}</dd></div>
      {notification_email_html}
      <div><dt>所属院系</dt><dd>{escape(str(target_user['department_name']))}</dd></div>
      <div><dt>当前角色数</dt><dd>{target_user['role_count']} 项</dd></div>
    </dl>
  </div>
</article>
"""


def _render_created_user_summary(created_user: dict[str, object] | None) -> str:
    if created_user is None:
        return ""
    next_step_html = (
        '<div class="actions">'
        f'<a class="action-link" href="{escape(str(created_user["role_assignment_href"]), quote=True)}">'
        "继续分配管理员角色"
        "</a>"
        '<a class="action-link secondary-link" href="/admin/roles#user-role-entry">'
        "返回角色分配工作台"
        "</a>"
        "</div>"
        if created_user.get("show_role_assignment_hint")
        else '<div class="actions"><a class="action-link secondary-link" href="/admin">返回管理首页</a></div>'
    )
    notification_email_html = (
        f"<div><dt>通知邮箱</dt><dd>{escape(str(created_user['notification_email']))}</dd></div>"
        if created_user.get("show_notification_email")
        else ""
    )
    return f"""
<article class="record-card" data-created-user-summary="true">
  <div class="record-main">
    <div class="record-head">
      <div>
        <h4>{escape(str(created_user['name']))}</h4>
        <p class="muted">{escape(str(created_user['account_type_label']))}</p>
      </div>
      <span class="status-badge{' inactive' if str(created_user['status_label']) != '启用中' else ''}">{escape(str(created_user['status_label']))}</span>
    </div>
    <dl class="meta-list">
      <div><dt>用户 ID</dt><dd>{created_user['id']}</dd></div>
      <div><dt>{escape(str(created_user['login_label']))}</dt><dd>{escape(str(created_user['login_value']))}</dd></div>
      {notification_email_html}
      <div><dt>所属院系</dt><dd>{escape(str(created_user['department_name']))}</dd></div>
    </dl>
    <p class="muted">系统只会保存密码哈希，创建成功后不会返回原始密码。</p>
    <p class="muted">{escape(str(created_user['next_step_message']))}</p>
  </div>
  {next_step_html}
</article>
"""


def _render_role_assignment_options(
    roles: list[dict[str, object]],
    selected_role_ids: set[int],
) -> str:
    return "".join(
        (
            '<label class="selection-row">'
            f'<input type="checkbox" name="role_ids" value="{role["id"]}"'
            f'{_checked(int(role["id"]) in selected_role_ids)}>'
            '<span class="selection-copy">'
            f"<strong>{escape(str(role['name']))}</strong>"
            f"<span>{escape(str(role['description']))}</span>"
            "</span>"
            f"<code>{escape(str(role['code']))}</code>"
            "</label>"
        )
        for role in roles
    )


def _build_rooms_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    room_cards_html = "".join(_render_room_card(room, context["departments"]) for room in context["rooms"])
    if not room_cards_html:
        room_cards_html = '<div class="empty-state">当前还没有自习室，先从左侧表单创建一个。</div>'
    return {
        "create_name": create_form["name"],
        "create_location": create_form["location"],
        "create_scope_options_html": _render_scope_options(str(create_form["access_scope"])),
        "create_department_options_html": _render_department_options(context["departments"], create_form["department_id"]),
        "create_open_time": create_form["open_time"],
        "create_close_time": create_form["close_time"],
        "create_active_checked": _checked(create_form["is_active"]),
        "room_count": context["room_count"],
        "active_room_count": context["active_room_count"],
        "department_only_room_count": context["department_only_room_count"],
        "room_cards_html": room_cards_html,
    }


def _render_room_card(room: dict[str, object], departments: list[dict[str, object]]) -> str:
    activation_switch = _render_switch_field(
        "is_active",
        "保持启用",
        "停用后不会删除自习室记录，但不会继续对外开放。",
        bool(room["is_active"]),
    )
    return f"""
<details class="item-card">
  <summary>
    <div class="item-summary">
      <div>
        <strong>{escape(str(room['name']))}</strong>
        <p>{escape(str(room['location']))}</p>
      </div>
      <div class="chip-row">
        <span class="chip">{escape(str(room['scope_label']))}</span>
        <span class="chip">{escape(str(room['department_label']))}</span>
        <span class="chip">{escape(str(room['status_label']))}</span>
        <span class="chip">{escape(str(room['open_time_text']))} - {escape(str(room['close_time_text']))}</span>
      </div>
    </div>
  </summary>
  <div class="details-body">
    <form method="post" action="/admin/rooms/page" data-room-form="true" class="form-shell" data-form-variant="admin-shared">
      <input type="hidden" name="form_action" value="update">
      <input type="hidden" name="room_id" value="{room['id']}">
      <div class="fields">
        <label>自习室名称<input name="name" value="{escape(str(room['name']), quote=True)}"></label>
        <label>位置说明<input name="location" value="{escape(str(room['location']), quote=True)}"></label>
        <label>开放范围<select name="access_scope">{_render_scope_options(str(room['access_scope']))}</select></label>
        <label data-department-field>所属院系<select name="department_id">{_render_department_options(departments, room['department_id'])}</select></label>
        <label>开放时间<input type="time" step="60" name="open_time" value="{escape(str(room['open_time_text']), quote=True)}"></label>
        <label>关闭时间<input type="time" step="60" name="close_time" value="{escape(str(room['close_time_text']), quote=True)}"></label>
      </div>
      <div class="form-section">{activation_switch}</div>
      <div class="form-actions">
        <button class="secondary" type="submit">保存修改</button>
      </div>
    </form>
    <form method="post" action="/admin/rooms/page" class="form-shell form-shell--compact">
      <input type="hidden" name="form_action" value="deactivate">
      <input type="hidden" name="room_id" value="{room['id']}">
      <div class="form-actions"><button class="danger" type="submit">停用自习室</button></div>
    </form>
  </div>
</details>
"""


def _build_seats_context(context: dict[str, object]) -> dict[str, object]:
    create_form = context["create_form"]
    selected_room_id = context.get("selected_room_id")
    selected_room_text = "" if selected_room_id is None else str(selected_room_id)
    seat_cards_html = "".join(_render_seat_card(seat, context["rooms"], selected_room_text) for seat in context["seats"])
    if not seat_cards_html:
        seat_cards_html = '<div class="empty-state">当前筛选范围内还没有座位，可以先创建一条记录。</div>'
    return {
        "filter_room_options_html": _render_room_options(context["rooms"], selected_room_text, include_all=True),
        "create_room_options_html": _render_room_options(context["rooms"], str(create_form["room_id"])),
        "create_seat_code": create_form["seat_code"],
        "create_seat_label": create_form["seat_label"],
        "create_active_toggle_html": _render_switch_field(
            "is_active",
            "创建后立即启用",
            "保存后会直接进入可用状态，适合已经准备开放的座位。",
            bool(create_form["is_active"]),
            data_purpose="immediate-activation",
        ),
        "create_attribute_toggles_html": _render_seat_attribute_toggles(create_form),
        "selected_room_id": selected_room_text,
        "selected_room_label": context["selected_room_label"],
        "seat_count": context["seat_count"],
        "active_seat_count": context["active_seat_count"],
        "window_seat_count": context["window_seat_count"],
        "seat_cards_html": seat_cards_html,
    }


def _render_seat_card(seat: dict[str, object], rooms: list[dict[str, object]], selected_room_id: str) -> str:
    room_options_html = _render_room_options(rooms, str(seat["room_id"]))
    attribute_chips = "".join(f'<span class="chip">{escape(str(label))}</span>' for label in seat["attribute_labels"])
    activation_switch = _render_switch_field(
        "is_active",
        "保持启用",
        "停用后座位会保留在列表里，但不会继续对外开放。",
        bool(seat["is_active"]),
    )
    attribute_toggles = _render_seat_attribute_toggles(
        {
            "is_window_side": seat["is_window_side"],
            "has_power_socket": seat["has_power_socket"],
            "has_track_socket": seat["has_track_socket"],
        }
    )
    return f"""
<details class="item-card">
  <summary>
    <div class="item-summary">
      <div>
        <strong>{escape(str(seat['seat_label']))}</strong>
        <p><code>{escape(str(seat['seat_code']))}</code> · {escape(str(seat['room_name']))}</p>
      </div>
      <div class="chip-row">
        <span class="chip">{escape(str(seat['status_label']))}</span>
        {attribute_chips}
      </div>
    </div>
  </summary>
  <div class="details-body">
    <p class="muted">所属自习室：{escape(str(seat['room_name']))} {escape(str(seat.get('room_location') or ''))}</p>
    <form method="post" action="/admin/seats/page" class="form-shell" data-form-variant="admin-shared">
      <input type="hidden" name="form_action" value="update">
      <input type="hidden" name="seat_id" value="{seat['id']}">
      <input type="hidden" name="filter_room_id" value="{escape(selected_room_id, quote=True)}">
      <div class="fields">
        <label>所属自习室<select name="room_id">{room_options_html}</select></label>
        <label>座位编号<input name="seat_code" value="{escape(str(seat['seat_code']), quote=True)}"></label>
        <label>座位名称<input name="seat_label" value="{escape(str(seat['seat_label']), quote=True)}"></label>
      </div>
      <div class="form-section">
        <div class="form-section-head">
          <div>
            <h4>开放状态</h4>
            <p>把启用状态与属性标注分开，避免同一块里堆太多不同语义的控件。</p>
          </div>
        </div>
        {activation_switch}
      </div>
      <div class="form-section">
        <div class="form-section-head">
          <div>
            <h4>座位属性</h4>
            <p>统一使用轻量开关组件，便于快速确认当前标注。</p>
          </div>
        </div>
        <div class="toggle-grid" data-toggle-group="seat-attributes">{attribute_toggles}</div>
      </div>
      <div class="form-actions"><button class="secondary" type="submit">保存修改</button></div>
    </form>
    <form method="post" action="/admin/seats/page" class="form-shell form-shell--compact">
      <input type="hidden" name="form_action" value="deactivate">
      <input type="hidden" name="seat_id" value="{seat['id']}">
      <input type="hidden" name="filter_room_id" value="{escape(selected_room_id, quote=True)}">
      <div class="form-actions"><button class="danger" type="submit">停用座位</button></div>
    </form>
  </div>
</details>
"""


def _render_seat_attribute_toggles(values: dict[str, object]) -> str:
    return "".join(
        (
            _render_toggle_card(
                name,
                label,
                description,
                bool(values.get(name)),
            )
            for name, label, description in (
                ("is_window_side", "靠窗", "用于标注采光更好的位置，方便管理员维护偏好信息。"),
                ("has_power_socket", "固定插座", "标记座位旁是否有固定电源插口。"),
                ("has_track_socket", "移动导轨插座", "标记是否配置了可移动导轨或轨道电源。"),
            )
        )
    )


def _render_switch_field(
    name: str,
    label: str,
    description: str,
    checked: bool,
    *,
    data_purpose: str | None = None,
) -> str:
    purpose_attr = f' data-switch-purpose="{escape(data_purpose, quote=True)}"' if data_purpose else ""
    return (
        f'<label class="switch-field" data-switch-style="compact"{purpose_attr}>'
        f'<input type="checkbox" name="{escape(name, quote=True)}"{_checked(checked)}>'
        '<span class="switch-ui" aria-hidden="true"></span>'
        '<span class="switch-copy">'
        f"<strong>{escape(label)}</strong>"
        f"<span>{escape(description)}</span>"
        "</span>"
        "</label>"
    )


def _render_toggle_card(name: str, label: str, description: str, checked: bool) -> str:
    return (
        '<label class="toggle-card">'
        f'<input type="checkbox" name="{escape(name, quote=True)}"{_checked(checked)}>'
        '<span class="toggle-card__indicator" aria-hidden="true"></span>'
        '<span class="toggle-card__copy">'
        f"<strong>{escape(label)}</strong>"
        f"<span>{escape(description)}</span>"
        "</span>"
        "</label>"
    )


def _render_scope_options(selected_scope: str) -> str:
    return "".join(
        (
            f'<option value="{value}"{_selected(value == selected_scope)}>{label}</option>'
            for value, label in (("public", "公共开放"), ("department", "院系专属"))
        )
    )


def _render_department_options(
    departments: Iterable[dict[str, object]],
    selected_department_id: object,
) -> str:
    selected_text = str(selected_department_id or "")
    options = [f'<option value=""{_selected(selected_text == "")}>请选择院系</option>']
    found = selected_text == ""
    for department in departments:
        department_id = str(department["id"])
        found = found or department_id == selected_text
        options.append(
            f'<option value="{escape(department_id, quote=True)}"{_selected(department_id == selected_text)}>'
            f"{escape(str(department['name']))}（{escape(str(department['code']))}）</option>"
        )
    if selected_text and not found:
        options.append(
            f'<option value="{escape(selected_text, quote=True)}" selected>当前选择无效（ID {escape(selected_text)}）</option>'
        )
    return "".join(options)


def _render_room_options(
    rooms: Iterable[dict[str, object]],
    selected_room_id: str,
    *,
    include_all: bool = False,
) -> str:
    options: list[str] = []
    if include_all:
        options.append(f'<option value=""{_selected(selected_room_id == "")}>全部自习室</option>')
    for room in rooms:
        room_id = str(room["id"])
        options.append(
            f'<option value="{escape(room_id, quote=True)}"{_selected(room_id == selected_room_id)}>'
            f"{escape(str(room['name']))} · {escape(str(room['location']))}</option>"
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
    <form method="post" action="/admin/system-configs/page" class="form-shell form-shell--compact">
      <input type="hidden" name="config_key" value="{escape(str(config['config_key']), quote=True)}">
      <label>新值<input name="config_value" value="{escape(str(config['config_value']), quote=True)}"></label>
      <div class="form-actions"><button type="submit">更新参数</button></div>
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
        "create_result_html": _render_reservation_result("最近一次创建结果", create_result),
        "cancel_result_html": _render_reservation_result("最近一次取消结果", cancel_result),
    }


def _render_reservation_result(title: str, payload: dict[str, object] | None) -> str:
    if not payload:
        return ""
    return (
        f'<p class="muted">{escape(title)}：reservation_id={payload["reservation_id"]}，'
        f'状态 {escape(str(payload["status"]))}</p>'
    )


def _build_checkins_context(context: dict[str, object]) -> dict[str, object]:
    selected_room_id = _optional(context.get("selected_room_id"))
    current_code_html = _render_dynamic_checkin_code(context.get("current_code"))
    records_html = "".join(
        f"""
<tr>
  <td>{item['checkin_record_id']}</td>
  <td>{item['reservation_id']}</td>
  <td>{item['user_id']}<br><span class="muted">{escape(str(item.get('student_no') or '未记录学号'))}</span></td>
  <td>{item['room_id']}</td>
  <td>{item['seat_id']}</td>
  <td><code>{escape(str(item['checkin_method']))}</code></td>
  <td>{escape(str(item['checkin_at']))}</td>
</tr>
"""
        for item in context["checkin_records"]
    )
    if not records_html:
        records_html = '<tr><td colspan="7" class="muted">当前条件下没有签到记录。</td></tr>'
    return {
        "room_options_html": _render_simple_room_options(context["rooms"], selected_room_id),
        "filter_room_id": selected_room_id,
        "filter_date_from": _optional(context.get("date_from")),
        "filter_date_to": _optional(context.get("date_to")),
        "filter_page": _optional(context.get("page")),
        "filter_page_size": _optional(context.get("page_size")),
        "checkin_code_html": current_code_html,
        "checkin_records_total": context["checkin_total"],
        "checkin_record_rows_html": records_html,
    }


def _render_dynamic_checkin_code(payload: object) -> str:
    if not isinstance(payload, dict):
        return '<p class="muted">请选择自习室查看当前 5 分钟动态签到码状态。</p>'
    return (
        f'<div class="result-box">'
        f'<strong>当前动态签到码</strong>'
        f'<p>自习室 ID：{escape(str(payload["room_id"]))}</p>'
        f'<p>动态码：<code>{escape(str(payload["code"]))}</code></p>'
        f'<p>时间片开始：{escape(str(payload["time_slice_start"]))}</p>'
        f'<p>有效至：{escape(str(payload["expires_at"]))}</p>'
        f'<p class="muted">剩余约 {escape(str(payload["remaining_seconds"]))} 秒，服务端会按 5 分钟时间片自动轮换。</p>'
        f'</div>'
    )


def _render_simple_room_options(rooms: Iterable[dict[str, object]], selected_room_id: str) -> str:
    options = [f'<option value=""{_selected(selected_room_id == "")}>请选择自习室</option>']
    for room in rooms:
        room_id = str(room["id"])
        options.append(
            f'<option value="{escape(room_id, quote=True)}"{_selected(room_id == selected_room_id)}>'
            f'{escape(str(room["name"]))}</option>'
        )
    return "".join(options)


def _build_violations_context(context: dict[str, object]) -> dict[str, object]:
    filters = context["filters"]
    user_summary = context.get("user_summary")
    can_manage_manual_blocks = bool(context.get("can_manage_manual_blocks"))
    violation_rows_html = "".join(
        f"""
<tr>
  <td>{item['violation_id']}</td>
  <td>{item['user_id']}<br><span class="muted">{escape(str(item.get('student_no') or '未记录学号'))}</span></td>
  <td>{item['reservation_id']}</td>
  <td>{item['room_id']}</td>
  <td><code>{escape(str(item['violation_type']))}</code></td>
  <td>{escape(str(item['occurred_at']))}</td>
</tr>
"""
        for item in context["violations"]
    )
    if not violation_rows_html:
        violation_rows_html = '<tr><td colspan="6" class="muted">当前条件下没有查询到违约记录。</td></tr>'
    return {
        "filter_user_id": _optional(filters.get("user_id")),
        "filter_student_no": _optional(filters.get("student_no")),
        "filter_room_id": _optional(filters.get("room_id")),
        "filter_date_from": _optional(filters.get("date_from")),
        "filter_date_to": _optional(filters.get("date_to")),
        "filter_page": _optional(filters.get("page")),
        "filter_page_size": _optional(filters.get("page_size")),
        "violations_total": context["total"],
        "violation_rows_html": violation_rows_html,
        "user_summary_html": _render_violation_user_summary(user_summary, can_manage_manual_blocks),
    }


def _render_violation_user_summary(summary: object, can_manage_manual_blocks: bool) -> str:
    if not isinstance(summary, dict):
        return '<p class="muted">输入用户 ID 或学生学号后显示单用户违约次数和预约限制状态。</p>'

    user_id = int(summary["user_id"])
    is_penalized = bool(summary["is_penalized"])
    status_label = "限制中" if is_penalized else "未限制"
    source_label = _restriction_source_label(str(summary["restriction_source"]))
    details = [
        ("用户 ID", str(summary["user_id"])),
        ("学生学号", str(summary.get("student_no") or "未记录")),
        ("违约次数", str(summary["violation_count"])),
        ("预约限制", status_label),
        ("限制来源", source_label),
    ]
    if summary.get("penalty_start") or summary.get("penalty_end"):
        details.append(("自动惩罚期", f"{_optional(summary.get('penalty_start'))} 至 {_optional(summary.get('penalty_end'))}"))
    if summary.get("manual_block_id"):
        details.append(("手动限制", f"#{summary['manual_block_id']}"))
    if summary.get("manual_block_reason"):
        details.append(("限制原因", str(summary["manual_block_reason"])))
    if summary.get("manual_block_started_at"):
        details.append(("开启时间", str(summary["manual_block_started_at"])))

    detail_html = "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
        for label, value in details
    )
    actions_html = _render_manual_block_actions(summary, can_manage_manual_blocks, user_id)
    return f"""
<div class="result-box">
  <dl class="metric-grid">{detail_html}</dl>
  {actions_html}
</div>
"""


def _render_manual_block_actions(summary: dict[str, object], can_manage_manual_blocks: bool, user_id: int) -> str:
    if not can_manage_manual_blocks:
        return ""
    if summary.get("manual_block_id"):
        return f"""
<form method="post" action="/admin/violations/users/{user_id}/manual-block/release" class="form-shell form-shell--compact">
  <div class="form-actions"><button class="secondary" type="submit">解除手动限制</button></div>
</form>
"""
    return f"""
<form method="post" action="/admin/violations/users/{user_id}/manual-block" class="form-shell form-shell--compact">
  <label>限制原因<input name="reason" required></label>
  <div class="form-actions"><button class="secondary" type="submit">开启手动限制</button></div>
</form>
"""


def _restriction_source_label(value: str) -> str:
    labels = {
        "NONE": "无",
        "AUTO_VIOLATION": "自动违约惩罚",
        "MANUAL_BLOCK": "手动限制",
        "AUTO_AND_MANUAL": "自动违约惩罚 + 手动限制",
    }
    return labels.get(value, value)


def _build_notifications_context(context: dict[str, object]) -> dict[str, object]:
    filters = context["filters"]
    log_rows_html = "".join(
        f"""
<tr>
  <td>{item['notification_log_id']}</td>
  <td>{item['reservation_id']}</td>
  <td>{item['user_id']}</td>
  <td><code>{escape(str(item['notification_type']))}</code></td>
  <td>{escape(str(item['channel']))}</td>
  <td><code>{escape(str(item['status']))}</code></td>
  <td>{escape(str(item['sent_at']))}</td>
  <td>{escape(str(item.get('message') or ''))}</td>
</tr>
"""
        for item in context["logs"]
    )
    if not log_rows_html:
        log_rows_html = '<tr><td colspan="8" class="muted">当前条件下没有通知日志。</td></tr>'
    return {
        "notification_default_channel": context["notification_default_channel"],
        "smtp_host": context["smtp_host"],
        "filter_reservation_id": _optional(filters.get("reservation_id")),
        "filter_notification_type": _optional(filters.get("notification_type")),
        "filter_status": _optional(filters.get("status")),
        "filter_page": _optional(filters.get("page")),
        "filter_page_size": _optional(filters.get("page_size")),
        "notification_type_options_html": _render_notification_type_options(_optional(filters.get("notification_type"))),
        "status_options_html": _render_notification_status_options(_optional(filters.get("status"))),
        "notification_logs_total": context["total"],
        "notification_log_rows_html": log_rows_html,
        "task_scheduler_enabled_label": "已启用" if context["task_scheduler_enabled"] else "已关闭",
        "task_scheduler_interval_seconds": context["task_scheduler_interval_seconds"],
    }


def _render_notification_type_options(selected_value: str) -> str:
    values = [
        ("", "全部类型"),
        ("RESERVATION_REMINDER", "预约前提醒"),
        ("NO_SHOW_REMINDER", "未签到提醒"),
        ("AUTO_CANCEL_NOTICE", "超时未签到释放通知"),
    ]
    return "".join(
        f'<option value="{escape(value, quote=True)}"{_selected(value == selected_value)}>{escape(label)}</option>'
        for value, label in values
    )


def _render_notification_status_options(selected_value: str) -> str:
    values = [
        ("", "全部状态"),
        ("PENDING", "PENDING"),
        ("SENT", "SENT"),
        ("FAILED", "FAILED"),
    ]
    return "".join(
        f'<option value="{escape(value, quote=True)}"{_selected(value == selected_value)}>{escape(label)}</option>'
        for value, label in values
    )

def _checked(value: bool) -> str:
    return " checked" if value else ""


def _bool_attr(value: bool, attr_name: str) -> str:
    return f" {attr_name}" if value else ""


def _selected(value: bool) -> str:
    return " selected" if value else ""


def _optional(value: object) -> str:
    return "" if value is None else str(value)


def _stringify(value: object) -> str:
    return "" if value is None else str(value)


def _build_reservation_records_context(context: dict[str, object]) -> dict[str, object]:
    filters = context["filters"]
    reservation_rows_html = "".join(
        f"""
<tr>
  <td>{item['reservation_id']}</td>
  <td>{item['user_id']}</td>
  <td>{item['room_id']}</td>
  <td>{item['seat_id']}</td>
  <td><code>{escape(str(item['status']))}</code></td>
  <td>{escape(str(item['start_time']))}</td>
  <td>{escape(str(item['end_time']))}</td>
  <td>{escape(str(item['created_by']))}</td>
</tr>
"""
        for item in context["reservations"]
    )
    if not reservation_rows_html:
        reservation_rows_html = '<tr><td colspan="8" class="muted">当前条件下没有查询到预约记录。</td></tr>'
    return {
        "filter_user_id": _optional(filters.get("user_id")),
        "filter_room_id": _optional(filters.get("room_id")),
        "filter_seat_id": _optional(filters.get("seat_id")),
        "filter_status_options_html": _render_reservation_status_options(filters.get("status")),
        "filter_date_from": _optional(filters.get("date_from")),
        "filter_date_to": _optional(filters.get("date_to")),
        "filter_page": _optional(filters.get("page")),
        "filter_page_size": _optional(filters.get("page_size")),
        "reservations_total": context["total"],
        "reservation_rows_html": reservation_rows_html,
    }


def _render_reservation_status_options(selected_status: object) -> str:
    selected_text = str(selected_status or "")
    options = [
        ("", "全部状态"),
        ("BOOKED", "已预约"),
        ("CHECKED_IN", "已签到"),
        ("CANCELLED", "已取消"),
        ("EXPIRED", "已过期"),
    ]
    return "".join(
        f'<option value="{value}"{_selected(value == selected_text)}>{label}</option>'
        for value, label in options
    )


def _build_statistics_context(context: dict[str, object]) -> dict[str, object]:
    filters = context["filters"]
    room_rows_html = "".join(
        f"""
<tr>
  <td>{item['room_id']}</td>
  <td>{escape(str(item['room_name']))}</td>
  <td>{item['usage_rate']}</td>
</tr>
"""
        for item in context["rooms"]
    )
    if not room_rows_html:
        room_rows_html = '<tr><td colspan="3" class="muted">当前日期范围内没有房间统计结果。</td></tr>'

    seat_rows_html = "".join(
        f"""
<tr>
  <td>{item['seat_id']}</td>
  <td>{escape(str(item['seat_code']))}</td>
  <td>{item['room_id']}</td>
  <td>{item['usage_rate']}</td>
</tr>
"""
        for item in context["seats"]
    )
    if not seat_rows_html:
        seat_rows_html = '<tr><td colspan="4" class="muted">当前日期范围内没有座位统计结果。</td></tr>'

    overview = context["overview"]
    return {
        "filter_date_from": _optional(filters.get("date_from")),
        "filter_date_to": _optional(filters.get("date_to")),
        "overview_reserved_minutes": overview["total_reserved_minutes"],
        "overview_violation_count": overview["total_violation_count"],
        "overview_violation_rate": overview["overall_violation_rate"],
        "room_rows_html": room_rows_html,
        "seat_rows_html": seat_rows_html,
    }
