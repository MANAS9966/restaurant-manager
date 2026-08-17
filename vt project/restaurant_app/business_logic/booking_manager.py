from __future__ import annotations
import uuid
import re
from datetime import datetime

from business_logic.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from database.dao.booking_dao import BookingDAO
from database.dao.owner_dao import OwnerDAO
from database.dao.audit_dao import AuditDAO


class BookingManager:

    def __init__(self, booking_dao: BookingDAO, owner_dao: OwnerDAO, audit_dao: AuditDAO):
        self._bookings = booking_dao
        self._owners = owner_dao
        self._audit = audit_dao

    def _gen_booking_number(self) -> str:
        return f"BKG-{uuid.uuid4().hex[:10].upper()}"

    def create_booking(self, customer_id: int, owner_id: int, booking_date: str,
                       booking_time: str, number_of_guests: int,
                       dining_area: str = "Main Dining Area",
                       special_requests: str = None) -> dict:
        # Validation
        if not booking_date or not re.match(r"^\d{4}-\d{2}-\d{2}$", booking_date):
            raise ValidationError("Booking date must be in YYYY-MM-DD format.")

        try:
            parsed_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Invalid date value.")

        if parsed_date < datetime.today().date():
            raise ValidationError("Booking date cannot be in the past.")

        if not booking_time or not re.match(r"^\d{2}:\d{2}$", booking_time):
            raise ValidationError("Booking time must be in HH:MM format.")

        try:
            h, m = map(int, booking_time.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
        except ValueError:
            raise ValidationError("Invalid time value (must be between 00:00 and 23:59).")

        if not isinstance(number_of_guests, int) or number_of_guests < 1:
            try:
                number_of_guests = int(number_of_guests)
                if number_of_guests < 1:
                    raise ValueError()
            except ValueError:
                raise ValidationError("Number of guests must be at least 1.")

        dining_area = (dining_area or "Main Dining Area").strip()

        # Check if restaurant exists
        owner = self._owners.get_owner_by_id(owner_id)
        if not owner:
            raise NotFoundError(f"Restaurant owner {owner_id} not found.")

        booking_number = self._gen_booking_number()

        booking = self._bookings.create_booking(
            booking_number=booking_number,
            customer_id=customer_id,
            owner_id=owner_id,
            booking_date=booking_date,
            booking_time=booking_time,
            number_of_guests=number_of_guests,
            dining_area=dining_area,
            special_requests=special_requests
        )

        self._audit.log_operation(
            user_id=customer_id,
            operation="BOOKING_CREATED",
            resource_type="booking",
            resource_id=booking["id"],
            new_value=f"Booking for {number_of_guests} guests on {booking_date} at {booking_time} ({dining_area})"
        )

        return booking

    def get_customer_bookings(self, customer_id: int, status: str = None,
                              limit: int = 50, offset: int = 0) -> list[dict]:
        return self._bookings.get_bookings_by_customer(customer_id, status, limit, offset)

    def get_owner_bookings(self, owner_id: int, status: str = None,
                           limit: int = 50, offset: int = 0) -> list[dict]:
        return self._bookings.get_bookings_by_owner(owner_id, status, limit, offset)

    def get_booking(self, booking_id: int, actor_id: int, actor_role: str) -> dict:
        booking = self._bookings.get_booking_by_id(booking_id)
        if not booking:
            raise NotFoundError(f"Booking {booking_id} not found.")

        if actor_role == "customer" and booking["customer_id"] != actor_id:
            raise AuthorizationError("You are not authorized to view this booking.")
        elif actor_role == "owner":
            owner = self._owners.get_owner_by_user_id(actor_id)
            if not owner or booking["owner_id"] != owner["id"]:
                raise AuthorizationError("You are not authorized to view this booking.")

        return booking

    def update_booking_status(self, booking_id: int, new_status: str,
                              actor_id: int, actor_role: str) -> dict:
        booking = self._bookings.get_booking_by_id(booking_id)
        if not booking:
            raise NotFoundError(f"Booking {booking_id} not found.")

        old_status = booking["status"]
        if old_status == new_status:
            return booking

        if actor_role == "customer":
            if booking["customer_id"] != actor_id:
                raise AuthorizationError("You cannot modify this booking.")
            if new_status != "cancelled":
                raise ValidationError("Customers can only cancel bookings.")
            if old_status not in ("pending", "confirmed"):
                raise ValidationError(f"Cannot cancel a booking in '{old_status}' state.")
        elif actor_role == "owner":
            owner = self._owners.get_owner_by_user_id(actor_id)
            if not owner or booking["owner_id"] != owner["id"]:
                raise AuthorizationError("You cannot modify this booking.")
            if new_status not in ("confirmed", "cancelled", "completed"):
                raise ValidationError(f"Invalid booking status '{new_status}' for owners.")
        else:
            raise AuthorizationError("Unauthorized role.")

        self._bookings.update_booking_status(booking_id, new_status)

        self._audit.log_operation(
            user_id=actor_id,
            operation="BOOKING_STATUS_UPDATED",
            resource_type="booking",
            resource_id=booking_id,
            old_value=old_status,
            new_value=new_status
        )

        return self._bookings.get_booking_by_id(booking_id)
