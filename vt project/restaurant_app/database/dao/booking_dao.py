from __future__ import annotations
from database.dao.base_dao import BaseDAO


class BookingDAO(BaseDAO):

    def create_booking(self, booking_number: str, customer_id: int, owner_id: int,
                       booking_date: str, booking_time: str, number_of_guests: int,
                       dining_area: str = "Main Dining Area",
                       special_requests: str = None) -> dict:
        sql = """
            INSERT INTO table_bookings
            (booking_number, customer_id, owner_id, booking_date, booking_time,
             number_of_guests, dining_area, special_requests)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        bid = self._insert(sql, (
            booking_number, customer_id, owner_id, booking_date, booking_time,
            number_of_guests, dining_area or "Main Dining Area", special_requests
        ))
        return self.get_booking_by_id(bid)

    def get_booking_by_id(self, booking_id: int) -> dict | None:
        return self._fetchone(
            """SELECT tb.*, u.full_name AS customer_name, u.email AS customer_email,
                      ro.business_name
               FROM table_bookings tb
               JOIN users u ON tb.customer_id = u.id
               JOIN restaurant_owners ro ON tb.owner_id = ro.id
               WHERE tb.id = ?""",
            (booking_id,)
        )

    def get_booking_by_number(self, booking_number: str) -> dict | None:
        return self._fetchone(
            "SELECT * FROM table_bookings WHERE booking_number = ?", (booking_number,)
        )

    def get_bookings_by_customer(self, customer_id: int, status: str = None,
                                 limit: int = 50, offset: int = 0) -> list[dict]:
        conditions = ["tb.customer_id = ?"]
        params = [customer_id]
        if status:
            conditions.append("tb.status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT tb.*, ro.business_name
            FROM table_bookings tb
            JOIN restaurant_owners ro ON tb.owner_id = ro.id
            {where}
            ORDER BY tb.booking_date DESC, tb.booking_time DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def get_bookings_by_owner(self, owner_id: int, status: str = None,
                              limit: int = 50, offset: int = 0) -> list[dict]:
        conditions = ["tb.owner_id = ?"]
        params = [owner_id]
        if status:
            conditions.append("tb.status = ?")
            params.append(status)
        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT tb.*, u.full_name AS customer_name
            FROM table_bookings tb
            JOIN users u ON tb.customer_id = u.id
            {where}
            ORDER BY tb.booking_date DESC, tb.booking_time DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return self._fetchall(sql, tuple(params))

    def update_booking_status(self, booking_id: int, status: str) -> bool:
        sql = "UPDATE table_bookings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        self._execute(sql, (status, booking_id))
        return True
