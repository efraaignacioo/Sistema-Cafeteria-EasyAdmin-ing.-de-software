# Usamos una imagen base de Python más completa para que 'mysqlclient' pueda compilar
FROM python:3.11

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala las dependencias necesarias para 'mysqlclient'
# Esto es específico para MySQL y evita errores de compilación
RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev pkg-config

# Copia e instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Comando para correr la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
