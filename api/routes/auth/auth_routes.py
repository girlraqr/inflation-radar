from fastapi import APIRouter, Depends, status

from api.schemas.auth_schema import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from auth.dependencies import get_current_user
from auth.models import User
from auth.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    auth_service = AuthService()
    user = auth_service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    auth_service = AuthService()
    access_token, user = auth_service.login(
        email=payload.email,
        password=payload.password,
    )
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)