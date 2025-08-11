# Google Drive Clone - Test Técnico Full Stack

E## Cómo Ejecutar el Proyecto

### Prerrequisitos
- Docker Desktop instalado
- Docker Compose v2.0 o superior
- Git (para clonar el repositorio)

### Pasos de Instalación

1. **Clona el repositorio:**
   ```bash
   git clone <url-del-repositorio>
   cd <nombre-del-repositorio>
   ```

2. **Crea las carpetas de datos (si no existen):**
   ```bash
   mkdir -p data/mongodb data/minio
   ```

3. **Copia las variables de entorno (opcional):**
   ```bash
   cp .env.example .env
   # Edita .env si necesitas cambiar alguna configuración
   ```

4. **Construye y levanta los contenedores:**
   ```bash
   docker-compose up --build
   ```
   
   Para ejecutar en segundo plano:
   ```bash
   docker-compose up --build -d
   ```

5. **Verifica que todos los servicios estén funcionando:**
   ```bash
   docker-compose ps
   ```

### Acceso a la Aplicación
- **Frontend (Aplicación Web)**: http://localhost:5173
- **Backend API (Documentación)**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (usuario: `minioadmin`, contraseña: `minioadmin`)
- **MongoDB**: localhost:27017 (acceso directo con cliente MongoDB)

### Comandos Útiles

### Comandos Útiles

**Ejecutar tests del backend:**
```bash
cd backend
pytest tests/ -v
```

**Ejecutar tests con coverage:**
```bash
cd backend
pytest tests/ --cov=. --cov-report=html
```

**Parar los servicios:**
```bash
docker-compose down
```

**Ver logs en tiempo real:**
```bash
docker-compose logs -f
```

**Reiniciar un servicio específico:**
```bash
docker-compose restart frontend
docker-compose restart backend
```

**Limpiar volúmenes (⚠️ elimina todos los datos):**
```bash
docker-compose down -v
```

**Acceder al contenedor del backend:**
```bash
docker-compose exec backend bash
```

**Acceder a MongoDB:**
```bash
docker-compose exec mongodb mongosh
```a implementación de un clon simple de Google Drive, desarrollado como parte de un test técnico para una posición de Full Stack Developer.

## Descripción

La aplicación permite a los usuarios gestionar archivos (subir, descargar, editar nombre, eliminar y listar) a través de una interfaz web intuitiva. El proyecto está completamente containerizado usando Docker y Docker Compose.

## Arquitectura y Tecnologías

- **Frontend**: SvelteKit y TailwindCSS
- **Backend**: FastAPI (Python)
- **Base de Datos**: MongoDB (para metadatos de archivos)
- **Almacenamiento de Archivos**: MinIO (Object Storage compatible con S3)
- **Containerización**: Docker y Docker Compose

## Estructura del Proyecto

```
/
├── backend/                 # Aplicación FastAPI
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── frontend/               # Aplicación SvelteKit
│   ├── Dockerfile
│   ├── package.json
│   ├── svelte.config.js
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── src/
│       ├── app.css
│       ├── app.html
│       └── routes/
│           ├── +layout.svelte
│           └── +page.svelte
├── data/                   # Volúmenes persistentes
│   ├── mongodb/           # Datos de MongoDB
│   └── minio/             # Datos de MinIO
├── docker-compose.yml     # Orquestación de servicios
├── .env.example          # Variables de entorno de ejemplo
├── .gitignore           # Archivos a ignorar en Git
└── README.md           # Documentación del proyecto
```


## Requisitos Previos

- Docker
- Docker Compose

## Cómo Ejecutar el Proyecto

1.  **Clona el repositorio:**
    ```bash
    git clone <url-del-repositorio>
    cd <nombre-del-repositorio>
    ```

2.  **Construye y levanta los contenedores:**
    Desde la raíz del proyecto, ejecuta el siguiente comando. Esto construirá las imágenes de Docker para el frontend y el backend, y levantará todos los servicios definidos en `docker-compose.yml`.

    ```bash
    docker-compose up --build
    ```

3.  **Accede a la aplicación:**
    - **Frontend (Aplicación Web)**: Abre tu navegador y ve a `http://localhost:5173`
    - **Backend (API Docs)**: La documentación interactiva de la API (generada por FastAPI/Swagger) está disponible en `http://localhost:8000/docs`
    - **MinIO Console**: Puedes gestionar los buckets y archivos directamente desde la consola de MinIO en `http://localhost:9001`. Usa las credenciales `minioadmin`/`minioadmin`.

