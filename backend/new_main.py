from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_bucket_if_not_exists, user_collection
from app.utils.security import get_password_hash
from app.middleware.auth import AuthMiddleware
from app.routers import health, auth, files, folders

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de autenticación
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Middleware de autenticación para proteger rutas"""
    # Verificar si es una ruta pública
    if AuthMiddleware.is_public_route(request.url.path, request.method):
        return await call_next(request)

    # Obtener y validar usuario
    try:
        user = await AuthMiddleware.get_current_user(request)
        request.state.user = user
    except HTTPException as e:
        return e

    response = await call_next(request)
    return response


# Incluir routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)


@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación"""
    # Crear bucket de MinIO si no existe
    create_bucket_if_not_exists()

    # Crear usuario admin si no existe
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
        # Asegurar que el admin tenga el rol correcto
        if admin.get("role") != "admin":
            await user_collection.update_one({"_id": admin["_id"]}, {"$set": {"role": "admin"}})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
