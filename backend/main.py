from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_bucket_if_not_exists, user_collection
from app.middleware.auth import AuthMiddleware
from app.routers import auth, files, folders, health
from app.utils.security import get_password_hash

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if AuthMiddleware.is_public_route(request.url.path, request.method):
        return await call_next(request)

    try:
        user = await AuthMiddleware.get_current_user(request)
        request.state.user = user
        response = await call_next(request)
        return response
    except HTTPException as e:
        raise e


# Incluir routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)


@app.on_event("startup")
async def startup_event():
    create_bucket_if_not_exists()

    admin = await user_collection.find_one({"username": "admin"})
    if not admin:
        await user_collection.insert_one(
            {
                "username": "admin",
                "hashed_password": get_password_hash("admin123"),
                "created_at": datetime.utcnow(),
                "role": "admin",
            }
        )
        print("Usuario admin creado: admin / admin123")
    else:
        if admin.get("role") != "admin":
            await user_collection.update_one({"_id": admin["_id"]}, {"$set": {"role": "admin"}})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