## Funcionalidades Implementadas

### **Core Features ✅**
- **📤 Subida de archivos**: Soporte para selección de archivos y drag-and-drop
- **📋 Listado de archivos**: Muestra una tabla/cuadrícula con metadatos de archivos
- **📥 Descarga de archivos**: Permite descargar cualquier archivo de la lista
- **✏️ Edición de nombre**: Permite cambiar el nombre del archivo directamente en la interfaz
- **🗑️ Eliminación de archivos**: Borra el archivo y sus metadatos con confirmación
- **📱 Interfaz Responsiva**: Diseño limpio y funcional en dispositivos desktop y móviles
- **💬 Notificaciones**: Mensajes de éxito y error para todas las operaciones

### **Bonus Features ⭐**
- **📁 Soporte de Carpetas**: Creación, navegación y organización por carpetas
- **🔍 Búsqueda Avanzada**: Búsqueda en tiempo real por nombre de archivo
- **🔄 Ordenamiento**: Ordenar por nombre, tamaño o fecha (ascendente/descendente)
- **👁️ Modos de Vista**: Vista de lista y vista de cuadrícula
- **🧪 Testing Completo**: Tests unitarios e integración
- **🚀 CI/CD Pipeline**: GitHub Actions para testing y deployment automático
- **🔒 Análisis de Seguridad**: Escaneo de vulnerabilidades con Trivy
- **🎨 UI Mejorada**: Iconos de archivos, breadcrumbs de navegación, animaciones

## Endpoints de la API (Backend)

### 📤 **Archivos (Files)**
- **POST** `/files/upload`: Sube un nuevo archivo
  - **Form Data**: `file` (archivo), `folder_id` (opcional)
  - **Response**: Metadatos del archivo subido

- **GET** `/files`: Lista todos los archivos con filtros opcionales
  - **Query Params**: `folder_id`, `search`
  - **Response**: Array de metadatos de archivos

- **GET** `/files/download/{file_id}`: Descarga un archivo
  - **Params**: `file_id` (string) - ID del archivo
  - **Response**: Stream del archivo

- **PUT** `/files/edit/{file_id}`: Edita el nombre de un archivo
  - **Params**: `file_id` (string) - ID del archivo
  - **Body**: `{"new_filename": "nuevo_nombre.ext"}`
  - **Response**: Metadatos actualizados del archivo

- **DELETE** `/files/delete/{file_id}`: Elimina un archivo
  - **Params**: `file_id` (string) - ID del archivo
  - **Response**: 204 No Content

### � **Carpetas (Folders)**
- **POST** `/folders`: Crea una nueva carpeta
  - **Body**: `{"name": "nombre", "parent_folder_id": "id_padre"}`
  - **Response**: Metadatos de la carpeta creada

- **GET** `/folders`: Lista carpetas en un directorio
  - **Query Params**: `parent_folder_id`
  - **Response**: Array de metadatos de carpetas

- **GET** `/folders/{folder_id}`: Obtiene información de una carpeta
  - **Params**: `folder_id` (string) - ID de la carpeta
  - **Response**: Metadatos de la carpeta

- **GET** `/folders/{folder_id}/content`: Obtiene contenido completo de una carpeta
  - **Params**: `folder_id` (string) - ID de la carpeta
  - **Response**: `{"folders": [], "files": [], "folder_id": "", "total_items": 0}`

- **DELETE** `/folders/{folder_id}`: Elimina una carpeta y su contenido
  - **Params**: `folder_id` (string) - ID de la carpeta
  - **Response**: 204 No Content

### 🏥 **Salud (Health)**
- **GET** `/`: Health check básico
- **GET** `/health`: Health check detallado con estado de servicios

### 📚 Documentación Interactiva
Una vez que el backend esté ejecutándose, puedes acceder a la documentación interactiva de la API en:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

El proyecto incluye tests completos para el backend:

### **Ejecutar Tests**
```bash
# Desde la raíz del proyecto
cd backend
pytest tests/ -v

# Con coverage
pytest tests/ --cov=. --cov-report=html

# Tests específicos
pytest tests/test_api.py -v
pytest tests/test_models.py -v
```

### **Estructura de Tests**
```
backend/tests/
├── __init__.py
├── conftest.py          # Configuración y fixtures
├── test_api.py          # Tests de endpoints
└── test_models.py       # Tests de modelos Pydantic
```

