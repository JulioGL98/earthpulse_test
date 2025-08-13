from datetime import datetime

from fastapi import APIRouter

from app.database import file_collection, minio_client

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Google Drive Clone API is running", "status": "healthy", "version": "1.0.0"}


@router.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        await file_collection.find_one()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    try:
        # Check MinIO connection
        from app.config import settings

        minio_client.bucket_exists(settings.BUCKET_NAME)
        storage_status = "connected"
    except Exception:
        storage_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" and storage_status == "connected" else "unhealthy",
        "database": db_status,
        "storage": storage_status,
        "timestamp": datetime.utcnow().isoformat(),
    }
