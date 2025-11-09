# auth-service/Dockerfile
# Usamos la misma imagen base de Python que los otros servicios

FROM python:3.11-slim

WORKDIR /app

# Copiamos primero el archivo de requerimientos para optimizar el caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Comando para correr la aplicación
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
