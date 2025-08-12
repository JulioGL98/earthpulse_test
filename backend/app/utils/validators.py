from bson import ObjectId
from typing import Optional
from app.utils.exceptions import ValidationException


def validate_object_id(id_str: str, field_name: str = "ID") -> ObjectId:
    """Valida y convierte string a ObjectId"""
    if not ObjectId.is_valid(id_str):
        raise ValidationException(f"{field_name} inválido")
    return ObjectId(id_str)


def validate_filename(filename: str) -> str:
    """Valida nombre de archivo"""
    if not filename or not filename.strip():
        raise ValidationException("El nombre del archivo no puede estar vacío")

    # Caracteres no permitidos en nombres de archivo
    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        raise ValidationException(f"El nombre del archivo contiene caracteres no válidos: {invalid_chars}")

    return filename.strip()


def validate_folder_name(folder_name: str) -> str:
    """Valida nombre de carpeta"""
    if not folder_name or not folder_name.strip():
        raise ValidationException("El nombre de la carpeta no puede estar vacío")

    # Caracteres no permitidos en nombres de carpeta
    invalid_chars = '<>:"/\\|?*'
    if any(char in folder_name for char in invalid_chars):
        raise ValidationException(f"El nombre de la carpeta contiene caracteres no válidos: {invalid_chars}")

    return folder_name.strip()
