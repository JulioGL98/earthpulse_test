# Clon de Google Drive - Sistema de Gestión de Archivos

Un sistema completo de gestión de archivos en la nube desarrollado como prueba técnica full stack. Permite subir, organizar, descargar y gestionar archivos a través de una interfaz web intuitiva con autenticación de usuarios.

## ¿Qué hace esta aplicación?

Esta aplicación replica las funcionalidades básicas de Google Drive:
- **Gestión de archivos**: Sube, descarga, renombra y elimina archivos
- **Organización por carpetas**: Crea carpetas y organiza tus archivos  
- **Búsqueda**: Encuentra archivos rápidamente por nombre
- **Autenticación**: Sistema de login seguro con JWT
- **Interfaz responsiva**: Funciona bien en desktop y móviles

## Arquitectura del Sistema

El proyecto utiliza una arquitectura de microservicios dockerizada:

- **Frontend**: SvelteKit + TailwindCSS (puerto 5173)
- **Backend**: FastAPI + Python (puerto 8000)  
- **Base de datos**: MongoDB (puerto 27017)
- **Almacenamiento**: MinIO (compatible S3, puerto 9000)
- **Panel admin**: MinIO Console (puerto 9001)

## Instalación y Configuración

### Requisitos previos
- **Docker Desktop** instalado y funcionando
- **Git** para clonar el repositorio
- Al menos **4GB de RAM libre** para los contenedores

### Pasos de instalación

1. **Clona este repositorio:**
   ```bash
   git clone https://github.com/JulioGL98/test.git
   cd test
   ```

2. **Crea las carpetas para los datos:**
   ```bash
   # En Windows (PowerShell)
   mkdir data\mongodb, data\minio

   # En Linux/Mac
   mkdir -p data/mongodb data/minio
   ```

3. **Levanta todos los servicios:**
   ```bash
   docker-compose up --build
   ```

   Si quieres ejecutarlo en segundo plano:
   ```bash
   docker-compose up --build -d
   ```

4. **Verifica que todo esté funcionando:**
   ```bash
   docker-compose ps
   ```
   
   Deberías ver 4 servicios corriendo: frontend, backend, mongodb y minio.

### Acceso a la aplicación

Una vez que todo esté corriendo, puedes acceder a:

- **🌐 Aplicación principal**: http://localhost:5173
- **📚 Documentación de API**: http://localhost:8000/docs  
- **🗄️ Panel de MinIO**: http://localhost:9001 (admin: minioadmin / minioadmin)
- **🔧 Health check**: http://localhost:8000/health

## Credenciales de acceso

**Usuario administrador por defecto:**
- Username: `admin`
- Password: `admin123`

Este usuario se crea automáticamente al iniciar el backend por primera vez.

## Estructura del Proyecto

```
proyecto/
├── frontend/               # Aplicación SvelteKit
│   ├── src/
│   │   ├── routes/        # Páginas de la aplicación
│   │   │   ├── login/     # Página de login
│   │   │   └── dashboard/ # Panel principal
│   │   ├── lib/           # Componentes reutilizables
│   │   └── app.html       # Template base
│   ├── package.json
│   └── Dockerfile
│
├── backend/                # API FastAPI
│   ├── app/
│   │   ├── routers/       # Endpoints de la API
│   │   │   ├── auth.py    # Autenticación
│   │   │   ├── files.py   # Gestión de archivos
│   │   │   ├── folders.py # Gestión de carpetas
│   │   │   └── health.py  # Health checks
│   │   ├── models/        # Modelos de datos
│   │   ├── services/      # Lógica de negocio
│   │   ├── middleware/    # Middleware de auth
│   │   └── utils/         # Utilidades
│   ├── tests/             # Tests unitarios
│   ├── main.py           # Punto de entrada
│   └── requirements.txt
│
├── data/                  # Datos persistentes
│   ├── mongodb/          # Base de datos
│   └── minio/            # Archivos subidos
│
└── docker-compose.yml    # Orquestación de servicios
```

## Funcionalidades Principales

### 🔐 Autenticación
- Sistema de login con JWT tokens
- Middleware de autenticación automática
- Protección de rutas privadas

### 📁 Gestión de Carpetas
- Crear carpetas y subcarpetas
- Navegación jerárquica
- Breadcrumbs para ubicación actual

### � Gestión de Archivos  
- **Subir archivos**: Drag & drop o selección manual
- **Descargar**: Un click para descargar cualquier archivo
- **Renombrar**: Edición inline del nombre
- **Eliminar**: Con confirmación de seguridad
- **Búsqueda**: Filtro en tiempo real por nombre

