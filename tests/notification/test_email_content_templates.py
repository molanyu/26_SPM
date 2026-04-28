from __future__ import annotations

from datetime import datetime, timedelta, time

from app.core.config import Settings
from app.core.database import SessionLocal
from app.modules.identity.schemas.user import UserCreateRequest
from app.modules.identity.services.user_service import UserService
from app.modules.notification.services.reminder_service import ReminderService
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_EXPIRED,
    Reservation,
)
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


class FakeEmailSender:
    def __init__(self) -> None:
        self.deliveries: list[dict[str, str]] = []

    def send_email(self, *, to_email: str, subject: str, body: str) -> None:
        self.deliveries.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
            }
        )


def _build_smtp_settings() -> Settings:
    return Settings(
        notification_default_channel="smtp_email",
        smtp_host="smtp.example.com",
        smtp_port="587",
        smtp_from_email="noreply@example.com",
        smtp_use_tls=True,
        smtp_timeout_seconds="10",
    )


def _create_student_with_notification_email(seed_data: dict) -> int:
    with SessionLocal() as session:
        created_student = UserService(session).create_user(
            UserCreateRequest(
                account_type="student",
                name="Template Student",
                student_no="20249992",
                notification_email="template.student@example.com",
                password="template-student-pass",
                department_id=seed_data["departments"]["cs"],
            )
        )
        return created_student.id


def _seed_template_reservations(seed_data: dict, *, user_id: int, now: datetime) -> dict[str, tuple[int, datetime, datetime]]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Email Template Room",
            location="Engineering 906",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()

        reminder_seat = Seat(
            room_id=room.id,
            seat_code="ET-01",
            seat_label="Reminder Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        no_show_seat = Seat(
            room_id=room.id,
            seat_code="ET-02",
            seat_label="No Show Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        expired_seat = Seat(
            room_id=room.id,
            seat_code="ET-03",
            seat_label="Expired Seat",
            is_active=True,
            is_window_side=False,
            has_power_socket=True,
            has_track_socket=False,
        )
        session.add_all([reminder_seat, no_show_seat, expired_seat])
        session.flush()

        reminder_start = now + timedelta(minutes=15)
        reminder_end = reminder_start + timedelta(hours=1)
        no_show_start = now - timedelta(minutes=10)
        no_show_end = no_show_start + timedelta(hours=1)
        expired_start = now - timedelta(hours=2)
        expired_end = now - timedelta(hours=1)

        reminder_reservation = Reservation(
            user_id=user_id,
            seat_id=reminder_seat.id,
            room_id=room.id,
            start_time=reminder_start,
            end_time=reminder_end,
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        no_show_reservation = Reservation(
            user_id=user_id,
            seat_id=no_show_seat.id,
            room_id=room.id,
            start_time=no_show_start,
            end_time=no_show_end,
            status=RESERVATION_STATUS_BOOKED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        expired_reservation = Reservation(
            user_id=user_id,
            seat_id=expired_seat.id,
            room_id=room.id,
            start_time=expired_start,
            end_time=expired_end,
            status=RESERVATION_STATUS_EXPIRED,
            created_by=RESERVATION_SOURCE_STUDENT,
            cancelled_by=None,
            cancel_reason=None,
        )
        session.add_all([reminder_reservation, no_show_reservation, expired_reservation])
        session.commit()
        return {
            "reservation_reminder": (reminder_reservation.id, reminder_start, reminder_end),
            "no_show_reminder": (no_show_reservation.id, no_show_start, no_show_end),
            "auto_cancel_notice": (expired_reservation.id, expired_start, expired_end),
        }


def _assert_common_email_body(
    body: str,
    *,
    reservation_id: int,
    room_name: str,
    seat_text: str,
    start_time: datetime,
    end_time: datetime,
) -> None:
    assert "Reservation " not in body, "邮件正文不应再使用英文调试文案。"
    assert "starts at" not in body, "预约开始提醒正文不应包含旧英文模板。"
    assert "awaiting check-in" not in body, "未签到提醒正文不应包含旧英文模板。"
    assert f"预约 ID：{reservation_id}" in body
    assert f"自习室：{room_name}" in body
    assert f"座位：{seat_text}" in body
    assert f"开始时间：{start_time.strftime('%Y-%m-%d %H:%M')}" in body
    assert f"结束时间：{end_time.strftime('%Y-%m-%d %H:%M')}" in body


def test_reminder_smtp_email_templates_are_user_facing_chinese(seed_data: dict) -> None:
    now = datetime(2026, 4, 27, 9, 0)
    user_id = _create_student_with_notification_email(seed_data)
    reservations = _seed_template_reservations(seed_data, user_id=user_id, now=now)
    fake_sender = FakeEmailSender()

    with SessionLocal() as session:
        service = ReminderService(
            session,
            settings=_build_smtp_settings(),
            email_sender=fake_sender,
        )
        reservation_result = service.send_reservation_reminders(now=now)
        no_show_result = service.send_no_show_reminders(now=now)
        auto_cancel_result = service.send_auto_cancel_notifications(now=now)

    assert reservation_result.sent_reservation_ids == [reservations["reservation_reminder"][0]]
    assert no_show_result.sent_reservation_ids == [reservations["no_show_reminder"][0]]
    assert auto_cancel_result.sent_reservation_ids == [reservations["auto_cancel_notice"][0]]
    assert len(fake_sender.deliveries) == 3
    assert {delivery["to_email"] for delivery in fake_sender.deliveries} == {"template.student@example.com"}

    deliveries_by_subject = {delivery["subject"]: delivery["body"] for delivery in fake_sender.deliveries}
    assert set(deliveries_by_subject) == {
        "自习室预约即将开始提醒",
        "自习室预约未签到提醒",
        "自习室预约自动取消通知",
    }

    reservation_id, start_time, end_time = reservations["reservation_reminder"]
    reminder_body = deliveries_by_subject["自习室预约即将开始提醒"]
    assert "即将开始" in reminder_body
    _assert_common_email_body(
        reminder_body,
        reservation_id=reservation_id,
        room_name="Email Template Room",
        seat_text="Reminder Seat（ET-01）",
        start_time=start_time,
        end_time=end_time,
    )

    reservation_id, start_time, end_time = reservations["no_show_reminder"]
    no_show_body = deliveries_by_subject["自习室预约未签到提醒"]
    assert "尚未记录签到" in no_show_body
    _assert_common_email_body(
        no_show_body,
        reservation_id=reservation_id,
        room_name="Email Template Room",
        seat_text="No Show Seat（ET-02）",
        start_time=start_time,
        end_time=end_time,
    )

    reservation_id, start_time, end_time = reservations["auto_cancel_notice"]
    auto_cancel_body = deliveries_by_subject["自习室预约自动取消通知"]
    assert "自动取消" in auto_cancel_body
    assert "座位已释放" in auto_cancel_body
    _assert_common_email_body(
        auto_cancel_body,
        reservation_id=reservation_id,
        room_name="Email Template Room",
        seat_text="Expired Seat（ET-03）",
        start_time=start_time,
        end_time=end_time,
    )
