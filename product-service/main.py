# product-service/main.py
# Microservicio para la gestión de productos, con seguridad por roles JWT.

import os
import time
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# ----------------------------------------------------
# 0. CONFIGURACIÓN Y LÓGICA DE SEGURIDAD (AUTORIZACIÓN)
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

def required_role(role: str):
    def role_checker(token_data: TokenData = Depends(get_current_user_data)):
        if token_data.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso denegado. Rol '{token_data.role}' no autorizado. Se requiere rol '{role}'.",
            )
        return token_data
    return role_checker

# ----------------------------------------------------
# 1. Creación de la Instancia de FastAPI
# ----------------------------------------------------
app = FastAPI(
    title="API de Productos - EasyAdmin",
    description="Microservicio para gestionar el menú de la cafetería.",
    version="2.0.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
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

# --- Modelos SQLAlchemy ---
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    price = Column(Float)

# --- Modelos Pydantic ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None

class ProductCreate(ProductBase):
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is None:
            raise ValueError("El precio es un campo requerido al crear.")
        if v <= 0:
            raise ValueError("El precio debe ser un número positivo.")
        return v

class ProductResponse(ProductBase):
    id: int
    class Config: from_attributes = True

# --- Lógica de Conexión y Sesión ---
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    for attempt in range(10):
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect(): Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print("✅ [product-service] Conexión a MySQL exitosa.")
            return
        except Exception as e:
            print(f"⚠️ [product-service] Fallo en conexión, reintentando... ({e})")
            time.sleep(5)
            if attempt == 9: raise e

def get_db():
    if SessionLocal is None: raise HTTPException(status_code=500, detail="DB no disponible.")
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- Endpoints ---
@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "product-service"}

@app.get("/menu", tags=["Menú"], response_model=List[ProductResponse])
def ver_menu(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.post("/menu", tags=["Menú"], response_model=ProductResponse, status_code=201,
          dependencies=[Depends(required_role("admin"))]) 
def agregar_producto(producto: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**producto.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.put("/menu/{product_id}", tags=["Menú"], response_model=ProductResponse,
         dependencies=[Depends(required_role("admin"))])
def actualizar_producto(product_id: int, producto_actualizado: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")
    
    update_data = producto_actualizado.model_dump()
    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/menu/{product_id}", tags=["Menú"],
            dependencies=[Depends(required_role("admin"))])
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado."}