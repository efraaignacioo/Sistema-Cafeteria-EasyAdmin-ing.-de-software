// app.js COMPLETAMENTE ACTUALIZADO con Total del Carrito y Texto Siempre Oscuro

let carrito = []; // Almacena solo los nombres de los productos
let productosData = {}; // Almacena datos completos (nombre, precio, descripción) para referencia
let qrIdMesa = null; 

document.addEventListener('DOMContentLoaded', () => {
    // 1. DETECTAR MESA DESDE LA URL
    const params = new URLSearchParams(window.location.search);
    qrIdMesa = params.get('mesa');

    if (qrIdMesa) {
        console.log("¡Cliente sentado en una mesa! QR ID:", qrIdMesa);
    } else {
        console.log("Modo visualización (Sin mesa)");
    }
    
    cargarSettingsYMenu();
    setupCarrito();
});

async function cargarSettingsYMenu() {
    try {
        const response = await fetch('http://127.0.0.1:8000/settings');
        if (response.ok) {
            const settings = await response.json();
            
            // 1. Aplicar Título e Imagen
            document.getElementById('main-menu-title').textContent = settings.menu_title;
            
            const headerImage = document.getElementById('header-image');
            if (settings.header_image_url) {
                headerImage.src = settings.header_image_url;
                headerImage.style.display = 'block';
            } else {
                headerImage.style.display = 'none';
            }
            
            // 2. Aplicar Colores y Fondo
            aplicarColores(settings);
        }
    } catch (e) {
        console.error("Error al cargar configuración visual:", e);
    }
    cargarMenu();
}

// MODIFICADO: Mantiene los colores de texto oscuros en AMBOS modos
function aplicarColores(settings) {
    const root = document.documentElement;
    
    // Solo aplicamos el color secundario (acento para botones/título/texto)
    root.style.setProperty('--color-secundario', settings.color_secundario);

    // 2. Aplicar el modo visual (blanco/negro)
    if (settings.modo_visual === 'oscuro') {
        // Modo oscuro: Colores de Fondo y Estampado
        root.style.setProperty('--bg-general', '#F9F5EF'); // Color base fijo para el recuadro (mantener fondo claro)
        root.style.setProperty('--bg-tarjeta', '#FFFFFF');
        
        // CLAVE: MANTENEMOS LOS COLORES DE TEXTO OSCUROS
        root.style.setProperty('--color-texto-principal', '#333'); 
        root.style.setProperty('--color-texto-secundario', '#555');
        root.style.setProperty('--color-separador', '#eee');
        
        // Activar imagen de modo oscuro
        root.style.setProperty('--bg-image-url', 'url("Fondo Oscuro.jpg")'); 

    } else {
        // Modo claro: Colores por defecto
        root.style.setProperty('--bg-general', '#F9F5EF'); // Color base fijo para el recuadro
        root.style.setProperty('--bg-tarjeta', '#FFFFFF');
        
        // Colores oscuros por defecto
        root.style.setProperty('--color-texto-principal', '#333'); 
        root.style.setProperty('--color-texto-secundario', '#555');
        root.style.setProperty('--color-separador', '#eee');
        
        // Activar imagen de modo claro
        root.style.setProperty('--bg-image-url', 'url("Fondo Blanco.jpg")'); 
    }
}


function cargarMenu() {
    fetch('http://127.0.0.1:8000/menu')
        .then(r => r.json())
        .then(productos => {
            // Guardamos los datos de los productos en la variable global
            productos.forEach(p => {
                productosData[p.name] = p;
            });
            mostrarMenu(productos);
        })
        .catch(e => console.error(e));
}

// MODIFICADO: Añade funcionalidad de clic para ver la descripción
function mostrarMenu(productos) {
    const container = document.getElementById('menu-container');
    container.innerHTML = ''; 

    const productosPorCategoria = productos.reduce((acc, prod) => {
        const categoria = prod.category_name || 'Sin Categoría';
        if (!acc[categoria]) {
            acc[categoria] = [];
        }
        acc[categoria].push(prod);
        return acc;
    }, {});
    
    for (const categoria in productosPorCategoria) {
        
        const categoryContainer = document.createElement('div');
        categoryContainer.className = 'category';
        
        const title = document.createElement('h2');
        title.textContent = categoria;
        categoryContainer.appendChild(title);
        
        productosPorCategoria[categoria].forEach(prod => {
            const item = document.createElement('div');
            item.className = 'menu-item';
            
            // Hacemos el nombre del producto clickeable
            const nameSpan = document.createElement('span');
            nameSpan.innerHTML = `<strong>${prod.name}</strong> ($${prod.price})`;
            nameSpan.style.cursor = 'pointer'; // Indicador visual
            nameSpan.addEventListener('click', () => {
                mostrarDescripcion(prod.name);
            });

            const addButton = document.createElement('button');
            addButton.className = 'add-button';
            addButton.textContent = '+';
            addButton.dataset.name = prod.name;
            addButton.addEventListener('click', () => {
                carrito.push(prod.name);
                alert(`Añadido: ${prod.name}`);
                actualizarBotonCarrito();
            });

            item.appendChild(nameSpan);
            item.appendChild(addButton);
            categoryContainer.appendChild(item);
        });
        
        container.appendChild(categoryContainer);
    }
}

// NUEVA FUNCIÓN: Muestra la descripción
function mostrarDescripcion(productName) {
    const prod = productosData[productName];
    if (prod) {
        alert(`
--- ${prod.name} ---
Precio: $${prod.price}
Descripción: ${prod.description || 'No disponible'}
        `);
    }
}

