from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# MongoDB Connection
client = AsyncIOMotorClient(settings.DATABASE_URL)
db = client[settings.DATABASE_NAME]

# Collections
file_collection = db.get_collection("files")
folder_collection = db.get_collection("folders")
user_collection = db.get_collection("users")

# MinIO Connection
minio_client = Minio(settings.MINIO_URL, access_key=settings.MINIO_ACCESS_KEY, secret_key=settings.MINIO_SECRET_KEY, secure=False)


def create_bucket_if_not_exists():
    """Crea el bucket de MinIO si no existe"""
    found = minio_client.bucket_exists(settings.BUCKET_NAME)
    if not found:
        minio_client.make_bucket(settings.BUCKET_NAME)
        print(f"Bucket '{settings.BUCKET_NAME}' creado.")
    else:
        print(f"Bucket '{settings.BUCKET_NAME}' ya existe.")


async def get_db():
    """Dependency para obtener la instancia de base de datos"""
    return db


def get_minio():
    """Dependency para obtener el cliente de MinIO"""
    return minio_client
