# order-service/main.py
# Microservicio para pedidos, mesas, KDS y Notificaciones.

import os
import time
import json
import uuid
import io
import qrcode
import requests # <-- CLAVE: Importado para la comunicación entre servicios
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Query
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func, cast, Date
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm.exc import NoResultFound # Para buscar la mesa

# ----------------------------------------------------
# 0. CONFIGURACIÓN DE SEGURIDAD
# ----------------------------------------------------
SECRET_KEY = "EASYADMIN_SUPER_SECRET_KEY_REPLACE_ME_LATER"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8002/auth/token")

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

def get_current_user_data(token: str = Depends(oauth2_scheme)) -> TokenData:
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
    def role_checker(token_data: TokenData = Depends(get_current_user_data)):
        if token_data.role not in roles:
            roles_str = " o ".join([f"'{r}'" for r in roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado. Rol '{token_data.role}' no autorizado.",
            )
        return token_data
    return role_checker

# ----------------------------------------------------
# 1. Instancia de FastAPI
# ----------------------------------------------------
app = FastAPI(
    title="API de Pedidos y Mesas - EasyAdmin",
    version="1.4.1" 
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- Base de Datos ---
DB_USER = os.getenv("MYSQL_USER", "easyadmin_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "password_segura")
DB_HOST = os.getenv("MYSQL_HOST", "mysql_db")
DB_NAME = os.getenv("MYSQL_DATABASE", "easyadmin_db")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# --- Telegram Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Frontend Config ---
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500") # <-- Leemos la URL del frontend

Base = declarative_base()
engine = None
SessionLocal = None

# ----------------------------------------------------
# 2. MODELOS DE BASE DE DATOS (SQLAlchemy)
# ----------------------------------------------------

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    items = Column(String(500))
    total = Column(Float)
    status = Column(String(50), default="pendiente")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    table_number = Column(Integer, index=True) 
    payment_method = Column(String(50), nullable=True)
    qr_id_used = Column(String(36), nullable=True)

class Table(Base):
    __tablename__ = "tables"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True) 
    section = Column(String(50))           
    qr_id = Column(String(36), unique=True, index=True) 

# ----------------------------------------------------
# 3. MODELOS PYDANTIC (Schemas)
# ----------------------------------------------------
class OrderBase(BaseModel):
    items: List[str]
    table_number: int 
    qr_id: Optional[str] = None 

class OrderCreate(OrderBase): pass

class OrderResponse(BaseModel):
    id: int
    items: List[str]
    total: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    table_number: Optional[int] = None
    payment_method: Optional[str] = None
    class Config: from_attributes = True
    @field_validator('items', mode='before')
    @classmethod
    def split_items(cls, v):
        if isinstance(v, str): return [x.strip() for x in v.split(',')] if v else []
        return v or []

class OrderStatusUpdate(BaseModel): status: str
class PaymentRequest(BaseModel): method: str
class DailyReport(BaseModel): fecha: date; total_ventas: float
class TicketResponse(BaseModel):
    order_id: int; items: List[str]; total: float; issued_at: datetime; table_number: int; payment_method: Optional[str]

class TableCreate(BaseModel):
    name: str
    section: str

class TableResponse(BaseModel):
    id: int
    name: str
    section: str
    qr_id: str
    class Config: from_attributes = True

# ----------------------------------------------------
# 4. FUNCIONES AUXILIARES
# ----------------------------------------------------

# NUEVA FUNCIÓN: Obtiene los precios reales del Product Service
def fetch_product_prices() -> dict:
    """Obtiene un diccionario de precios {nombre: precio} desde el product-service
       usando el nombre del servicio Docker."""
    # Usamos el nombre del servicio Docker 'product-service' y el puerto 8000
    PRODUCT_SERVICE_URL = "http://product-service:8000/menu"
    
    try:
        # Se necesita un timeout en peticiones entre microservicios
        response = requests.get(PRODUCT_SERVICE_URL, timeout=5)
        response.raise_for_status() # Lanza un error para códigos de estado 4xx/5xx
        
        products = response.json()
        
        # Mapea los productos a un diccionario {nombre: precio}
        price_map = {product['name']: product['price'] for product in products}
        
        return price_map

    except requests.exceptions.RequestException as e:
        # Esto ocurre si el product-service está caído o no es accesible
        print(f"❌ Error al conectar con product-service para obtener precios: {e}")
        return {}


# MODIFICADO: Función para calcular el total usando los precios reales
def calcular_total_pedido(items: List[str]) -> float:
    """Calcula el total real del pedido consultando los precios del product-service."""
    
    price_map = fetch_product_prices()
    
    if not price_map:
        # Si la consulta falla, usamos 0.0 o un precio fijo, pero esto indicarÃ¡ una venta fallida
        # En este caso, lo dejamos en 0.0 y el reporte lo ignorarÃ¡ o serÃ¡ 0
        FALLBACK_PRICE = 0.0
        print(f"⚠️ Fallback: Usando precio fijo de {FALLBACK_PRICE} por ítem (el product-service no respondió).")
        return len(items) * FALLBACK_PRICE
        
    total = 0.0
    for item_name in items:
        # Utiliza el precio real o 0.0 si el producto no se encuentra (indicando un error de inventario)
        price = price_map.get(item_name, 0.0) 
        total += price
        
    return total


def enviar_notificacion_telegram(mensaje: str):
    """Envía un mensaje al grupo de Telegram configurado."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram no configurado (Falta TOKEN o CHAT_ID). Omitiendo notificación.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"✅ Notificación enviada a Telegram: {mensaje}")
        else:
            print(f"❌ Error enviando a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Excepción enviando a Telegram: {e}")

# ----------------------------------------------------
# 5. WEBSOCKETS Y CONEXIÓN DB
# ----------------------------------------------------
class ConnectionManager:
    def __init__(self): self.active_connections: List[WebSocket] = []
    async def connect(self, ws: WebSocket): await ws.accept(); self.active_connections.append(ws)
    def disconnect(self, ws: WebSocket): self.active_connections.remove(ws)
    async def broadcast(self, data: dict):
        for conn in self.active_connections: await conn.send_text(json.dumps(data, default=str))
manager = ConnectionManager()

@app.on_event("startup")
def startup():
    global engine, SessionLocal
    for _ in range(10):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect(): Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine)
            print("✅ [order-service] Conectado a MySQL.")
            return
        except Exception: time.sleep(5)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def verify_ws_token(token: str):
    try:
        print(f"🔍 Verificando token: {token[:15]}...")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if not payload.get("role"): 
            print("❌ El token no tiene campo 'role'")
            raise Exception("Token sin rol")
            
        print(f"✅ Token válido. Usuario: {payload.get('sub')}, Rol: {payload.get('role')}")
        return payload
    except Exception as e:
        print(f"❌ Error al decodificar token WS: {str(e)}")
        return None

@app.websocket("/ws/kds")
async def ws_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = verify_ws_token(token)
    if not payload or payload["role"] not in ["admin", "cocinero"]:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

# ----------------------------------------------------
# 6. ENDPOINTS
# ----------------------------------------------------

@app.post("/tables", tags=["Mesas"], response_model=TableResponse, status_code=201,
          dependencies=[Depends(required_roles(["admin"]))])
def crear_mesa(mesa: TableCreate, db: Session = Depends(get_db)):
    existe = db.query(Table).filter(Table.name == mesa.name).first()
    if existe: raise HTTPException(status_code=400, detail="El ID de la mesa ya está en uso.")
    nuevo_qr_id = str(uuid.uuid4())
    nueva_mesa = Table(name=mesa.name, section=mesa.section, qr_id=nuevo_qr_id)
    db.add(nueva_mesa); db.commit(); db.refresh(nueva_mesa)
    return nueva_mesa

@app.get("/tables", tags=["Mesas"], response_model=List[TableResponse],
         dependencies=[Depends(required_roles(["admin", "cajero"]))])
def listar_mesas(db: Session = Depends(get_db)):
    return db.query(Table).all()

@app.get("/tables/{table_id}/qr", tags=["Mesas"])
def obtener_qr_mesa(table_id: int, db: Session = Depends(get_db)):
    mesa = db.query(Table).filter(Table.id == table_id).first()
    if not mesa: raise HTTPException(status_code=404, detail="Mesa no encontrada")
    
    # Usamos la variable de entorno FRONTEND_URL
    qr_content = f"{FRONTEND_URL}/index.html?mesa={mesa.qr_id}"
    
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(qr_content); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201)
async def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    mesa_numero = pedido.table_number
    qr_usado = None
    if pedido.qr_id:
        mesa_db = db.query(Table).filter(Table.qr_id == pedido.qr_id).first()
        if not mesa_db: raise HTTPException(status_code=404, detail="Código QR inválido.")
        mesa_numero = mesa_db.id
        qr_usado = pedido.qr_id

    # CLAVE: Calculamos el total usando el fetch al product-service
    total_price = calcular_total_pedido(pedido.items)

    db_order = Order(items=", ".join(pedido.items), total=total_price, table_number=mesa_numero, qr_id_used=qr_usado)
    db.add(db_order); db.commit(); db.refresh(db_order)
    resp = OrderResponse.model_validate(db_order)
    
    await manager.broadcast({"type": "new_order", "data": resp.model_dump()})
    return resp

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.get("/pedidos/{order_id}", tags=["Pedidos"], response_model=OrderResponse)
def ver_detalle_pedido(order_id: int, db: Session = Depends(get_db)):
    res = db.query(Order).filter(Order.id == order_id).first()
    if not res: raise HTTPException(404, "No encontrado")
    return res

@app.put("/pedidos/{order_id}/estado", tags=["Pedidos"], response_model=OrderResponse,
         dependencies=[Depends(required_roles(["admin", "cocinero"]))])
async def actualizar_estado(order_id: int, st: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(404)
    
    order.status = st.status
    db.commit(); db.refresh(order)
    resp = OrderResponse.model_validate(order)
    
    # --- NOTIFICACIÓN TELEGRAM (RF20) ---
    if st.status == "listo":
        msg = f"✅ *¡Pedido #{order.id} LISTO!*\n🍽 Mesa: {order.table_number}\n📦 Items: {order.items}"
        enviar_notificacion_telegram(msg)
    # ------------------------------------

    await manager.broadcast({"type": "status_update", "data": resp.model_dump()})
    return resp

@app.put("/pedidos/{order_id}/pagar", tags=["Pedidos"], response_model=OrderResponse,
         dependencies=[Depends(required_roles(["admin", "cajero"]))])
async def pagar_pedido(order_id: int, pay: PaymentRequest, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(404)
    if order.status == "Pagado": raise HTTPException(409, "Ya pagado")
    
    # Recalculamos el total antes de pagar (si es necesario)
    if order.total == 0.0:
        items_list = [item.strip() for item in order.items.split(',') if item.strip()]
        order.total = calcular_total_pedido(items_list)

    order.status = "Pagado"; order.payment_method = pay.method
    db.commit(); db.refresh(order)
    resp = OrderResponse.model_validate(order)
    await manager.broadcast({"type": "status_update", "data": resp.model_dump()})
    return resp

@app.get("/pedidos/{order_id}/ticket", tags=["Pedidos"], response_model=TicketResponse,
         dependencies=[Depends(required_roles(["admin", "cajero"]))])
def ticket(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or order.status != "Pagado": raise HTTPException(400, "Requiere pago")
    return TicketResponse(
        order_id=order.id, items=OrderResponse.model_validate(order).items,
        total=order.total, issued_at=order.created_at,
        table_number=order.table_number, payment_method=order.payment_method
    )

@app.get("/reporte/diario", tags=["Reportes"], response_model=DailyReport,
         dependencies=[Depends(required_roles(["admin"]))])
def reporte(fecha: Optional[date] = None, db: Session = Depends(get_db)):
    fecha = fecha or datetime.now().date()
    total = db.query(func.sum(Order.total)).filter(
        cast(Order.created_at, Date) == fecha, Order.status == "Pagado"
    ).scalar() or 0.0
    return DailyReport(fecha=fecha, total_ventas=total)