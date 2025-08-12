from fastapi import HTTPException


class AppException(HTTPException):
    """Excepción base de la aplicación"""

    pass


class ValidationException(AppException):
    """Excepción de validación"""

    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class NotFoundException(AppException):
    """Excepción de recurso no encontrado"""

    def __init__(self, detail: str = "Recurso no encontrado"):
        super().__init__(status_code=404, detail=detail)


class UnauthorizedException(AppException):
    """Excepción de no autorizado"""

    def __init__(self, detail: str = "No autorizado"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenException(AppException):
    """Excepción de acceso prohibido"""

    def __init__(self, detail: str = "Acceso prohibido"):
        super().__init__(status_code=403, detail=detail)


class ConflictException(AppException):
    """Excepción de conflicto"""

    def __init__(self, detail: str = "Conflicto"):
        super().__init__(status_code=409, detail=detail)


class InternalServerException(AppException):
    """Excepción de error interno del servidor"""

    def __init__(self, detail: str = "Error interno del servidor"):
        super().__init__(status_code=500, detail=detail)
