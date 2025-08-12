from fastapi import APIRouter
from app.models.user import UserCreate, LoginRequest, Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """Registro de nuevo usuario"""
    return await AuthService.create_user(user)


@router.post("/login", response_model=Token)
async def login(data: LoginRequest):
    """Login de usuario"""
    return await AuthService.login_user(data.username, data.password)
