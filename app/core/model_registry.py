from __future__ import annotations


def import_all_models() -> None:
    from app.modules.checkin.models import checkin_code, checkin_record  # noqa: F401
    from app.modules.identity.models import department, permission, role, role_permission, user, user_role  # noqa: F401
    from app.modules.notification.models import notification_log  # noqa: F401
    from app.modules.reservation.models import reservation  # noqa: F401
    from app.modules.resource.models import seat, study_room  # noqa: F401
    from app.modules.system_config.models import system_config  # noqa: F401
    from app.modules.violation.models import user_reservation_block, violation_record  # noqa: F401
