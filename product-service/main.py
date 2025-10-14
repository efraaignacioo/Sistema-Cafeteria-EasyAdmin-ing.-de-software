import os
import time
import json
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, field_validator # <--- IMPORTACIÓN AÑADIDA
from typing import List, Optional, Dict, Union
from datetime import datetime

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI
# ----------------------------------------------------
app = FastAPI(
    title="API de Cafetería - EasyAdmin",
    description="API para gestionar los productos y pedidos de la cafetería.",
    version="1.3.0"
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
    items = Column(String(500)) # <-- Almacenado como String
    total = Column(Float)
    status = Column(String(50), default="pendiente")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

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
    items: List[str] # <-- Espera una Lista
    total: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

    # ✅ --- VALIDADOR PARA CORREGIR EL TIPO DE DATO --- ✅
    @field_validator('items', mode='before')
    @classmethod
    def split_items_string(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(',')]
        return v

# --- Modelo para Actualizar Estado ---
class OrderStatusUpdate(BaseModel):
    status: str

# Modelo de Mensaje para WebSocket
class WebSocketMessage(BaseModel):
    action: str
    order: OrderResponse
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Modulo de Gestión de WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WS-KDS / Conexión activa: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WS-KDS / Conexion cerrada. Activas: {len(self.active_connections)}")

    async def broadcast(self, data: Union[str, Dict, BaseModel]):
        if isinstance(data, BaseModel):
            message = data.model_dump_json()
        elif isinstance(data, dict):
            message = json.dumps(data)
        elif isinstance(data, str):
            message = data
        else:
            message = json.dumps({"error": "Formato de mensaje no soportado"})
        
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                dead_connections.append(connection)
            except Exception as e:
                print(f"WS-KDS / Error al enviar conexión: {e}")
                dead_connections.append(connection)

        for connection in dead_connections:
            if connection in self.active_connections:
                self.disconnect(connection)

manager = ConnectionManager()
        
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
            print(f"product-service | ❌ Intento {attempt + 1} de conexión a DB fallido: {e}")
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

# Endpoint de WebSockets
@app.websocket("/ws/kds")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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
    db_product = Product(**producto.dict())
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
async def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
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
    
    notification_message = WebSocketMessage(action="new_order", order=db_order)
    await manager.broadcast(notification_message)

    return db_order

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.put("/pedidos/{order_id}/estado", tags=["Pedidos"], summary="Actualizar el estado de un pedido.", response_model=OrderResponse)
async def actualizar_estado_pedido(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db:
        raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")
        
    order_db.status = status_update.status
    db.commit()
    db.refresh(order_db)
    
    notification_message = WebSocketMessage(action='status_update', order=order_db)
    await manager.broadcast(notification_message)

    return order_db