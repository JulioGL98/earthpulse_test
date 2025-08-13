from typing import Optional

from bson import ObjectId

from app.utils.exceptions import ValidationException


def validate_object_id(id_str: str, field_name: str = "ID") -> ObjectId:
    """Valida y convierte string a ObjectId"""
    if not ObjectId.is_valid(id_str):
        raise ValidationException(f"{field_name} inválido")
    return ObjectId(id_str)
