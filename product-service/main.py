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
    title="API de Productos (Versión Funcional)",
    description="API para gestionar los productos y pedidos de la cafetería.",
    version="1.0.0"
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

# Modelo SQLAlchemy
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    price = Column(Float)

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

# ----------------------------------------------------
# 4. Lógica de Conexión y Sesión de la Base de Datos
# ----------------------------------------------------
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    # ... (código de reintentos de conexión, sin cambios)
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
# 5. Endpoints de la API
# ----------------------------------------------------
@app.get("/health", tags=["Salud del Servicio"])
def health_check():
    return {"status": "ok"}

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

# ### RESTAURADO ### - Endpoint para eliminar productos
@app.delete("/menu/{product_id}", tags=["Menú"], summary="Eliminar un producto del menú por su ID.")
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    """Elimina un producto de la base de datos por su ID."""
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto con ID {product_id} no encontrado.")
    
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado correctamente del menú."}

