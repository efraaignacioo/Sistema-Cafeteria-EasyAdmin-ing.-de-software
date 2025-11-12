# order-service/main.py
# Este microservicio se encarga de toda la lógica de pedidos y ahora está protegido.

import os
import time
import json
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Query
# IMPORTACIONES DE SEGURIDAD
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
# FIN IMPORTACIONES DE SEGURIDAD

# --- MODIFICADO: Importaciones añadidas ---
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func, cast, Date
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List, Optional
# --- MODIFICADO: Importamos 'date', 'datetime' y 'Enum' ---
from datetime import datetime, date
from enum import Enum
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
    version="1.2.2" # Versión con corrección de bugs 500 (TypeError y ValidationError)
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
    price = Column(Float) # Esta columna permite NULL

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    items = Column(String(500)) # Esta columna permite NULL
    total = Column(Float) # Esta columna permite NULL
    # Status puede ser: "pendiente", "en preparacion", "listo", "Pagado"
    status = Column(String(50), default="pendiente")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    table_number = Column(Integer, index=True) # Esta columna permite NULL
    # --- NUEVO: Columna para RF15 ---
    payment_method = Column(String(50), nullable=True) # "efectivo", "tarjeta"

# --- Modelos Pydantic (Sin cambios) ---
class OrderBase(BaseModel):
    items: List[str]
    table_number: int
class OrderCreate(OrderBase): pass

# --- CORREGIDO: Modelo de Respuesta (FIX 2) ---
# Hacemos Opcionales los campos que pueden ser NULL en la BD
# para evitar el error 500 de serialización en GET /pedidos.
class OrderResponse(BaseModel):
    id: int
    items: List[str] # El validador de abajo ya maneja items=None
    total: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    table_number: Optional[int] = None
    payment_method: Optional[str] = None
    
    class Config: from_attributes = True
    
    # Este validador estaba bien, lo mantenemos.
    @field_validator('items', mode='before')
    @classmethod
    def split_items_string(cls, v):
        """
        Toma el string de la base de datos y lo convierte en lista.
        Maneja el caso donde 'items' pueda ser None si la BD lo permite.
        """
        if isinstance(v, str): 
            if v == "":
                return []
            return [item.strip() for item in v.split(',')]
        if v is None:
            # Si es None, devolvemos una lista vacía
            return []
        return v

class OrderStatusUpdate(BaseModel):
    status: str # "pendiente", "en preparacion", "listo"

class TicketResponse(BaseModel):
    order_id: int
    items: List[str]
    total: float
    issued_at: datetime
    table_number: int
    payment_method: Optional[str] = None

# --- NUEVO: Enum y Modelo para RF15 ---
class PaymentMethod(str, Enum):
    tarjeta = "tarjeta"
    efectivo = "efectivo"

class PaymentRequest(BaseModel):
    method: PaymentMethod

class DailyReport(BaseModel):
    fecha: date
    total_ventas: float

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

# --- LECTOR DE TOKENS PARA WEBSOCKET ---
# No podemos usar "Depends" en WebSockets, así que creamos una función
# helper que hace el mismo trabajo que get_current_user_data.
def verify_token_for_websocket(token: str) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado para WebSocket",
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
# --- FIN LECTOR ---


@app.websocket("/ws/kds")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)  # <-- (Paso A) Leemos el token de la URL
):
    try:
        # --- (Paso B) Validamos el token ---
        token_data = verify_token_for_websocket(token)
        
        # --- (Paso C) Verificamos el rol ---
        # Solo "admin" o "cocinero" pueden conectarse al KDS
        if token_data.role not in ["admin", "cocinero"]:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rol no autorizado")
            return

        # --- (Paso D) Si todo es válido, nos conectamos ---
        await manager.connect(websocket)
        print(f"KDS conectado: {token_data.username} (Rol: {token_data.role})") # Log de éxito
        
        while True:
            await websocket.receive_text()
            
    except HTTPException:
        # Si el token es inválido, cerramos la conexión
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido o expirado")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("KDS desconectado.")

# --- Endpoints de la API de Pedidos (MODIFICADOS) ---
@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "order-service"}

# --- CORREGIDO: crear_pedido (FIX 1) ---
# Añadida validación para product.price
@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201,
          dependencies=[Depends(required_roles(["admin", "cajero"]))])
