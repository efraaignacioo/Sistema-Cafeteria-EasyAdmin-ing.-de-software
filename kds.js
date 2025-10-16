document.addEventListener('DOMContentLoaded', () => {
    cargarPedidosIniciales();
    conectarWebSocket();
    inicializarDragAndDrop();
});

// 1. Carga los pedidos que ya existen al abrir la página
async function cargarPedidosIniciales() {
    try {
        const response = await fetch('http://127.0.0.1:8000/pedidos');
        const pedidos = await response.json();
        pedidos.forEach(pedido => crearTarjetaPedido(pedido));
    } catch (error) {
        console.error("Error al cargar pedidos iniciales:", error);
    }
}

// 2. Se conecta por WebSocket para recibir actualizaciones en tiempo real
function conectarWebSocket() {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/kds');

    ws.onmessage = function(event) {
        const message = JSON.parse(event.data);
        
        if (message.type === 'new_order') {
            console.log("Nuevo pedido recibido:", message.data);
            crearTarjetaPedido(message.data);
            // Opcional: Podrías añadir un sonido de notificación aquí
        }
    };

    ws.onclose = function() {
        console.log('WebSocket desconectado. Intentando reconectar...');
        setTimeout(conectarWebSocket, 3000); // Intenta reconectar cada 3 segundos
    };
}

// 3. Crea la tarjeta HTML para un pedido y la pone en la columna correcta
function crearTarjetaPedido(pedido) {
    // Convierte la lista de items en un formato legible
    const itemsHTML = pedido.items.map(item => `<li>- ${item}</li>`).join('');

    const card = document.createElement('div');
    card.className = 'order-card';
    card.id = `pedido-${pedido.id}`; // Asigna un ID único a la tarjeta
    card.innerHTML = `
        <div class="card-header">
            <span class="order-id">Pedido #${pedido.id}</span>
            <span class="table-number">Mesa ${pedido.table_number}</span>
        </div>
        <ul class="item-list">
            ${itemsHTML}
        </ul>
    `;

    // Decide en qué columna poner la tarjeta
    const status = pedido.status.replace(' ', '-'); // "en preparación" -> "en-preparacion"
    const columna = document.getElementById(`columna-${status}`);
    if (columna) {
        columna.appendChild(card);
    }
}

// 4. Activa la función de arrastrar y soltar en las columnas
function inicializarDragAndDrop() {
    const columnas = document.querySelectorAll('.card-container');
    
    columnas.forEach(columna => {
        new Sortable(columna, {
            group: 'pedidos', // Permite arrastrar entre columnas del mismo grupo
            animation: 150,
            ghostClass: 'sortable-ghost', // Clase CSS para el elemento "fantasma"
            onEnd: function (evt) {
                // 'evt.to' es la columna donde se soltó la tarjeta
                // 'evt.item' es la tarjeta que se movió
                const nuevoEstado = evt.to.dataset.status;
                const pedidoId = evt.item.id.split('-')[1]; // Extrae el ID del 'id' del elemento

                actualizarEstadoPedido(pedidoId, nuevoEstado);
            }
        });
    });
}

// 5. Envía la actualización de estado al backend cuando se mueve una tarjeta
async function actualizarEstadoPedido(pedidoId, nuevoEstado) {
    try {
        await fetch(`http://127.0.0.1:8000/pedidos/${pedidoId}/estado`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: nuevoEstado })
        });
        console.log(`Pedido ${pedidoId} actualizado a: ${nuevoEstado}`);
    } catch (error) {
        console.error("Error al actualizar el estado del pedido:", error);
    }
}