### 🎨 Interfaz de Usuario
- Diseño responsivo con TailwindCSS
- Vista de lista y cuadrícula
- Iconos específicos por tipo de archivo
- Notificaciones de éxito/error
- Animaciones suaves

## API Endpoints

### Autenticación
```
POST /auth/login          # Iniciar sesión
POST /auth/logout         # Cerrar sesión  
GET  /auth/me            # Info del usuario actual
```

### Archivos
```
POST   /files/upload      # Subir archivo
GET    /files             # Listar archivos
GET    /files/download/{id} # Descargar archivo
PUT    /files/edit/{id}   # Renombrar archivo
DELETE /files/delete/{id} # Eliminar archivo
```

### Carpetas
```
POST   /folders           # Crear carpeta
GET    /folders           # Listar carpetas
GET    /folders/{id}      # Info de carpeta específica
GET    /folders/{id}/content # Contenido de carpeta
DELETE /folders/{id}      # Eliminar carpeta
```

### Sistema
```
GET /health              # Estado de servicios
GET /docs               # Documentación interactiva
```

## Comandos Útiles para Desarrollo

### Gestión de Contenedores

**Parar todos los servicios:**
```bash
docker-compose down
```

**Ver logs en tiempo real:**
```bash
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Reiniciar un servicio:**
```bash
docker-compose restart backend
docker-compose restart frontend
```

**Reconstruir y reiniciar:**
```bash
docker-compose up --build --no-deps backend
```

**Limpiar todo (¡cuidado! elimina los datos):**
```bash
docker-compose down -v
```

### Desarrollo y Testing

**Ejecutar tests del backend:**
```bash
cd backend
pytest tests/ -v

# Con reporte de cobertura
pytest tests/ --cov=. --cov-report=html
```

**Acceso directo a contenedores:**
```bash
# Entrar al contenedor del backend
docker-compose exec backend bash

# Entrar a MongoDB
docker-compose exec mongodb mongosh

# Ver archivos en MinIO
docker-compose exec minio ls /data
```

**Desarrollo local del frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Desarrollo local del backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

## Testing

El proyecto incluye tests automatizados para garantizar la calidad del código:

### Tests del Backend
- **Tests de modelos**: Validación de esquemas Pydantic
- **Tests de API**: Endpoints de autenticación y health checks  
- **Tests de integración**: Funcionamiento con MongoDB y MinIO

```bash
# Ejecutar todos los tests
cd backend && pytest tests/ -v

# Tests específicos
pytest tests/test_models.py -v
pytest tests/test_api.py -v
pytest tests/test_auth.py -v
```

### Cobertura de Código
```bash
cd backend
pytest tests/ --cov=. --cov-report=html
# Abre coverage_html/index.html para ver el reporte
```

## Solución de Problemas Comunes

### Error: Puerto ya en uso
```bash
# Verificar qué está usando el puerto
netstat -ano | findstr :5173
netstat -ano | findstr :8000

# Matar el proceso (Windows)
taskkill /PID <numero_del_proceso> /F
```

### Frontend no conecta con Backend
1. Verifica que el backend esté corriendo: http://localhost:8000/health
2. Revisa las variables de entorno en docker-compose.yml
3. Comprueba los logs: `docker-compose logs backend`

### Problemas con permisos de carpetas
```bash
# En Windows, ejecuta PowerShell como administrador
# En Linux/Mac:
sudo chmod -R 755 data/
sudo chown -R $USER:$USER data/
```

### Base de datos no inicializa
```bash
# Reinicia MongoDB
docker-compose restart mongodb

# Verifica el estado
docker-compose exec mongodb mongosh --eval "db.stats()"
```

### MinIO no crea el bucket automáticamente
```bash
# Reinicia el backend para que recree el bucket
docker-compose restart backend

# Verifica en el panel de MinIO: http://localhost:9001
```

## Tecnologías Utilizadas

### Frontend
- **SvelteKit**: Framework web reactivo y rápido
- **TailwindCSS**: Framework de CSS utility-first
- **Vite**: Build tool moderno y rápido

### Backend  
- **FastAPI**: Framework web asíncrono para Python
- **Motor**: Driver asíncrono para MongoDB
- **MinIO Client**: SDK para interactuar con almacenamiento
- **Pydantic**: Validación de datos y serialización
- **JWT**: Autenticación con tokens seguros

### Base de Datos
- **MongoDB**: Base de datos NoSQL para metadatos
- **MinIO**: Almacenamiento de objetos compatible con S3

### DevOps
- **Docker**: Containerización de servicios
- **Docker Compose**: Orquestación multi-contenedor
- **GitHub Actions**: CI/CD pipeline automatizado
  
