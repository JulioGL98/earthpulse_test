from typing import Any

from bson import ObjectId
from pydantic import BaseModel
from pydantic_core import core_schema


class PyObjectId(ObjectId):
    """Tipo personalizado para manejar ObjectId con Pydantic v2"""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.chain_schema(
                        [
                            core_schema.str_schema(),
                            core_schema.no_info_plain_validator_function(cls.validate),
                        ]
                    ),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return cls(v)


class BaseDocument(BaseModel):
    """Modelo base para documentos de MongoDB"""

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
