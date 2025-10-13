# product-service/main.py

import os
import time
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI (¡PASO CLAVE!)
#    Esto debe ocurrir ANTES de usar '@app'.
# ----------------------------------------------------
app = FastAPI(
    title="Servicio de Productos - EasyAdmin",
    description="API para gestionar los productos de la cafetería.",
    version="1.0.0"
)

# ----------------------------------------------------
# 2. Variables de Entorno y Conexión a la Base de Datos
# ----------------------------------------------------
DB_USER = os.getenv("MYSQL_USER", "easyadmin_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "password_segura")
DB_HOST = os.getenv("MYSQL_HOST", "mysql_db")
DB_NAME = os.getenv("MYSQL_DATABASE", "easyadmin_db")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# ----------------------------------------------------
# 3. Configuración y Modelos de SQLAlchemy
# ----------------------------------------------------
# AÑADIDO: 'Base' es necesario para que SQLAlchemy sepa cómo crear las tablas.
Base = declarative_base()

# Motor de conexión (se inicializará en el evento 'startup')
engine = None
SessionLocal = None

# AÑADIDO: Un modelo de ejemplo para que 'Base.metadata.create_all' funcione.
# Debes reemplazar esto con tus modelos reales (ej: Producto).
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    description = Column(String(255))
    price = Column(Float)
    
# ----------------------------------------------------
# 4. Evento de Arranque para Conectar a la DB
#    Ahora 'app' ya existe y este código es válido.
# ----------------------------------------------------
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    max_attempts = 10
    
    for attempt in range(max_attempts):
        try:
            print(f"product-service | Intentando conectar a la DB... (Intento {attempt+1}/{max_attempts})")
            
            # Intento de conexión
            engine = create_engine(DATABASE_URL)
            engine.connect()
            
            # Si la conexión es exitosa, creamos la sesión y las tablas
            # AÑADIDO: Faltaba importar 'sessionmaker'.
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine) # Esto creará la tabla 'products'
            
            print("product-service | ✅ Conexión a MySQL exitosa y tablas creadas.")
            return
        
        except Exception as e:
            print(f"product-service | ⚠️  Fallo en la conexión: {e}")
            if attempt == max_attempts - 1:
                print(f"product-service | ❌ ERROR FATAL: Fallo al conectar a la DB después de {max_attempts} intentos.")
                raise e

            time.sleep(5)

# ----------------------------------------------------
# 5. Endpoint de Salud (Health Check)
# ----------------------------------------------------
@app.get("/health", tags=["Salud del Servicio"])
def health_check():
    """Verifica el estado general del microservicio y su conexión a MySQL."""
    if engine and SessionLocal:
        return {"status": "ok", "service": "product-service", "db_status": "connected"}
    else:
        raise HTTPException(status_code=503, detail="Servicio inactivo: La conexión a la base de datos falló durante el arranque.")

# ----------------------------------------------------
# 6. Endpoints de tu API (CRUD de Productos)
#    ... (El resto de tus endpoints CRUD RF01, RF02, etc. van aquí) ...
# ----------------------------------------------------
