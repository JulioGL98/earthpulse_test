from typing import Optional

from app.services.auth_service import AuthService
from app.utils.exceptions import NotFoundException


class BaseService:
    """Clase base para servicios con funcionalidades comunes"""

    @staticmethod
    def _check_ownership(
        resource: Optional[dict], current_user: dict, not_found_message: str = "Recurso no encontrado"
    ):
        """Verifica que el usuario tenga permisos sobre el recurso"""
        if not resource:
            raise NotFoundException(not_found_message)
        if AuthService.is_admin(current_user):
            return
        owner = resource.get("owner")
        if owner is None:
            raise NotFoundException(not_found_message)
        if owner != current_user.get("username"):
            raise NotFoundException(not_found_message)
