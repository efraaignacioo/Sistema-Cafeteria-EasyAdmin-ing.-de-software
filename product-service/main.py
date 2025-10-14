# product-service/main.py

import os
import time
<<<<<<< Updated upstream
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
=======
import json
from fastapi import FastAPI, HTTPException, Depends
# *** IMPORTACIÓN CORREGIDA: Se añade DateTime y func de SQLAlchemy ***
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func 
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
>>>>>>> Stashed changes

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI (¡PASO CLAVE!)
#    Esto debe ocurrir ANTES de usar '@app'.
# ----------------------------------------------------
app = FastAPI(
<<<<<<< Updated upstream
    title="Servicio de Productos - EasyAdmin",
    description="API para gestionar los productos de la cafetería.",
=======
    title="API de Productos y Pedidos (Versión Funcional)",
    description="API para gestionar los productos y pedidos de la cafetería.",
>>>>>>> Stashed changes
    version="1.0.0"
)

# ----------------------------------------------------
<<<<<<< Updated upstream
# 2. Variables de Entorno y Conexión a la Base de Datos
=======
# 2. Configuración de la Base de Datos y Modelos SQLAlchemy
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
# AÑADIDO: Un modelo de ejemplo para que 'Base.metadata.create_all' funcione.
# Debes reemplazar esto con tus modelos reales (ej: Producto).
=======
# Modelo SQLAlchemy: Product
>>>>>>> Stashed changes
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    description = Column(String(255))
    price = Column(Float)
<<<<<<< Updated upstream
    
# ----------------------------------------------------
# 4. Evento de Arranque para Conectar a la DB
#    Ahora 'app' ya existe y este código es válido.
=======

# Modelo SQLAlchemy para Pedidos (Corregidos nombres de columnas y tipos)
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    # Nombre de columna corregido a 'items_json'
    items_json = Column(String(1024), nullable=False) 
    total_price = Column(Float, nullable=False)
    status = Column(String(50), default="Pendiente")
    client_name = Column(String(100), nullable=True)
    # Nombre de columna corregido a 'created_at'
    created_at = Column(DateTime, default=func.now()) 
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# ----------------------------------------------------
# 3. Modelos Pydantic (para validación en la API)
# ----------------------------------------------------
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

# Modelos Pydantic para pedidos
class OrderItem(BaseModel):
    product_id: int = Field(..., description="ID del producto")
    quantity: int = Field(..., gt=0, description="Cantidad del producto")

class OrderCreate(BaseModel):
    items: List[OrderItem] = Field(..., description="Lista y cantidad de items en el pedido")
    client_name: Optional[str] = Field(None, description="Nombre del cliente")

# Modelo para respuesta de pedidos (Corregido nombre del campo)
class OrderResponse(BaseModel):
    id : int
    # Nombre de campo corregido a 'items_json'
    items_json: str = Field(..., description="Detalles serializados del pedido") 
    total_price: float
    status: str
    client_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------------------------------------------
# 4. Lógica de Conexión y Sesión de la Base de Datos
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            engine.connect()
            
            # Si la conexión es exitosa, creamos la sesión y las tablas
            # AÑADIDO: Faltaba importar 'sessionmaker'.
=======
            # Aquí se crean ambas tablas: 'products' y 'orders'
            Base.metadata.create_all(bind=engine) 
>>>>>>> Stashed changes
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            Base.metadata.create_all(bind=engine) # Esto creará la tabla 'products'
            
            print("product-service | ✅ Conexión a MySQL exitosa y tablas creadas.")
            return
        
        except Exception as e:
<<<<<<< Updated upstream
            print(f"product-service | ⚠️  Fallo en la conexión: {e}")
            if attempt == max_attempts - 1:
                print(f"product-service | ❌ ERROR FATAL: Fallo al conectar a la DB después de {max_attempts} intentos.")
=======
            # Si hay un error de importación (como 'func' no definido), el código falla aquí.
            time.sleep(5)
            if attempt == max_attempts - 1:
                # Imprimir el error al final del intento, ayuda a diagnosticar
                print(f"Error al conectar/crear tablas: {e}") 
>>>>>>> Stashed changes
                raise e

            time.sleep(5)

# ----------------------------------------------------
# 5. Endpoint de Salud (Health Check)
# ----------------------------------------------------
@app.get("/health", tags=["Salud del Servicio"])
def health_check():
<<<<<<< Updated upstream
    """Verifica el estado general del microservicio y su conexión a MySQL."""
    if engine and SessionLocal:
        return {"status": "ok", "service": "product-service", "db_status": "connected"}
    else:
        raise HTTPException(status_code=503, detail="Servicio inactivo: La conexión a la base de datos falló durante el arranque.")

# ----------------------------------------------------
# 6. Endpoints de tu API (CRUD de Productos)
#    ... (El resto de tus endpoints CRUD RF01, RF02, etc. van aquí) ...
# ----------------------------------------------------
=======
    return {"status": "ok"}

# Endpoints de /menu
@app.get("/menu", tags=["Menú"], response_model=List[ProductResponse])
def ver_menu(db: Session = Depends(get_db)):
    """Obtiene todos los productos de la base de datos."""
    return db.query(Product).all()

@app.post("/menu", tags=["Menú"], response_model=ProductResponse, status_code=201)
def agregar_producto(producto: ProductCreate, db: Session = Depends(get_db)):
    """Crea un nuevo producto en la base de datos."""
    db_product = Product(**producto.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/menu/{product_id}", tags=["Menú"], summary="Eliminar un producto del menú por su ID.")
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    """Elimina un producto de la base de datos por su ID."""
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado.")
    
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado correctamente del menú"}

# Endpoints de /pedidos
@app.post("/pedidos", tags=["Pedidos"], response_model=OrderResponse, status_code=201)
def crear_pedido(pedido_in: OrderCreate, db: Session = Depends(get_db)):
    """Crea un nuevo pedido y lo guarda en la base de datos."""
    total_price = 0.0
    order_details = []

    # 1. Verificar productos y calcular el total
    for item in pedido_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto con ID {item.product_id} no encontrado en el menú.")
        
        subtotal = product.price * item.quantity
        total_price += subtotal

        order_details.append({
            "product_id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": item.quantity,
            "subtotal": round(subtotal, 2)
        })

    # 2. Crear el objeto de SQLAlchemy
    db_order = Order(
        items_json=json.dumps(order_details),
        total_price=round(total_price, 2),
        client_name=pedido_in.client_name,
        status="Pendiente"
    )

    # 3. Guardar en la base de datos
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    return db_order

@app.get("/pedidos", tags=["Pedidos"], response_model=List[OrderResponse])
def ver_pedidos(db: Session = Depends(get_db)):
    """Obtiene la lista completa de pedidos desde la base de datos."""
    return db.query(Order).all()

# Endpoint para ver un solo pedido por ID (útil para verificar)
@app.get("/pedidos/{order_id}", tags=["Pedidos"], response_model=OrderResponse)
def ver_pedido_por_id(order_id: int, db: Session = Depends(get_db)):
    """Obtiene un pedido específico por su ID."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Pedido con ID {order_id} no encontrado.")
    return order
>>>>>>> Stashed changes
