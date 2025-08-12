from fastapi import Request, HTTPException
from app.utils.security import decode_access_token
from app.services.auth_service import AuthService


class AuthMiddleware:
    """Middleware para manejo de autenticación"""

    @staticmethod
    def is_public_route(path: str, method: str) -> bool:
        """Verifica si una ruta es pública"""
        public_routes = [
            ("/", "GET"),
            ("/health", "GET"),
            ("/docs", "GET"),
            ("/redoc", "GET"),
            ("/openapi.json", "GET"),
        ]

        # Rutas de autenticación
        if path.startswith("/auth/"):
            return True

        # Preflight CORS
        if method == "OPTIONS":
            return True

        return (path, method) in public_routes

    @staticmethod
    async def get_current_user(request: Request) -> dict:
        """Obtiene el usuario actual desde el token de autorización"""
        if AuthMiddleware.is_public_route(request.url.path, request.method):
            return None

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="No autorizado: token faltante")

        token = auth_header.split(" ", 1)[1].strip()
        payload = decode_access_token(token)

        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido o expirado")

        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")

        user = await AuthService.get_user(username)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        return user
