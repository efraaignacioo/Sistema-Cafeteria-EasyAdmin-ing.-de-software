# product-service/main.py

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import time
import os

# 1. Configuración de la Base de Datos (variables de entorno de Docker Compose)
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_NAME = os.getenv("MYSQL_DATABASE")
DATABASE_URL = f"mysql+mysqlclient://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# 2. Inicialización de FastAPI
app = FastAPI(
    title="Servicio de Productos EasyAdmin",
    description="API para la gestión de productos, cubriendo RF01, RF02 y RF03."
)

# 3. Función de Conexión y Salud de DB
def check_db_connection(max_attempts=10):
    """Intenta conectar a la base de datos con reintentos."""
    
    # Crea una URL para logs sin la contraseña (solo por seguridad en logs, pero no es necesario en Docker)
    log_url = f"mysql+mysqlclient://{DB_USER}:***@{DB_HOST}/{DB_NAME}"
    
    print(f"product-service | Intentando conectar a la DB: {log_url}")

    for attempt in range(1, max_attempts + 1):
        try:
            # Crea un motor de SQLAlchemy y verifica la conexión
            engine = create_engine(DATABASE_URL)
            engine.connect()
            print("product-service | ✅ Conexión a MySQL exitosa!")
            return "connected"
        except Exception as e:
            if attempt < max_attempts:
                print(f"product-service | ❌ Fallo al conectar a MySQL. Reintento en 5s... (Intento {attempt}/{max_attempts})")
                time.sleep(5)
            else:
                print(f"product-service | ❌ Fallo fatal después de {max_attempts} intentos: {e}")
                return f"failed ({e})"

# 4. Endpoint de Salud (Health Check)
@app.get("/health", tags=["Salud del Servicio"], summary="Verifica el estado del servicio y la conexión a la base de datos.")
def health_check():
    """Verifica el estado general del microservicio y su conexión a MySQL."""
    db_status = check_db_connection()
    
    return {
        "status": "ok",
        "service": "product-service",
        "db_status": db_status
    }

# 5. Endpoint de Productos (Ruta inicial de prueba)
@app.get("/products", tags=["Productos"], summary="Obtiene la lista de productos (vacío por ahora).")
def list_products():
    """Ruta de prueba que devolverá un listado vacío hasta implementar el CRUD."""
    return []