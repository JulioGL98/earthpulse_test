# Usar una imagen oficial de Python como imagen base
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de dependencias al directorio de trabajo
COPY requirements.txt .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación al directorio de trabajo
COPY . .

# Agregar el directorio app al PYTHONPATH para imports relativos
ENV PYTHONPATH=/app

# Exponer el puerto 8000 para que la API sea accesible
EXPOSE 8000

# Comando para ejecutar la aplicación cuando se inicie el contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]