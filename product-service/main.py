# product-service/main.py
# Este microservicio ahora solo se encarga de la gestión de productos.

import os
import time
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# --- Instancia de FastAPI para el servicio de productos ---
app = FastAPI(
    title="API de Productos - EasyAdmin",
    description="Microservicio para gestionar el menú de la cafetería.",
    version="2.0.0" # Versión 2.0 por refactorización
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
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    price = Column(Float)

# --- Modelos Pydantic ---
class ProductBase(BaseModel):
    name: str
    description: str
    price: float
class ProductCreate(ProductBase): pass
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

# --- Endpoints de la API de Productos ---
@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "product-service"}

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
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado."}

