from datetime import datetime
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Esquema base de usuario"""

    username: str


class UserCreate(UserBase):
    """Esquema para crear usuario"""

    password: str


class UserInDB(UserBase):
    """Esquema de usuario en base de datos"""

    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    role: str = "user"


class Token(BaseModel):
    """Esquema de token de autenticación"""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Esquema para login"""

    username: str
    password: str
