# Usar una imagen oficial de Node.js como imagen base
FROM node:18-alpine

# Establecer el directorio de trabajo dentro del contenedor
    WORKDIR /app

    # Copiar los archivos de definición del paquete (package.json y package-lock.json)
    # Esto aprovecha el cache de Docker para no reinstalar dependencias si no cambian
    COPY package*.json ./

    # Instalar todas las dependencias del proyecto
    RUN npm install

    # Copiar el resto del código de la aplicación
    # (Será sobreescrito por el volumen de docker-compose, pero es una buena práctica tenerlo)
    COPY . .

    # Exponer el puerto de desarrollo de Vite
    EXPOSE 5173

    # Comando para iniciar el servidor de desarrollo
    # El flag --host es crucial para que sea accesible desde fuera del contenedor
    CMD ["npm", "run", "dev", "--", "--host"]
    