async def crear_pedido(pedido: OrderCreate, db: Session = Depends(get_db)):
    total_price = 0.0
    for name in pedido.items:
        product = db.query(Product).filter(Product.name == name).first()
        
        # --- INICIO DE CORRECCIÓN (FIX 1) ---
        if not product: 
            raise HTTPException(status_code=404, detail=f"Producto '{name}' no existe.")
        
        # Esta es la validación que faltaba. Si el precio es NULL, evitamos el TypeError
        if product.price is None:
            print(f"Error 500: El producto '{name}' (ID: {product.id}) no tiene precio asignado (es NULL).")
            raise HTTPException(status_code=500, detail=f"El producto '{name}' no tiene un precio asignado en la base de datos.")
        
        total_price += product.price
        # --- FIN DE CORRECCIÓN ---

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
    # El bug 500 estaba aquí: si un 'order' tenía 'total=None' o 'table_number=None',
    # la serialización fallaba. El modelo OrderResponse corregido (FIX 2)
    # ahora maneja esto.
    return db.query(Order).all()

# --- NUEVO: Endpoint para RF18 (Ver historial de un pedido) ---
@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse],
         dependencies=[Depends(required_roles(["admin", "cocinero"]))])
def ver_pedidos(db: Session = Depends(get_db)):
    """
    (RF18) Permite al cajero o admin ver los detalles de un pedido específico 
    por su ID para verificar pagos o historial.
    """
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} no encontrado.")
    
    # Esto también fallaba con 500 si el pedido tenía campos NULL.
    # Ahora está corregido por OrderResponse (FIX 2).
    return order_db

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


@app.put("/pedidos/{order_id}/pagar", tags=["Pedidos"], response_model=OrderResponse,
         dependencies=[Depends(required_roles(["admin", "cajero"]))])
async def procesar_pago_pedido(order_id: int, payment: PaymentRequest, db: Session = Depends(get_db)):
    """
    (RF15) Permite al cajero marcar un pedido como 'Pagado' y registrar el
    método de pago (efectivo o tarjeta).
    """
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} no encontrado.")

    
    if order_db.status == "Pagado":
        raise HTTPException(status_code=409, detail="El pedido ya ha sido pagado.") 

   
    order_db.status = "Pagado"
    order_db.payment_method = payment.method
    
    db.commit()
    db.refresh(order_db)

    
    response_order = OrderResponse.model_validate(order_db)
    message = {"type": "status_update", "data": response_order.model_dump()}
    await manager.broadcast(message)

    return response_order



@app.get("/pedidos/{order_id}/ticket", tags=["Pedidos"], response_model=TicketResponse,
         dependencies=[Depends(required_roles(["admin", "cajero"]))])
def generar_ticket(order_id: int, db: Session = Depends(get_db)):
   
    order_db = db.query(Order).filter(Order.id == order_id).first()
    if not order_db:
        # --- CORREGIDO: El código de estado era 4404, debe ser 404 ---
        raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")

    # --- NUEVA VALIDACIÓN RF16 ---
    if order_db.status != "Pagado":
        raise HTTPException(status_code=400, detail="El ticket solo puede generarse para pedidos pagados.")

    # Esta línea usa OrderResponse.model_validate, por lo que también
    # se beneficia de la corrección del validador.
    items_list = OrderResponse.model_validate(order_db).items

    # --- CORRECCIÓN ADICIONAL ---
    # Si el pedido tiene total=None o table_number=None (por FIX 2),
    # el modelo TicketResponse (que es estricto) fallaría.
    # Debemos validar aquí.
    if order_db.total is None or order_db.table_number is None or order_db.created_at is None:
         raise HTTPException(status_code=500, detail=f"No se puede generar ticket. El pedido {order_id} tiene datos incompletos (total, mesa o fecha es NULL).")

    ticket = TicketResponse(
        order_id=order_db.id,
        items=items_list,
        total=order_db.total,
        issued_at=order_db.created_at,
        table_number=order_db.table_number,
        payment_method=order_db.payment_method 
    )
    return ticket


@app.get("/reporte/diario", tags=["Reportes"], response_model=DailyReport,
         dependencies=[Depends(required_roles(["admin"]))])
def obtener_reporte_diario(
    db: Session = Depends(get_db),
    fecha: Optional[date] = None
):

    if fecha is None:
        fecha = datetime.now().date()

    total_ventas = db.query(func.sum(Order.total)).filter(
        cast(Order.created_at, Date) == fecha,
        Order.status == "Pagado" 
    ).scalar()

    if total_ventas is None:
        total_ventas = 0.0

    return DailyReport(fecha=fecha, total_ventas=total_ventas)