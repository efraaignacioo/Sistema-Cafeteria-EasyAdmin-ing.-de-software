# Usamos una imagen base de Python. La versión 'slim' es más ligera.
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instala las dependencias de Python
<<<<<<< Updated upstream
# No se necesitan dependencias del sistema para PyMySQL
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
=======
# Copia el archivo de requerimientos
COPY ./requirements.txt /app/

# Instala las dependencias
RUN pip install --no-cache-dir -r /app/requirements.txt
>>>>>>> Stashed changes

# Copia el resto del código
COPY . .

# Comando para correr la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
