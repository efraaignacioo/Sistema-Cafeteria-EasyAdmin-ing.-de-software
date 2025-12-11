# product-service/main.py
# Microservicio para la gestión de productos, categorías y configuración visual.

import os
import time
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship 
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, field_validator
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm.exc import NoResultFound

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
    version="2.3.0" 
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

# ----------------------------------------------------
# 2. MODELOS SQLALCHEMY (Base de Datos)
# ----------------------------------------------------

# MODIFICADO: Modelo de Configuración (SIN color_principal)
class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True, default=1) 
    color_secundario = Column(String(10), default="#8A9A5B") 
    modo_visual = Column(String(10), default="claro") 
    menu_title = Column(String(100), default="Menú Principal") 
    header_image_url = Column(String(255), nullable=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    price = Column(Float)
    category_id = Column(Integer, ForeignKey("categories.id")) 
    category = relationship("Category", back_populates="products") 

# ----------------------------------------------------
# 3. MODELOS PYDANTIC (Schemas)
# ----------------------------------------------------

# MODIFICADO: Schemas de Configuración (SIN color_principal)
class SettingsBase(BaseModel):
    color_secundario: str
    modo_visual: str
    menu_title: str
    header_image_url: Optional[str] = None

class SettingsResponse(SettingsBase):
    id: int
    class Config: from_attributes = True

# Schemas de Categoría
class CategoryBase(BaseModel): 
    name: str

class CategoryResponse(CategoryBase): 
    id: int 
    class Config: 
        from_attributes = True

# Schemas de Producto
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    
class ProductCreate(ProductBase):
    category_id: int 
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
    category_id: int 
    category_name: str = None 
    class Config: from_attributes = True

# ----------------------------------------------------
# 4. Lógica de Conexión y Sesión
# ----------------------------------------------------
@app.on_event("startup")
def startup_db_client():
    global engine, SessionLocal
    for attempt in range(10):
        try:
            engine = create_engine(DATABASE_URL)
            # Intentamos crear las tablas (esto se hace sin importar si ya existen)
            with engine.connect(): Base.metadata.create_all(bind=engine) 
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            print("✅ [product-service] Conexión a MySQL exitosa.")

            db = SessionLocal()
            try:
                # Si la tabla existe, verificamos si existe la fila de configuración (ID=1)
                db.query(Settings).filter(Settings.id == 1).one()
            except NoResultFound:
                # Si no existe, la creamos con valores por defecto
                initial_settings = Settings(
                    id=1,
                    # color_principal ELIMINADO del constructor
                    menu_title="Menú Principal",
                    header_image_url=None
                ) 
                db.add(initial_settings)
                db.commit()
                print("⚙️ [product-service] Fila de configuración inicial creada (ID=1).")
            finally:
                db.close()

            return
        except Exception as e:
            print(f"⚠️ [product-service] Fallo en conexión, reintentando... ({e})")
            time.sleep(5)
            if attempt == 9: raise e

def get_db():
    # Aumentamos la tolerancia aquí
    if SessionLocal is None: 
         raise HTTPException(status_code=500, detail="DB no disponible.")
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ----------------------------------------------------
# 5. ENDPOINTS DE CONFIGURACIÓN (MODIFICADOS)
# ----------------------------------------------------

@app.get("/settings", tags=["Configuración"], response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    try:
        return db.query(Settings).filter(Settings.id == 1).one()
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")

@app.put("/settings", tags=["Configuración"], response_model=SettingsResponse,
         dependencies=[Depends(required_role("admin"))])
def update_settings(new_settings: SettingsBase, db: Session = Depends(get_db)):
    settings = db.query(Settings).filter(Settings.id == 1).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Configuración no encontrada.")
    
    # Actualiza solo los campos restantes
    settings.color_secundario = new_settings.color_secundario
    settings.modo_visual = new_settings.modo_visual
    settings.menu_title = new_settings.menu_title        
    settings.header_image_url = new_settings.header_image_url 
    
    db.commit()
    db.refresh(settings)
    return settings
# ----------------------------------------------------
# 6. ENDPOINTS DE CATEGORÍAS Y PRODUCTOS
# ----------------------------------------------------
@app.get("/categories", tags=["Categorías"], response_model=List[CategoryResponse],
         dependencies=[Depends(required_role("admin"))])
def listar_categorias(db: Session = Depends(get_db)):
    return db.query(Category).all()

@app.post("/categories", tags=["Categorías"], response_model=CategoryResponse, status_code=201,
          dependencies=[Depends(required_role("admin"))])
def crear_categoria(categoria: CategoryBase, db: Session = Depends(get_db)):
    existe = db.query(Category).filter(Category.name == categoria.name).first()
    if existe:
        raise HTTPException(status_code=400, detail="La categoría ya existe.")
    
    db_category = Category(**categoria.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/categories/{category_id}", tags=["Categorías"],
            dependencies=[Depends(required_role("admin"))])
def eliminar_categoria(category_id: int, db: Session = Depends(get_db)):
    category_to_delete = db.query(Category).filter(Category.id == category_id).first()
    if not category_to_delete:
        raise HTTPException(status_code=404, detail=f"Categoría {category_id} no encontrada.")

    if db.query(Product).filter(Product.category_id == category_id).first():
        raise HTTPException(status_code=400, detail="No se puede eliminar la categoría porque tiene productos asociados.")
        
    db.delete(category_to_delete)
    db.commit()
    return {"mensaje": f"Categoría '{category_to_delete.name}' eliminada."}

@app.get("/health", tags=["Salud del Servicio"])
def health_check(): return {"status": "ok", "service": "product-service"}

@app.get("/menu", tags=["Menú"], response_model=List[ProductResponse])
def ver_menu(db: Session = Depends(get_db)):
    result = db.query(Product, Category.name.label("category_name")).outerjoin(Category).all()
    
    products_with_category_name = []
    for product_db, category_name in result:
        product_dict = product_db.__dict__
        product_dict['category_name'] = category_name or 'Sin Categoría'
        products_with_category_name.append(ProductResponse.model_validate(product_dict))

    return products_with_category_name

@app.post("/menu", tags=["Menú"], response_model=ProductResponse, status_code=201,
          dependencies=[Depends(required_role("admin"))]) 
def agregar_producto(producto: ProductCreate, db: Session = Depends(get_db)):
    category_db = db.query(Category).filter(Category.id == producto.category_id).first()
    if not category_db:
        raise HTTPException(status_code=400, detail=f"Categoría con ID {producto.category_id} no existe.")

    db_product = Product(**producto.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    product_dict = db_product.__dict__
    product_dict['category_name'] = category_db.name

    return ProductResponse.model_validate(product_dict)

@app.put("/menu/{product_id}", tags=["Menú"], response_model=ProductResponse,
         dependencies=[Depends(required_role("admin"))])
def actualizar_producto(product_id: int, producto_actualizado: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")
    
    category_id_to_use = producto_actualizado.category_id
    category_db = db.query(Category).filter(Category.id == category_id_to_use).first()
    if not category_db:
        raise HTTPException(status_code=400, detail=f"Categoría con ID {category_id_to_use} no existe.")

    update_data = producto_actualizado.model_dump()
    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    
    product_dict = db_product.__dict__
    product_dict['category_name'] = category_db.name
    
    return ProductResponse.model_validate(product_dict)

@app.delete("/menu/{product_id}", tags=["Menú"],
            dependencies=[Depends(required_role("admin"))])
def eliminar_producto(product_id: int, db: Session = Depends(get_db)):
    product_to_delete = db.query(Product).filter(Product.id == product_id).first()
    if not product_to_delete:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")
    db.delete(product_to_delete)
    db.commit()
    return {"mensaje": f"Producto '{product_to_delete.name}' eliminado."}