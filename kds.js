// --- INICIO DE LA MODIFICACIÓN ---

// --> NUEVO: Función para obtener el token guardado
function getToken() {
    return localStorage.getItem('accessToken');
}

// --> NUEVO: Verificación de seguridad al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    const token = getToken();
    
    if (!token) {
        // Si no hay token, no estás logueado.
        // Redirigimos al usuario a la página de login.
        alert('Debes iniciar sesión para acceder al KDS.');
        window.location.href = 'login.html'; // Asegúrate que login.html esté en la misma carpeta
    } else {
        // Si hay un token, procedemos a cargar todo.
        cargarPedidosIniciales();
        conectarWebSocket();
        inicializarDragAndDrop();
    }
});

// --- FIN DE LA MODIFICACIÓN ---


// 1. Carga los pedidos que ya existen al abrir la página
async function cargarPedidosIniciales() {
    const token = getToken();

    try {
        // --> ¡CORREGIDO! Apuntamos al puerto 8001
        const response = await fetch('http://127.0.0.1:8001/pedidos', { 
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                alert('Tu sesión ha expirado o no tienes permisos. Por favor, inicia sesión de nuevo.');
                window.location.href = 'login.html';
            }
            throw new Error('Error al cargar pedidos');
        }

        const pedidos = await response.json();
        pedidos.forEach(pedido => crearTarjetaPedido(pedido));
    } catch (error) {
        console.error("Error al cargar pedidos iniciales:", error);
    }
}

// 2. Se conecta por WebSocket para recibir actualizaciones en tiempo real
function conectarWebSocket() {
    const token = getToken();
    
    // --> ¡CORREGIDO! Apuntamos al puerto 8001
    const ws = new WebSocket(`ws://127.0.0.1:8001/ws/kds?token=${token}`);

    ws.onmessage = function(event) {
        const message = JSON.parse(event.data);
        
        if (message.type === 'new_order') {
            console.log("Nuevo pedido recibido:", message.data);
            crearTarjetaPedido(message.data);
            // Opcional: Podríamos añadir un sonido de notificación aquí
        }
    };

    ws.onclose = function() {
        console.log('WebSocket desconectado. Intentando reconectar...');
        setTimeout(conectarWebSocket, 3000); 
    };

    ws.onerror = function(err) {
        console.error('Error de WebSocket:', err);
    };
}

// 3. Crea la tarjeta HTML para un pedido (Sin cambios)
function crearTarjetaPedido(pedido) {
    // Convierte la lista de items en un formato legible
    // Asumiendo que `pedido.items` es una lista de strings
    const itemsHTML = pedido.items.map(item => `<li>- ${item}</li>`).join('');

    const card = document.createElement('div');
    card.className = 'order-card';
    card.id = `pedido-${pedido.id}`;
    card.innerHTML = `
                <div class="card-header">
                    <span class="order-id">Pedido #${pedido.id}</span>
                    <span class="table-number">Mesa #${pedido.table_number}</span>
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

// 4. Activa la función de arrastrar y soltar (Sin cambios en esta parte)
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
    const token = getToken();

    try {
        // --> ¡CORREGIDO! Apuntamos al puerto 8001
        await fetch(`http://127.0.0.1:8001/pedidos/${pedidoId}/estado`, { 
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: nuevoEstado })
        });
        console.log(`Pedido ${pedidoId} actualizado a: ${nuevoEstado}`);
    } catch (error) {
        console.error("Error al actualizar el estado del pedido:", error);
    }
}