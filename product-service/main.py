# product-service/main.py

import os
import time
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI
# ----------------------------------------------------
app = FastAPI(
    title="API de Cafetería - EasyAdmin",
    description="API para gestionar los productos y pedidos de la cafetería.",
    version="1.1.0"
)

# ----------------------------------------------------
# 2. Configuración de la Base de Datos
# ----------------------------------------------------
DB_USER = os.getenv("MYSQL_USER", "easyadmin_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "password_segura")
DB_HOST = os.getenv("MYSQL_HOST", "mysql_db")
DB_NAME = os.getenv("MYSQL_DATABASE", "easyadmin_db")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

Base = declarative_base()
engine = None
SessionLocal = None

# ----------------------------------------------------
# 3. Modelos SQLAlchemy (Las "Tablas" de la BD)
# ----------------------------------------------------
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    price = Column(Float)

### NUEVO ###
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    # Guardamos la lista de productos como un texto separado por comas
    items = Column(String(500)) 
    total = Column(Float)
    status = Column(String(50), default="pendiente")

# ----------------------------------------------------
# 4. Modelos Pydantic (Validación para la API)
# ----------------------------------------------------
# --- Modelos de Producto ---
class ProductBase(BaseModel):
    name: str
    description: str
    price: float

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    class Config:
        from_attributes = True

# ### NUEVO ### --- Modelos de Pedido ---
class OrderBase(BaseModel):
    items: List[str] # Esperamos una lista de nombres de productos

class OrderCreate(OrderBase):
    pass

class OrderResponse(BaseModel):
    id: int
    items: List[str]
    total: float
    status: str
    class Config:
        from_attributes = True

# ----------------------------------------------------
# 5. Lógica de Conexión y Sesión de la Base de Datos
# ----------------------------------------------------
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            engine = create_engine(DATABASE_URL)
            Base.metadata.create_all(bind=engine) # Crea las tablas products Y orders
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print("product-service | ✅ Conexión a MySQL exitosa y tablas creadas.")
            return
        except Exception as e:
            time.sleep(5)
            if attempt == max_attempts - 1:
                raise e

def get_db():
    if SessionLocal is None:
        raise HTTPException(status_code=500, detail="La conexión a la base de datos no está disponible.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------------------------------
# 6. Endpoints de la API
# ----------------------------------------------------
@app.get("/health", tags=["Salud del Servicio"])
def health_check():
    return {"status": "ok"}

# --- Endpoints del Menú (sin cambios) ---
@app.get("/menu", tags=["Menú"], response_model=List[ProductResponse])
def ver_menu(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.post("/menu", tags=["Menú"], response_model=ProductResponse, status_code=201)
def agregar_producto(producto: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**producto.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/menu/{product_id}", tags=["Menú"], summary="Eliminar un producto del menú por su ID.")
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado.")
    
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado correctamente del menú."}

# ### MODIFICADO ### --- Endpoints de Pedidos (Ahora con Base de Datos) ---

@app.post("/pedidos", tags=["Pedidos"], summary="Crear un nuevo pedido.", response_model=OrderResponse, status_code=201)
def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo pedido.
    1. Valida que todos los productos existan en el menú.
    2. Calcula el precio total.
    3. Guarda el pedido en la base de datos.
    """
    total_price = 0.0
    
    # 1. Validar productos y calcular total
    for product_name in pedido.items:
        product_db = db.query(Product).filter(Product.name == product_name).first()
        if not product_db:
            raise HTTPException(status_code=404, detail=f"El producto '{product_name}' no existe en el menú.")
        total_price += product_db.price
        
    # 2. Crear el objeto del pedido para la base de datos
    # Convertimos la lista de items en un solo string para guardarlo
    items_as_string = ", ".join(pedido.items)
    
    db_order = Order(
        items=items_as_string,
        total=total_price
    )
    
    # 3. Guardar en la base de datos
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Para la respuesta, volvemos a convertir el string en una lista
    response_order = OrderResponse(
        id=db_order.id,
        items=db_order.items.split(", "),
        total=db_order.total,
        status=db_order.status
    )

    return response_order

@app.get("/pedidos", tags=["Pedidos"], summary="Ver todos los pedidos.", response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    """Obtiene todos los pedidos de la base de datos."""
    orders_db = db.query(Order).all()
    # Convertimos cada pedido de la BD al formato de respuesta
    response_orders = []
    for order in orders_db:
        response_orders.append(
            OrderResponse(
                id=order.id,
                items=order.items.split(", "),
                total=order.total,
                status=order.status
            )
        )
    return response_orders
