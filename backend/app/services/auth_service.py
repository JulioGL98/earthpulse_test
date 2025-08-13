from typing import Optional

from app.database import user_collection
from app.models.user import Token, UserCreate
from app.utils.exceptions import ConflictException, UnauthorizedException
from app.utils.security import create_access_token, get_password_hash, verify_password


class AuthService:
    """Servicio para manejo de autenticación"""

    @staticmethod
    async def get_user(username: str) -> Optional[dict]:
        """Obtiene usuario por username"""
        return await user_collection.find_one({"username": username})

    @staticmethod
    async def authenticate_user(username: str, password: str) -> dict:
        """Autentica usuario y retorna datos del usuario"""
        user = await AuthService.get_user(username)
        if not user or not verify_password(password, user.get("hashed_password", "")):
            raise UnauthorizedException("Credenciales inválidas")
        return user

    @staticmethod
    async def create_user(user_data: UserCreate) -> Token:
        """Crea nuevo usuario"""
        # Verificar si ya existe
        existing = await AuthService.get_user(user_data.username)
        if existing:
            raise ConflictException("El usuario ya existe")

        # Crear usuario
        hashed_password = get_password_hash(user_data.password)
        user_doc = {"username": user_data.username, "hashed_password": hashed_password, "role": "user"}

        await user_collection.insert_one(user_doc)

        # Crear token
        token = create_access_token({"sub": user_data.username})
        return Token(access_token=token)

    @staticmethod
    async def login_user(username: str, password: str) -> Token:
        """Login de usuario"""
        user = await AuthService.authenticate_user(username, password)
        token = create_access_token({"sub": user["username"]})
        return Token(access_token=token)

    @staticmethod
    def is_admin(user: Optional[dict]) -> bool:
        """Verifica si el usuario es admin"""
        return bool(user and user.get("role") == "admin")
