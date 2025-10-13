# product-service/main.py

import os
import time
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel # AÑADIDO: Importamos BaseModel para los modelos de tu compañero

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI
# ----------------------------------------------------
app = FastAPI(
    title="Servicio de Productos - EasyAdmin",
    description="API para gestionar los productos y pedidos de la cafetería.",
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
# 3. Configuración y Modelos de SQLAlchemy (Base de Datos)
# ----------------------------------------------------
Base = declarative_base()
engine = None
SessionLocal = None

# Modelo para la tabla 'products' en la base de datos
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    description = Column(String(255))
    price = Column(Float)

# ----------------------------------------------------
# CÓDIGO DE TU COMPAÑERO INTEGRADO
# ----------------------------------------------------

# 4. Modelos de Pydantic (para validar los datos de entrada de la API)
class ProductoAPI(BaseModel):
    nombre: str
    precio: int

class PedidoAPI(BaseModel):
    productos: list[str]

# 5. Datos en memoria (esto es temporal, luego debería usar la base de datos)
menu = {
    "cafecito": 2500,
    "tostada": 1750,
    "empanada": 2000,
    "jugo": 1500,
    "té" : 1200,
    "chocolate": 3000,
}
pedidos = []
pedidos_id_counter = 1
    
# ----------------------------------------------------
# 6. Evento de Arranque para Conectar a la DB
# ----------------------------------------------------
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    max_attempts = 10
    
    for attempt in range(max_attempts):
        try:
            print(f"product-service | Intentando conectar a la DB... (Intento {attempt+1}/{max_attempts})")
            engine = create_engine(DATABASE_URL)
            engine.connect()
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine)
            print("product-service | ✅ Conexión a MySQL exitosa y tablas creadas.")
            return
        except Exception as e:
            print(f"product-service | ⚠️  Fallo en la conexión: {e}")
            if attempt == max_attempts - 1:
                print(f"product-service | ❌ ERROR FATAL: Fallo al conectar a la DB después de {max_attempts} intentos.")
                raise e
            time.sleep(5)

# ----------------------------------------------------
# 7. Endpoints de la API
# ----------------------------------------------------

# Endpoint de Salud
@app.get("/health", tags=["Salud del Servicio"])
def health_check():
    """Verifica el estado general del microservicio y su conexión a MySQL."""
    if engine and SessionLocal:
        return {"status": "ok", "service": "product-service", "db_status": "connected"}
    else:
        raise HTTPException(status_code=503, detail="Servicio inactivo: La conexión a la base de datos falló.")

# --- Endpoints del Menú (de tu compañero) ---
@app.get("/menu", tags=["Menú"], summary="Ver el menú completo.")
def ver_menu():
    return {"Menú": menu}

@app.post("/menu", tags=["Menú"], summary="Agregar un nuevo producto al menú.")
def agregar_producto(plato: ProductoAPI):
    if plato.nombre in menu:
        raise HTTPException(status_code=400, detail="El producto ya existe en el menú.")
    menu[plato.nombre] = plato.precio
    return {"mensaje": f"Producto '{plato.nombre}' agregado correctamente al menú."}

@app.delete("/menu/{nombre}", tags=["Menú"], summary="Eliminar un producto del menú por su nombre.")
def eliminar_producto(nombre: str):
    if nombre not in menu:
        raise HTTPException(status_code=404, detail="El producto no existe en el menú.")
    del menu[nombre]
    return {"mensaje": f"Producto '{nombre}' eliminado correctamente del menú."}

# --- Endpoints de Pedidos (de tu compañero) ---
@app.post("/pedidos", tags=["Pedidos"], summary="Crear un nuevo pedido.")
def crear_pedido(pedido: PedidoAPI):
    global pedidos_id_counter
    for producto in pedido.productos:
        if producto not in menu:
            raise HTTPException(status_code=400, detail=f"El producto '{producto}' no existe en el menú.")
    
    nuevo_pedido = {
        "id": pedidos_id_counter,
        "productos": pedido.productos, # CORREGIDO: Usaba una variable incorrecta aquí
        "estado": "pendiente"
    }
    pedidos.append(nuevo_pedido)
    pedidos_id_counter += 1
    return {"mensaje": "Pedido creado correctamente.", "pedido": nuevo_pedido}

@app.get("/pedidos", tags=["Pedidos"], summary="Ver todos los pedidos.")
def ver_pedidos():
    return {"pedidos": pedidos}

@app.get("/pedidos/{pedido_id}", tags=["Pedidos"], summary="Ver un pedido por su ID.")
def ver_pedido(pedido_id: int):
    for pedido in pedidos:
        if pedido["id"] == pedido_id:
            return {"pedido": pedido}
    raise HTTPException(status_code=404, detail="Pedido no encontrado.")