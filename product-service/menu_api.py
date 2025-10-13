from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

#Prueba de menu
menu = {
    "cafecito": 2500,
    "tostada": 1750,
    "empanada": 2000,
    "jugo": 1500,
    "té" : 1200,
    "chocolate": 3000,
}

#Lista de pedidos
pedidos = []
pedidos_id_counter = 1

#Modelo para los pedidos
class Pedido(BaseModel):
    productos: list[str]

#Funcion para crear la app
app = FastAPI(
    title="API del Menú del Restaurante",
    description="Permite consultar, agregar y eliminar platos del menú.",
    version="1.0"
)

#Modelo de datos para el producto
class Producto(BaseModel):
    nombre: str
    precio: int

#Ver el menu
@app.get("/menu", tags=["Menú"], summary="Ver el menú completo.")
def ver_menu():
    return{"Menú": menu}

#Agregar producto
@app.post("/menu", tags=["Menú"], summary="Agregar un nuevo producto al menú.")
def agregar_producto(plato: Producto):
    if plato.nombre in menu:
        raise HTTPException(status_code=400, detail="El producto ya existe en el menú.")
    menu[plato.nombre] = plato.precio
    return {"mensaje": f"Producto '{plato.nombre}' agregado correctamente al menú."}

#Eliminar producto
@app.delete("/menu/{nombre}", tags=["Menú"], summary="Eliminar un producto del menú por su nombre.")
def eliminar_producto(nombre: str):
    if nombre not in menu:
        raise HTTPException(status_code=404, detail="El producto no existe en el menú.")
    del menu[nombre]
    return{"mensaje": f"Producto '{nombre}' eliminado correctamente del menú."}

#Crear pedido
@app.post("/pedidos", tags=["Pedidos"], summary="Crear un nuevo pedido.")
def crear_pedido(pedido: Pedido):
    global  pedidos_id_counter
# Validar que todos los productos existan en el menú
    for producto in pedido.productos:
        if producto not in menu:
            raise HTTPException(status_code=400, detail=f"El producto '{producto}' no existe en el menú.")
    nuevo_pedido = {
        "id": pedidos_id_counter,
        "productos": nuevo_pedido.productos,
 #       "total": total,
        "estado": "pendiente"
    }
    pedidos.append(pedido)
    pedidos_id_counter += 1
    return {"mensaje": "Pedido creado correctamente.", "pedido": pedido}

#Ver los pedidos
@app.get("/pedidos", tags=["Pedidos"], summary="Ver todos los pedidos.")
def ver_pedidos():
    return {"pedidos": pedidos}

#Ver un pedido por id
@app.get("/pedidos/{pedido_id}", tags=["Pedidos"], summary="Ver un pedido por su ID.")
def ver_pedido(pedido_id: int):
    for pedido in pedidos:
        if pedido["id"] == pedido_id:
            return {"pedido": pedido}
    raise HTTPException(status_code=404, detail="Pedido no encontrado.")