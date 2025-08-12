from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
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
        response = await call_next(request)
        return response
    except HTTPException as e:
        raise e

# Incluir routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(folders.router)

# Startup sin dependencias externas para testing
@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación - versión de testing"""
    print("🚀 Servidor FastAPI refactorizado iniciado correctamente!")
    print("📊 Estructura modular cargada:")
    print("   ✅ Config")
    print("   ✅ Models")
    print("   ✅ Services") 
    print("   ✅ Routers")
    print("   ✅ Utils")
    print("   ✅ Middleware")

if __name__ == "__main__":
    uvicorn.run("main_test:app", host="0.0.0.0", port=8000, reload=True)
