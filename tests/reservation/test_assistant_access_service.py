from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from datetime import time
from datetime import timedelta

from app.core.database import SessionLocal
from app.modules.reservation.models.reservation import (
    RESERVATION_SOURCE_STUDENT,
    RESERVATION_STATUS_BOOKED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_CHECKED_IN,
    Reservation,
)
from app.modules.reservation.services.assistant_access_service import AssistantReservationService
from app.modules.resource.models.seat import Seat
from app.modules.resource.models.study_room import StudyRoom


def _seed_room_and_seats(seed_data: dict) -> dict[str, int]:
    with SessionLocal() as session:
        room = StudyRoom(
            name="Assistant Access Room",
            location="Engineering 801",
            department_id=seed_data["departments"]["cs"],
            is_department_only=True,
            is_active=True,
            open_time=time(8, 0),
            close_time=time(22, 0),
        )
        session.add(room)
        session.flush()
        seats = [
            Seat(
                room_id=room.id,
                seat_code="A-01",
                seat_label="Seat 1",
                is_active=True,
                is_window_side=False,
                has_power_socket=False,
                has_track_socket=False,
            ),
            Seat(
                room_id=room.id,
                seat_code="A-02",
                seat_label="Seat 2",
                is_active=True,
                is_window_side=False,
                has_power_socket=False,
                has_track_socket=False,
            ),
            Seat(
                room_id=room.id,
                seat_code="A-03",
                seat_label="Seat 3",
                is_active=True,
                is_window_side=False,
                has_power_socket=False,
                has_track_socket=False,
            ),
        ]
        session.add_all(seats)
        session.commit()
        return {
            "room_id": room.id,
            "seat_booked": seats[0].id,
            "seat_checked_in": seats[1].id,
            "seat_cancelled": seats[2].id,
        }


def _insert_reservation(
    *,
    user_id: int,
    room_id: int,
    seat_id: int,
    start_time: datetime,
    end_time: datetime,
    status: str,
) -> None:
    with SessionLocal() as session:
        session.add(
            Reservation(
                user_id=user_id,
                seat_id=seat_id,
                room_id=room_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                created_by=RESERVATION_SOURCE_STUDENT,
                cancelled_by=None,
                cancel_reason=None,
            ),
        )
        session.commit()


def test_assistant_reservation_service_lists_booked_and_checked_in_occupied_seats(seed_data: dict) -> None:
    seeded = _seed_room_and_seats(seed_data)
    start_time = datetime.combine(dt_date.today(), time(18, 0))
    end_time = start_time + timedelta(hours=2)
    _insert_reservation(
        user_id=seed_data["users"]["student"],
        room_id=seeded["room_id"],
        seat_id=seeded["seat_booked"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_BOOKED,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        room_id=seeded["room_id"],
        seat_id=seeded["seat_checked_in"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_CHECKED_IN,
    )
    _insert_reservation(
        user_id=seed_data["users"]["target"],
        room_id=seeded["room_id"],
        seat_id=seeded["seat_cancelled"],
        start_time=start_time,
        end_time=end_time,
        status=RESERVATION_STATUS_CANCELLED,
    )

    with SessionLocal() as session:
        service = AssistantReservationService(session)
        snapshots = service.list_occupied_seat_snapshots(
            seeded["room_id"],
            start_time=start_time,
            end_time=end_time,
        )

    occupied_seat_ids = {snapshot.seat_id for snapshot in snapshots}
    assert occupied_seat_ids == {seeded["seat_booked"], seeded["seat_checked_in"]}
