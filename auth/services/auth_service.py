from __future__ import annotations

from fastapi import HTTPException, status

from auth.jwt_handler import create_access_token
from auth.models import User
from auth.passwords import hash_password, verify_password
from auth.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        # Check if user already exists
        existing_user = self.user_repository.get_by_email(email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists.",
            )

        # Hash password
        password_hash = hash_password(password)

        # Create user
        return self.user_repository.create_user(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role="user",
            subscription_tier="free",
        )

    def login(self, email: str, password: str) -> tuple[str, User]:
        user = self.user_repository.get_by_email(email)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive.",
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Create JWT
        token = create_access_token(subject=str(user.id))

        return token, user