# Usamos una imagen base de Python. La versión 'slim' es más ligera.
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Comando para correr la aplicación
# AÑADIDO: La bandera '--reload' para desarrollo en tiempo real.
# Esto le dice a Uvicorn que se reinicie automáticamente cuando los archivos .py cambien.
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
