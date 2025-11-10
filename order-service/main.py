# order-service/main.py
# Este microservicio se encarga de toda la lógica de pedidos y ahora está protegido.

import os
import time
import json
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
# IMPORTACIONES DE SEGURIDAD
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
# FIN IMPORTACIONES DE SEGURIDAD
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# ----------------------------------------------------
# 0. CONFIGURACIÓN DE SEGURIDAD
# ----------------------------------------------------
# Nota: La clave secreta debe ser idéntica en auth-service y en los servicios de recursos.
SECRET_KEY = "EASYADMIN_SUPER_SECRET_KEY_REPLACE_ME_LATER"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8002/auth/token")

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

def get_current_user_data(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Decodifica y verifica la validez del token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    return token_data

def required_roles(roles: List[str]):
    """Dependencia para verificar que el rol del usuario actual sea uno de los roles requeridos."""
    def role_checker(token_data: TokenData = Depends(get_current_user_data)):
        if token_data.role not in roles:
            roles_str = " o ".join([f"'{r}'" for r in roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado. Rol '{token_data.role}' no autorizado. Se requiere rol {roles_str}.",
            )
        return token_data
    return role_checker

# ----------------------------------------------------
# 1. Instancia de FastAPI para el servicio de pedidos
# ----------------------------------------------------
# --- Instancia de FastAPI para el servicio de pedidos ---
app = FastAPI(
    title="API de Pedidos - EasyAdmin",
    description="Microservicio para gestionar los pedidos, estados y KDS.",
    version="1.1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Configuración de la Base de Datos ---
DB_USER = os.getenv("MYSQL_USER", "easyadmin_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "password_segura")
DB_HOST = os.getenv("MYSQL_HOST", "mysql_db")
DB_NAME = os.getenv("MYSQL_DATABASE", "easyadmin_db")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

Base = declarative_base()
engine = None
SessionLocal = None

# --- Modelos SQLAlchemy (Product debe existir para calcular precio) ---
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
    table_number = Column(Integer, index=True)

# --- Modelos Pydantic (Sin cambios) ---
class OrderBase(BaseModel):
    items: List[str]
    table_number: int
class OrderCreate(OrderBase): pass
class OrderResponse(BaseModel):
    id: int; items: List[str]; total: float; status: str
    created_at: datetime; updated_at: datetime; table_number: int
    class Config: from_attributes = True
    @field_validator('items', mode='before')
    @classmethod
    def split_items_string(cls, v):
        if isinstance(v, str): return [item.strip() for item in v.split(',')]
        return v
class OrderStatusUpdate(BaseModel):
    status: str
class TicketResponse(BaseModel):
    order_id: int; items: List[str]; total: float
    issued_at: datetime; table_number: int

# --- Lógica de Conexión, Sesión y WebSockets (Sin cambios) ---
class ConnectionManager:
    def __init__(self): self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, data: dict):
        message = json.dumps(data, default=str)
        for connection in self.active_connections: await connection.send_text(message)
manager = ConnectionManager()
# ... (startup_db_client y get_db) ...

@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
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

# --- Endpoints de la API de Pedidos (MODIFICADOS) ---
@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "order-service"}

# PROTEGIDO: Solo 'admin' o 'cajero' pueden crear pedidos.
@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201,
          dependencies=[Depends(required_roles(["admin", "cajero"]))])
async def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    total_price = 0.0
    for name in pedido.items:
        product = db.query(Product).filter(Product.name == name).first()
        if not product: raise HTTPException(status_code=404, detail=f"Producto '{name}' no existe.")
        total_price += product.price

    db_order = Order(
        items=", ".join(pedido.items),
        total=total_price,
        table_number=pedido.table_number
    )
    db.add(db_order); db.commit(); db.refresh(db_order)

    response_order = OrderResponse.model_validate(db_order)
    message = {"type": "new_order", "data": response_order.model_dump()}
    await manager.broadcast(message)

    return response_order

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    """Puede ser público o requerir rol 'admin' / 'cajero' / 'cocinero' (dependiendo de la necesidad). Por ahora, público."""
    return db.query(Order).all()

# PROTEGIDO: Solo 'admin' o 'cocinero' pueden actualizar el estado de un pedido (KDS).
@app.put("/pedidos/{order_id}/estado", tags=["Pedidos"], response_model=OrderResponse,
         dependencies=[Depends(required_roles(["admin", "cocinero"]))])
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
    if not order_db:
        raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")

    items_list = OrderResponse.model_validate(order_db).items

    ticket = TicketResponse(
        order_id=order_db.id,
        items=items_list,
        total=order_db.total,
        issued_at=order_db.created_at,
        table_number=order_db.table_number
)
    return ticket