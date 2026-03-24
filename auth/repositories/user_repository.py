from __future__ import annotations

from typing import Optional

from auth.models import User
from storage.database import get_connection


class UserRepository:
    @staticmethod
    def _map_row_to_user(row) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            subscription_tier=row["subscription_tier"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # =========================
    # READ
    # =========================

    def get_by_email(self, email: str) -> Optional[User]:
        query = """
            SELECT id, email, password_hash, full_name, role, subscription_tier,
                   is_active, created_at, updated_at
            FROM users
            WHERE email = ?
            LIMIT 1
        """
        with get_connection() as connection:
            row = connection.execute(query, (email.lower().strip(),)).fetchone()

        if row is None:
            return None

        return self._map_row_to_user(row)

    def get_by_id(self, user_id: int) -> Optional[User]:
        query = """
            SELECT id, email, password_hash, full_name, role, subscription_tier,
                   is_active, created_at, updated_at
            FROM users
            WHERE id = ?
            LIMIT 1
        """
        with get_connection() as connection:
            row = connection.execute(query, (user_id,)).fetchone()

        if row is None:
            return None

        return self._map_row_to_user(row)

    # 🔥 COMPATIBILITY FIX (für dependencies.py)
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.get_by_email(email)

    # =========================
    # CREATE
    # =========================

    def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        role: str = "user",
        subscription_tier: str = "free",
    ) -> User:
        insert_query = """
            INSERT INTO users (
                email,
                password_hash,
                full_name,
                role,
                subscription_tier,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, 1)
        """

        normalized_email = email.lower().strip()

        with get_connection() as connection:
            cursor = connection.execute(
                insert_query,
                (
                    normalized_email,
                    password_hash,
                    full_name,
                    role,
                    subscription_tier,
                ),
            )
            user_id = cursor.lastrowid

        created_user = self.get_by_id(user_id)
        if created_user is None:
            raise RuntimeError("User was created but could not be loaded afterwards.")

        return created_user

    # =========================
    # UPDATE (🔥 wichtig für Monetarisierung)
    # =========================

    def update_subscription_tier(self, user_id: int, tier: str) -> None:
        query = """
            UPDATE users
            SET subscription_tier = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        with get_connection() as connection:
            connection.execute(query, (tier, user_id))

    def activate_user(self, user_id: int) -> None:
        query = """
            UPDATE users
            SET is_active = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        with get_connection() as connection:
            connection.execute(query, (user_id,))

    def deactivate_user(self, user_id: int) -> None:
        query = """
            UPDATE users
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        with get_connection() as connection:
            connection.execute(query, (user_id,))