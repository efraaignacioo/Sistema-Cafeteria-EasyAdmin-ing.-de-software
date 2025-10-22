# order-service/main.py
# Este microservicio se encarga de toda la lógica de pedidos.

import os
import time
import json
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# --- Instancia de FastAPI para el servicio de pedidos ---
app = FastAPI(
    title="API de Pedidos - EasyAdmin",
    description="Microservicio para gestionar los pedidos, estados y KDS.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuración de la Base de Datos (compartida) ---
DB_USER = os.getenv("MYSQL_USER", "easyadmin_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "password_segura")
DB_HOST = os.getenv("MYSQL_HOST", "mysql_db")
DB_NAME = os.getenv("MYSQL_DATABASE", "easyadmin_db")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

Base = declarative_base()
engine = None
SessionLocal = None

# --- Modelos SQLAlchemy ---
# Nota: Este servicio necesita conocer el modelo 'Product' para poder consultarlo.
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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# --- Modelos Pydantic ---
class OrderBase(BaseModel):
    items: List[str]
class OrderCreate(OrderBase): pass
class OrderResponse(BaseModel):
    id: int
    items: List[str]
    total: float
    status: str
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True
    
    @field_validator('items', mode='before')
    @classmethod
    def split_items_string(cls, v):
        if isinstance(v, str): return [item.strip() for item in v.split(',')]
        return v

class OrderStatusUpdate(BaseModel):
    status: str

class TicketResponse(BaseModel):
    order_id: int
    items: List[str]
    total: float
    issued_at: datetime

# --- Lógica de Conexión, Sesión y WebSockets ---
class ConnectionManager:
    def __init__(self): self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, data: dict):
        message = json.dumps(data, default=str)
        for connection in self.active_connections: await connection.send_text(message)
manager = ConnectionManager()

@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    # ... (código de reintentos de conexión)
    for attempt in range(10):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect(): Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print("✅ [order-service] Conexión a MySQL exitosa.")
            return
        except Exception as e:
            print(f"⚠️ [order-service] Fallo en conexión, reintentando... ({e})")
            time.sleep(5)
            if attempt == 9: raise e

def get_db():
    if SessionLocal is None: raise HTTPException(status_code=500, detail="DB no disponible.")
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.websocket("/ws/kds")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

# --- Endpoints de la API de Pedidos ---
@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "order-service"}

@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201)
async def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    total_price = 0.0
    for name in pedido.items:
        product = db.query(Product).filter(Product.name == name).first()
        if not product: raise HTTPException(status_code=404, detail=f"Producto '{name}' no existe.")
        total_price += product.price
    
    db_order = Order(items=", ".join(pedido.items), total=total_price)
    db.add(db_order); db.commit(); db.refresh(db_order)
    
    response_order = OrderResponse.model_validate(db_order)
    message = {"type": "new_order", "data": response_order.model_dump()}
    await manager.broadcast(message)
    
    return response_order

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.put("/pedidos/{order_id}/estado", tags=["Pedidos"], response_model=OrderResponse)
async def actualizar_estado_pedido(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db: raise HTTPException(status_code=404, detail=f"Pedido {order_id} no encontrado.")
    
    order_db.status = status_update.status
    db.commit(); db.refresh(order_db)
    
    response_order = OrderResponse.model_validate(order_db)
    message = {"type": "status_update", "data": response_order.model_dump()}
    await manager.broadcast(message)
    
    return response_order

@app.get("/pedidos/{order_id}/ticket", tags=["Pedidos"], response_model=TicketResponse)
def generar_ticket(order_id: int, db: Session = Depends(get_db)):
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db: raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")

    items_list = OrderResponse.model_validate(order_db).items
    ticket = TicketResponse(order_id=order_db.id, items=items_list, total=order_db.total, issued_at=order_db.created_at)
    return ticket
