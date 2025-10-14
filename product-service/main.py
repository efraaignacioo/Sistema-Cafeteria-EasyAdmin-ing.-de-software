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
    version="1.2.0" # Aumentamos la versión
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

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
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

# --- Modelos de Pedido ---
class OrderBase(BaseModel):
    items: List[str]

class OrderCreate(OrderBase):
    pass

class OrderResponse(BaseModel):
    id: int
    items: List[str]
    total: float
    status: str
    class Config:
        from_attributes = True

### NUEVO ### --- Modelo para Actualizar Estado ---
class OrderStatusUpdate(BaseModel):
    status: str

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
            Base.metadata.create_all(bind=engine)
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

# --- Endpoints del Menú ---
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

@app.delete("/menu/{product_id}", tags=["Menú"])
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado.")
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado correctamente."}

# --- Endpoints de Pedidos ---
@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201)
def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    total_price = 0.0
    for product_name in pedido.items:
        product_db = db.query(Product).filter(Product.name == product_name).first()
        if not product_db:
            raise HTTPException(status_code=404, detail=f"El producto '{product_name}' no existe en el menú.")
        total_price += product_db.price
    items_as_string = ", ".join(pedido.items)
    db_order = Order(items=items_as_string, total=total_price)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return OrderResponse(id=db_order.id, items=db_order.items.split(", "), total=db_order.total, status=db_order.status)

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    orders_db = db.query(Order).all()
    response_orders = []
    for order in orders_db:
        response_orders.append(OrderResponse(id=order.id, items=order.items.split(", "), total=order.total, status=order.status))
    return response_orders

### NUEVO ### --- Endpoint para Actualizar Estado del Pedido ---
@app.put("/pedidos/{order_id}/estado", tags=["Pedidos"], summary="Actualizar el estado de un pedido.", response_model=OrderResponse)
def actualizar_estado_pedido(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    """
    Busca un pedido por su ID y actualiza su estado.
    Estados posibles: 'pendiente', 'en preparación', 'listo', 'entregado', 'cancelado'.
    """
    # 1. Buscar el pedido en la base de datos
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db:
        raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")
        
    # 2. Actualizar el estado
    order_db.status = status_update.status
    
    # 3. Guardar los cambios en la base de datos
    db.commit()
    db.refresh(order_db)
    
    # 4. Devolver la respuesta actualizada
    return OrderResponse(id=order_db.id, items=order_db.items.split(", "), total=order_db.total, status=order_db.status)