// NUEVA FUNCIÓN: Calcula el total del carrito en el frontend
function calcularTotalCarrito() {
    let total = 0;
    carrito.forEach(itemName => {
        const product = productosData[itemName];
        if (product && product.price) {
            total += product.price;
        }
    });
    return total;
}


// NUEVA FUNCIÓN: Renderiza el carrito DENTRO del modal
const renderCart = () => {
    const list = document.getElementById('cart-items-list');
    const modalContent = list.closest('div'); // Contenedor que tiene h2, table-info, ul y botones
    
    list.innerHTML = '';
    
    // 1. Contamos las ocurrencias
    const counts = {};
    carrito.forEach(item => {
        counts[item] = (counts[item] || 0) + 1;
    });

    // 2. Dibujamos los items con el botón de eliminar
    Object.entries(counts).forEach(([name, count]) => {
        const li = document.createElement('li');
        li.style.display = 'flex';
        li.style.justifyContent = 'space-between';
        li.style.alignItems = 'center';
        li.style.marginBottom = '8px';

        // Contenido (Nombre y Cantidad)
        const contentSpan = document.createElement('span');
        contentSpan.textContent = `${count}x ${name}`;
        
        const removeButton = document.createElement('button');
        removeButton.className = 'remove-item-button';
        removeButton.textContent = '×'; // Usamos el símbolo de multiplicación para que sea visible
        removeButton.title = `Quitar 1 ${name}`;
        removeButton.dataset.name = name;
        
        // Adjuntamos el listener inmediatamente al crear el elemento
        removeButton.addEventListener('click', (e) => {
            eliminarProductoDelCarrito(e.currentTarget.dataset.name);
        });

        li.appendChild(contentSpan);
        li.appendChild(removeButton);
        list.appendChild(li);
    });

    // Si el carrito está vacío
    if (carrito.length === 0) {
        list.innerHTML = '<li>El carrito está vacío.</li>';
    }

    // 3. MOSTRAMOS EL TOTAL
    const total = calcularTotalCarrito();
    
    // Eliminamos el total anterior si existe
    let totalDisplay = document.getElementById('cart-total-display');
    if (!totalDisplay) {
        totalDisplay = document.createElement('p');
        totalDisplay.id = 'cart-total-display';
        totalDisplay.style.fontWeight = 'bold';
        totalDisplay.style.fontSize = '1.2em';
        totalDisplay.style.textAlign = 'right';
        totalDisplay.style.marginTop = '15px';
        totalDisplay.style.borderTop = '1px dashed var(--color-separador)';
        totalDisplay.style.paddingTop = '10px';
        
        // Insertamos el total ANTES del footer/botones (que no está en el modal, pero asumimos que está antes del cierre)
        const modalFooter = modalContent.querySelector('div:last-of-type'); 
        modalContent.insertBefore(totalDisplay, modalFooter);

    }
    totalDisplay.textContent = `TOTAL: $${total.toFixed(0)}`;
};


// MODIFICADO: Usa la nueva función renderCart
function setupCarrito() {
    const viewCartBtn = document.querySelector('.view-cart-button');
    const modal = document.getElementById('cart-modal');
    const closeBtn = document.getElementById('close-cart');
    const orderBtn = document.getElementById('place-order-btn');
    const tableInfo = document.getElementById('table-info');


    // Abrir Modal
    viewCartBtn.addEventListener('click', () => {
        renderCart(); // Renderiza la lista al abrir y calcula el total
        modal.style.display = 'flex';
        
        if (qrIdMesa) {
            tableInfo.textContent = "✅ Mesa detectada (QR Escaneado)";
            orderBtn.disabled = false;
            orderBtn.style.background = 'var(--color-secundario)'; 
            orderBtn.textContent = "¡Pedir!";
        } else {
            tableInfo.textContent = "⚠️ Escanea un QR para pedir";
            orderBtn.disabled = true;
            orderBtn.style.background = '#ccc';
            orderBtn.textContent = "Solo visualización";
        }
    });

    // Cerrar Modal
    closeBtn.addEventListener('click', () => modal.style.display = 'none');

    // ENVIAR PEDIDO (Lógica sin cambios)
    orderBtn.addEventListener('click', async () => {
        if (carrito.length === 0) return alert("El carrito está vacío");

        const pedido = {
            items: carrito,
            table_number: 0, 
            qr_id: qrIdMesa 
        };

        try {
            const res = await fetch('http://127.0.0.1:8001/pedidos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pedido)
            });

            if (res.ok) {
                const data = await res.json();
                alert(`¡Pedido enviado con éxito!\nTu número de pedido es: #${data.id}`);
                carrito = []; 
                actualizarBotonCarrito();
                modal.style.display = 'none';
            } else {
                alert("Error al enviar pedido. Intenta nuevamente.");
            }
        } catch (e) {
            console.error(e);
            alert("Error de conexión");
        }
    });
}

// NUEVA FUNCIÓN: Elimina UNA instancia de un producto del carrito
function eliminarProductoDelCarrito(productName) {
    const index = carrito.indexOf(productName);
    if (index > -1) {
        carrito.splice(index, 1); // Elimina solo esa instancia
    }
    
    // 1. Si el modal está abierto, lo re-renderizamos para actualizar la vista y el total
    const modal = document.getElementById('cart-modal');
    if (modal.style.display === 'flex') {
        renderCart(); 
    }
    
    // 2. Actualiza el contador del botón principal
    actualizarBotonCarrito();
}


function actualizarBotonCarrito() {
    const btn = document.querySelector('.view-cart-button');
    btn.textContent = `Ver carrito (${carrito.length})`;
}