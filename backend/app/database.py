from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

client = AsyncIOMotorClient(settings.DATABASE_URL)
db = client[settings.DATABASE_NAME]

file_collection = db.get_collection("files")
folder_collection = db.get_collection("folders")
user_collection = db.get_collection("users")

minio_client = Minio(settings.MINIO_URL, access_key=settings.MINIO_ACCESS_KEY, secret_key=settings.MINIO_SECRET_KEY, secure=False)


def create_bucket_if_not_exists():
    found = minio_client.bucket_exists(settings.BUCKET_NAME)
    if not found:
        minio_client.make_bucket(settings.BUCKET_NAME)
        print(f"Bucket '{settings.BUCKET_NAME}' creado.")
    else:
        print(f"Bucket '{settings.BUCKET_NAME}' ya existe.")


async def get_db():
    return db


def get_minio():
    return minio_client
