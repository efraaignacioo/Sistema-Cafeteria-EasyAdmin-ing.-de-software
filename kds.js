document.addEventListener('DOMContentLoaded', () => {
    cargarPedidosIniciales();
    conectarWebSocket();
    inicializarDragAndDrop();
});

// 1. Carga los pedidos que ya existen al abrir la página
async function cargarPedidosIniciales() {
    try {
        // ### CORREGIDO: Apuntar al puerto 8001 ###
        const response = await fetch('http://localhost:8001/pedidos'); 
        if (!response.ok) {
             throw new Error(`HTTP error! status: ${response.status}`);
        }
        const pedidos = await response.json();
        // Limpiar columnas antes de añadir
        document.getElementById('columna-pendiente').innerHTML = '';
        document.getElementById('columna-preparacion').innerHTML = '';
        document.getElementById('columna-listo').innerHTML = '';
        pedidos.forEach(pedido => crearTarjetaPedido(pedido));
    } catch (error) {
        console.error("Error al cargar pedidos iniciales:", error);
        // Opcional: Mostrar un mensaje de error al usuario en la página
    }
}

// 2. Se conecta por WebSocket para recibir actualizaciones en tiempo real
function conectarWebSocket() {
    // ### CORREGIDO: Apuntar al puerto 8001 ###
    const ws = new WebSocket('ws://localhost:8001/ws/kds');

    ws.onopen = function(event) {
        console.log("WebSocket KDS conectado exitosamente a ws://localhost:8001/ws/kds");
        // Puedes añadir aquí lógica para indicar visualmente la conexión (ej: icono verde)
    };

    ws.onmessage = function(event) {
        try {
            const message = JSON.parse(event.data);
            console.log("Mensaje WS recibido:", message);

            // Verificamos que el mensaje tenga la estructura esperada
            if (message && message.data && message.data.id) {
                 if (message.type === 'new_order' || message.action === 'new_order') { // Compatibilidad con ambos formatos de mensaje
                    console.log("Nuevo pedido recibido:", message.data);
                    // Asegurarse de que message.data.items sea una lista
                    if (typeof message.data.items === 'string') {
                        message.data.items = message.data.items.split(',').map(item => item.trim());
                    }
                     crearTarjetaPedido(message.data);
                     // Opcional: Podrías añadir un sonido de notificación aquí
                 } else if (message.type === 'status_update' || message.action === 'status_update') {
                    console.log("Actualización de estado recibida:", message.data);
                     // Asegurarse de que message.data.items sea una lista
                    if (typeof message.data.items === 'string') {
                         message.data.items = message.data.items.split(',').map(item => item.trim());
                    }
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
        // Puedes añadir aquí lógica para indicar visualmente la desconexión (ej: icono rojo)
        setTimeout(conectarWebSocket, 3000); // Intenta reconectar cada 3 segundos
    };

    ws.onerror = function(error) {
        console.error("Error de WebSocket KDS:", error);
    };
}

// 3. Crea el HTML para una tarjeta de pedido y la añade a la columna correcta
function crearTarjetaPedido(pedido) {
    const columnaId = `columna-${pedido.status.replace(/ /g, '-')}`; // Ej: 'columna-en-preparacion'
    const columna = document.getElementById(columnaId);

    if (!columna) {
        console.warn(`No se encontró la columna para el estado: ${pedido.status}`);
        return; // Salir si la columna no existe
    }

    // Crear el elemento de la tarjeta
    const card = document.createElement('div');
    card.id = `pedido-${pedido.id}`;
    card.className = 'order-card';
    card.draggable = true; // Hacerla arrastrable

    // Formatear la fecha/hora
    const fecha = new Date(pedido.created_at).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit'});

    // Generar HTML interno de la tarjeta
    let itemsHtml = '<ul>';
    // Asegurarse de que 'items' es un array antes de iterar
    if (Array.isArray(pedido.items)) {
         pedido.items.forEach(item => itemsHtml += `<li>${item}</li>`);
    } else if (typeof pedido.items === 'string') { // Si llega como string, intentar dividir
        pedido.items.split(',').forEach(item => itemsHtml += `<li>${item.trim()}</li>`);
    }
    itemsHtml += '</ul>';


    card.innerHTML = `
        <div class="card-header">
            <strong>Pedido #${pedido.id}</strong>
            <span>${fecha}</span>
        </div>
        ${itemsHtml}
    `;

    // Añadir la tarjeta a la columna correcta
    columna.appendChild(card);
}

// Función para actualizar o mover una tarjeta existente
function actualizarTarjetaPedido(pedido) {
     const tarjetaExistente = document.getElementById(`pedido-${pedido.id}`);
     if (tarjetaExistente) {
         tarjetaExistente.remove(); // Eliminar la tarjeta vieja
     }
     crearTarjetaPedido(pedido); // Crear la tarjeta en la nueva columna/estado
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
                // 'evt.item' es la tarjeta que se movió (el elemento HTML)
                const nuevoEstado = evt.to.dataset.status; // Obtiene el estado de la columna destino
                const pedidoId = evt.item.id.split('-')[1]; // Extrae el ID del 'id' del elemento

                console.log(`Pedido ${pedidoId} movido a estado: ${nuevoEstado}`);
                actualizarEstadoPedido(pedidoId, nuevoEstado);
            }
        });
    });
}

// 5. Envía la actualización de estado al backend cuando se mueve una tarjeta
async function actualizarEstadoPedido(pedidoId, nuevoEstado) {
    console.log(`Enviando actualización para Pedido ${pedidoId} a estado ${nuevoEstado}`);
    try {
        // ### CORREGIDO: Apuntar al puerto 8001 ###
        const response = await fetch(`http://localhost:8001/pedidos/${pedidoId}/estado`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: nuevoEstado })
        });
        if (!response.ok) {
            // Si falla la actualización, podríamos querer devolver la tarjeta a su columna original
            console.error(`Error al actualizar estado: ${response.status}`);
            // Aquí podríamos añadir lógica para revertir el movimiento visual si falla el backend
            // Por ahora, solo logueamos el error.
            const errorData = await response.json();
            console.error("Detalle del error:", errorData);
            // alert(`Error al actualizar el pedido ${pedidoId}. Por favor, inténtelo de nuevo.`); // Evitar alerts
        } else {
             console.log(`Pedido ${pedidoId} actualizado correctamente en el backend.`);
             // La actualización visual la manejará el mensaje WebSocket que el backend enviará de vuelta.
        }
    } catch (error) {
        console.error("Error de red al actualizar estado:", error);
         // alert(`Error de red al actualizar el pedido ${pedidoId}. Verifique la conexión.`); // Evitar alerts
    }
}