### **CI/CD Pipeline**
El proyecto incluye GitHub Actions que automáticamente:
- ✅ Ejecuta tests del backend con MongoDB y MinIO
- ✅ Ejecuta linting del código (Black, Flake8)
- ✅ Construye y prueba imágenes Docker
- ✅ Escanea vulnerabilidades de seguridad
- ✅ Despliega a staging/producción (configurable)

## 🔧 Troubleshooting

### Problemas Comunes

**❌ Error: "bind: address already in use"**
```bash
# Verifica qué está usando el puerto
netstat -tulpn | grep :5173
netstat -tulpn | grep :8000

# Para Windows:
netstat -ano | findstr :5173
netstat -ano | findstr :8000

# Mata el proceso o cambia el puerto en docker-compose.yml
```

**❌ Frontend no puede conectar con Backend**
- Verifica que `VITE_API_URL` apunte a `http://localhost:8000`
- Asegúrate de que CORS esté configurado correctamente
- Revisa los logs: `docker-compose logs backend`

**❌ Error de permisos en carpeta data/**
```bash
# En Linux/Mac:
sudo chmod -R 755 data/
sudo chown -R $USER:$USER data/

# En Windows, ejecuta Docker Desktop como administrador
```

**❌ MinIO bucket no se crea automáticamente**
```bash
# Reinicia solo el backend
docker-compose restart backend

# O revisa los logs
docker-compose logs minio
docker-compose logs backend
```

### Verificación de Funcionamiento

1. **Backend Health Check:**
   ```bash
   curl http://localhost:8000/docs
   ```

2. **Frontend Loading:**
   ```bash
   curl http://localhost:5173
   ```

3. **Database Connection:**
   ```bash
   docker-compose exec mongodb mongo --eval "db.stats()"
   ```

4. **MinIO Access:**
   ```bash
   curl http://localhost:9001
   ```

## 🚀 Mejoras Futuras

### **Funcionalidades Adicionales**
- [ ] 👤 Autenticación y autorización de usuarios (JWT)
- [ ] 🔗 Compartir archivos con enlaces públicos
- [ ] 👁️ Preview de imágenes y documentos en el navegador
- [ ] 📊 Dashboard con estadísticas de uso
- [ ] 🔄 Versionado de archivos
- [ ] 💾 Papelera de reciclaje
- [ ] 🏷️ Tags y etiquetas para archivos
- [ ] 📧 Notificaciones por email
- [ ] 🔐 Cifrado de archivos sensibles
- [ ] 📱 Aplicación móvil (React Native/Flutter)

### **Mejoras Técnicas**
- [ ] 🧪 Tests E2E con Playwright/Cypress
- [ ] 📊 Monitoreo y logging avanzado (Prometheus/Grafana)
- [ ] 🚀 CDN para archivos estáticos
- [ ] 🗄️ Backup automático de datos
- [ ] 🔒 HTTPS/SSL en producción
- [ ] 📦 Compresión automática de archivos
- [ ] ⚡ Cache con Redis
- [ ] 🐘 Migración a PostgreSQL (opcional)
- [ ] 🔍 Búsqueda full-text con Elasticsearch
- [ ] 🌐 Internacionalización (i18n)

### **Optimizaciones de Performance**
- [ ] ⚡ Lazy loading de imágenes
- [ ] 📄 Paginación de archivos
- [ ] 🔄 Virtual scrolling para listas grandes
- [ ] 💾 Service Worker para cache offline
- [ ] 🏃‍♂️ Optimización de imágenes automática
- [ ] 📊 Análisis de rendimiento con Web Vitals

## 📝 Notas del Desarrollador

Este proyecto fue desarrollado como parte de una prueba técnica para demostrar habilidades en:
- **Frontend**: SvelteKit, TailwindCSS, manejo de estado reactivo
- **Backend**: FastAPI, diseño de APIs RESTful, validación con Pydantic
- **Database**: MongoDB, operaciones CRUD asíncronas
- **Storage**: MinIO, gestión de archivos binarios
- **DevOps**: Docker, Docker Compose, orquestación de servicios

### Decisiones de Diseño
- Se usó MongoDB para metadatos por su flexibilidad con esquemas JSON
- MinIO se eligió por su compatibilidad con S3 y facilidad de deploy
- SvelteKit ofrece mejor rendimiento que React para este caso de uso
- FastAPI proporciona validación automática y documentación de API
