document.addEventListener('DOMContentLoaded', () => {
    cargarPedidosIniciales();
    conectarWebSocket();
    inicializarDragAndDrop();
});

// 1. Carga los pedidos que ya existen al abrir la página
async function cargarPedidosIniciales() {
    try {
        const response = await fetch('http://localhost:8001/pedidos'); 
        if (!response.ok) {
             throw new Error(`HTTP error! status: ${response.status}`);
        }
        const pedidos = await response.json();
        // Limpiar columnas antes de añadir
        document.getElementById('columna-pendiente').innerHTML = '';
        document.getElementById('columna-en-preparacion').innerHTML = '';
        document.getElementById('columna-listo').innerHTML = '';
        pedidos.forEach(pedido => crearTarjetaPedido(pedido));
    } catch (error) {
        console.error("Error al cargar pedidos iniciales:", error);
    }
}

// 2. Se conecta por WebSocket para recibir actualizaciones en tiempo real
function conectarWebSocket() {
    const ws = new WebSocket('ws://localhost:8001/ws/kds');

    ws.onopen = function(event) {
        console.log("WebSocket KDS conectado exitosamente a ws://localhost:8001/ws/kds");
    };

    ws.onmessage = function(event) {
        try {
            const message = JSON.parse(event.data);
            console.log("Mensaje WS recibido:", message);

            if (message && message.data && message.data.id) {
                 if (message.type === 'new_order' || message.action === 'new_order') {
                    console.log("Nuevo pedido recibido:", message.data);
                    crearTarjetaPedido(message.data);
                 } else if (message.type === 'status_update' || message.action === 'status_update') {
                    console.log("Actualización de estado recibida:", message.data);
                    actualizarTarjetaPedido(message.data);
                 }
            } else {
                 console.warn("Mensaje WS recibido con formato inesperado:", message);
            }
        } catch (e) {
            console.error("Error al procesar mensaje WS:", e, "Mensaje original:", event.data);
        }
    };

    ws.onclose = function(event) {
        console.log('WebSocket KDS desconectado. Intentando reconectar en 3 segundos...');
        setTimeout(conectarWebSocket, 3000);
    };

    ws.onerror = function(error) {
        console.error("Error de WebSocket KDS:", error);
    };
}

// 3. Crea el HTML para una tarjeta de pedido y la añade a la columna correcta
function crearTarjetaPedido(pedido) {
    // Corregido para manejar "en preparacion" sin acento
    const statusClass = pedido.status.replace(/ /g, '-').normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const columnaId = `columna-${statusClass}`;
    const columna = document.getElementById(columnaId);

    if (!columna) {
        console.warn(`No se encontró la columna para el estado: ${pedido.status} (ID buscado: ${columnaId})`);
        return;
    }

    const card = document.createElement('div');
    card.id = `pedido-${pedido.id}`;
    card.className = 'order-card';
    card.draggable = true;

    const fecha = new Date(pedido.created_at).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit'});

    let itemsHtml = '<ul>';
    if (Array.isArray(pedido.items)) {
         pedido.items.forEach(item => itemsHtml += `<li>${item}</li>`);
    } else if (typeof pedido.items === 'string') {
        pedido.items.split(',').forEach(item => itemsHtml += `<li>${item.trim()}</li>`);
    }
    itemsHtml += '</ul>';

    // ### MODIFICADO: Añadido el span para "Mesa #" ###
    card.innerHTML = `
        <div class="card-header">
            <strong>Pedido #${pedido.id}</strong>
            <span class="order-table">Mesa #${pedido.table_number}</span> 
            <span>${fecha}</span>
        </div>
        ${itemsHtml}
    `;

    columna.appendChild(card);
}

// Función para actualizar o mover una tarjeta existente
function actualizarTarjetaPedido(pedido) {
     const tarjetaExistente = document.getElementById(`pedido-${pedido.id}`);
     if (tarjetaExistente) {
         tarjetaExistente.remove();
     }
     crearTarjetaPedido(pedido);
}


// 4. Activa la función de arrastrar y soltar en las columnas
function inicializarDragAndDrop() {
    const columnas = document.querySelectorAll('.card-container');
    
    columnas.forEach(columna => {
        new Sortable(columna, {
            group: 'pedidos',
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function (evt) {
                const nuevoEstado = evt.to.dataset.status;
                const pedidoId = evt.item.id.split('-')[1];
                actualizarEstadoPedido(pedidoId, nuevoEstado);
            }
        });
    });
}

// 5. Envía la actualización de estado al backend cuando se mueve una tarjeta
async function actualizarEstadoPedido(pedidoId, nuevoEstado) {
    console.log(`Enviando actualización para Pedido ${pedidoId} a estado ${nuevoEstado}`);
    try {
        const response = await fetch(`http://localhost:8001/pedidos/${pedidoId}/estado`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: nuevoEstado })
        });
        if (!response.ok) {
            console.error(`Error al actualizar estado: ${response.status}`);
            const errorData = await response.json();
            console.error("Detalle del error:", errorData);
        } else {
             console.log(`Pedido ${pedidoId} actualizado correctamente en el backend.`);
        }
    } catch (error) {
        console.error("Error de red al actualizar estado:", error);
    }
}
