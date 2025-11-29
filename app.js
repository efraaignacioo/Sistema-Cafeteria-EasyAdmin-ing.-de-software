// app.js COMPLETAMENTE ACTUALIZADO

let carrito = [];
let qrIdMesa = null; // Aquí guardaremos el código secreto de la mesa

document.addEventListener('DOMContentLoaded', () => {
    // 1. DETECTAR MESA DESDE LA URL
    // El navegador busca algo como: index.html?mesa=a1b2c3d4...
    const params = new URLSearchParams(window.location.search);
    qrIdMesa = params.get('mesa');

    if (qrIdMesa) {
        console.log("¡Cliente sentado en una mesa! QR ID:", qrIdMesa);
        // Opcional: Podrías consultar al backend qué mesa es para mostrar "Estás en la Mesa 1"
        // Pero para el pedido, solo necesitamos enviar el ID.
    } else {
        console.log("Modo visualización (Sin mesa)");
    }

    cargarMenu();
    setupCarrito();
});

function cargarMenu() {
    fetch('http://127.0.0.1:8000/menu')
        .then(r => r.json())
        .then(productos => mostrarMenu(productos))
        .catch(e => console.error(e));
}

function mostrarMenu(productos) {
    const container = document.getElementById('menu-container');
    container.innerHTML = '<div class="category"><h2>Menú</h2></div>'; // Limpiar y poner título
    const catDiv = container.querySelector('.category');

    productos.forEach(prod => {
        const item = document.createElement('div');
        item.className = 'menu-item';
        item.innerHTML = `
            <span>${prod.name} ($${prod.price})</span>
            <button class="add-button" data-name="${prod.name}">+</button>
        `;
        // Lógica de agregar al carrito
        item.querySelector('.add-button').addEventListener('click', () => {
            carrito.push(prod.name);
            alert(`Añadido: ${prod.name}`);
            actualizarBotonCarrito();
        });
        catDiv.appendChild(item);
    });
}

// --- LÓGICA DEL CARRITO ---

function setupCarrito() {
    const viewCartBtn = document.querySelector('.view-cart-button');
    const modal = document.getElementById('cart-modal');
    const closeBtn = document.getElementById('close-cart');
    const orderBtn = document.getElementById('place-order-btn');
    const list = document.getElementById('cart-items-list');
    const tableInfo = document.getElementById('table-info');

    // Abrir Modal
    viewCartBtn.addEventListener('click', () => {
        modal.style.display = 'flex';
        list.innerHTML = carrito.map(item => `<li>${item}</li>`).join('');
        
        if (qrIdMesa) {
            tableInfo.textContent = "✅ Mesa detectada (QR Escaneado)";
            orderBtn.disabled = false;
            orderBtn.style.background = '#8A9A5B';
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

    // ENVIAR PEDIDO
    orderBtn.addEventListener('click', async () => {
        if (carrito.length === 0) return alert("El carrito está vacío");

        const pedido = {
            items: carrito,
            table_number: 0, // No importa, el backend lo deduce del QR
            qr_id: qrIdMesa  // ¡LA CLAVE! Enviamos el código secreto
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
                carrito = []; // Vaciar carrito
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

function actualizarBotonCarrito() {
    const btn = document.querySelector('.view-cart-button');
    btn.textContent = `Ver carrito (${carrito.length})`;
}