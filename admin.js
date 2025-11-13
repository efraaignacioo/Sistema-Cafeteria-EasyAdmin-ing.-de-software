// --- Funciones de Seguridad Esenciales ---

function getToken() {
    return localStorage.getItem('accessToken');
}

function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) { return null; }
}

// --- Variables globales para los Modales ---
let currentEditingId = null;
let currentPayingOrderId = null; 

// --- Lógica de la Página ---
document.addEventListener('DOMContentLoaded', () => {
    
    // 1. VERIFICAR SI EL USUARIO ES ADMIN
    const token = getToken();
    if (!token) {
        alert('Debes iniciar sesión para acceder.');
        window.location.href = 'login.html';
        return;
    }
    const userData = parseJwt(token);
    if (!userData || userData.role !== 'admin') {
        alert('No tienes permisos de administrador.');
        window.location.href = 'login.html'; 
        return;
    }
    console.log('Acceso de Administrador concedido.');

    
    // 2. LÓGICA DEL BOTÓN "CERRAR SESIÓN"
    const logoutButton = document.getElementById('logout-button');
    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('accessToken');
        alert('Sesión cerrada.');
        window.location.href = 'login.html';
    });
    

    // 3. LÓGICA PARA REGISTRAR NUEVOS USUARIOS
    const registerForm = document.getElementById('register-form');
    const registerMessage = document.getElementById('register-message');
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault(); 
        registerMessage.textContent = '';
        registerMessage.className = '';
        const username = document.getElementById('new-username').value;
        const password = document.getElementById('new-password').value;
        const role = document.getElementById('new-role').value;
        const adminToken = getToken();
        const newUser = { username, password, role };
        try {
            const response = await fetch('http://127.0.0.1:8002/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${adminToken}` },
                body: JSON.stringify(newUser)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al registrar el usuario.');
            }
            const createdUser = await response.json();
            registerMessage.textContent = `¡Usuario '${createdUser.username}' (Rol: ${createdUser.role}) creado con éxito!`;
            registerMessage.className = 'success';
            registerForm.reset(); 
        } catch (error) {
            console.error('Error al registrar:', error);
            registerMessage.textContent = error.message;
            registerMessage.className = 'error';
        }
    });

    // 4. LÓGICA PARA GESTIÓN DE MENÚ
    cargarProductosAdmin();
    
    // 5. LÓGICA PARA EL POP-UP (MODAL) DE "CREAR/EDITAR PRODUCTO"
    const modalOverlay = document.getElementById('modal-overlay');
    const modalTitle = document.getElementById('modal-title');
    const createProductForm = document.getElementById('create-product-form');
    const createProductMessage = document.getElementById('create-product-message');
    const showCreateFormButton = document.getElementById('show-create-form-button');
    const closeModalButton = document.getElementById('close-modal-button');

    function showProductModal() { modalOverlay.classList.remove('hidden'); }
    function hideProductModal() {
        modalOverlay.classList.add('hidden');
        createProductMessage.textContent = ''; 
        createProductForm.reset(); 
        currentEditingId = null; 
    }

    showCreateFormButton.addEventListener('click', () => {
        currentEditingId = null; 
        modalTitle.textContent = 'Crear Nuevo Producto'; 
        createProductForm.reset(); 
        showProductModal(); 
    });
    
    closeModalButton.addEventListener('click', hideProductModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            hideProductModal();
        }
    });
    
    createProductForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        createProductMessage.textContent = '';
        const token = getToken();
        const productData = {
            name: document.getElementById('product-name').value,
            description: document.getElementById('product-description').value,
            price: parseFloat(document.getElementById('product-price').value)
        };
        try {
            let response;
            let successMessage;
            if (currentEditingId) {
                response = await fetch(`http://127.0.0.1:8000/menu/${currentEditingId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(productData)
                });
                successMessage = `¡Producto "${productData.name}" actualizado con éxito!`;
            } else {
                response = await fetch('http://127.0.0.1:8000/menu', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(productData)
                });
                successMessage = `¡Producto "${productData.name}" creado con éxito!`;
            }
            if (!response.ok) {
                const errorData = await response.json();
                let errorMessage = errorData.detail || 'Error al guardar.';
                if (Array.isArray(errorData.detail) && errorData.detail[0].msg) {
                    errorMessage = errorData.detail[0].msg;
                }
                throw new Error(errorMessage);
            }
            hideProductModal();
            alert(successMessage);
            cargarProductosAdmin(); 
        } catch (error) {
            console.error('Error al guardar producto:', error);
            createProductMessage.textContent = error.message;
        }
    });

    // 6. LÓGICA PARA GESTIÓN DE PEDIDOS
    cargarTodosLosPedidosAdmin();

    // 7. LÓGICA PARA EL POP-UP (MODAL) DE "PAGAR"
    const paymentModalOverlay = document.getElementById('payment-modal-overlay');
    const paymentModalTitle = document.getElementById('payment-modal-title');
    const paymentForm = document.getElementById('payment-form');
    const paymentMessage = document.getElementById('payment-message');
    const closePaymentModalButton = document.getElementById('close-payment-modal-button');

    function hidePaymentModal() {
        paymentModalOverlay.classList.add('hidden');
        currentPayingOrderId = null; 
    }

    closePaymentModalButton.addEventListener('click', hidePaymentModal);
    paymentModalOverlay.addEventListener('click', (e) => {
        if (e.target === paymentModalOverlay) {
            hidePaymentModal();
        }
    });

    paymentForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        paymentMessage.textContent = '';
        const method = document.getElementById('payment-method').value;
        const token = getToken();
        try {
            const response = await fetch(`http://127.0.0.1:8001/pedidos/${currentPayingOrderId}/pagar`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ method: method }) 
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al procesar el pago.');
            }
            hidePaymentModal();
            alert(`¡Pedido #${currentPayingOrderId} pagado con ${method}!`);
            cargarTodosLosPedidosAdmin(); 

        } catch (error) {
            console.error('Error al pagar:', error);
            paymentMessage.textContent = error.message;
        }
    });

    // 8. LÓGICA PARA EL BOTÓN DE REPORTE DIARIO
    const getReportButton = document.getElementById('get-daily-report-button');
    const reportResultsDiv = document.getElementById('report-results');

    getReportButton.addEventListener('click', async () => {
        const token = getToken();
        reportResultsDiv.innerHTML = '<p>Cargando reporte...</p>';
        reportResultsDiv.style.display = 'block'; 

        try {
            const response = await fetch('http://127.0.0.1:8001/reporte/diario', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al obtener el reporte.');
            }

            const reporte = await response.json();

            // Formatear la fecha (que viene como "YYYY-MM-DD") a algo más legible
            const fechaParts = reporte.fecha.split('-');
            const fechaFormateada = new Date(fechaParts[0], fechaParts[1] - 1, fechaParts[2]).toLocaleDateString('es-CL');

            // --- ¡AQUÍ ESTÁ EL CAMBIO! ---
            // Borramos la línea <small>...</small>
            reportResultsDiv.innerHTML = `
                <p><strong>Fecha del Reporte:</strong> ${fechaFormateada}</p>
                <p class="report-total">Ventas Totales: $${reporte.total_ventas.toFixed(0)}</p>
            `;
            // --- FIN DEL CAMBIO ---

        } catch (error) {
            console.error('Error al obtener reporte:', error);
            reportResultsDiv.innerHTML = `<p style="color:red;">${error.message}</p>`;
        }
    });

});
// --- FIN DEL DOMContentLoaded ---


// --- Función de Cargar Productos (sin cambios) ---
const productListContainer = document.getElementById('product-list-container');
async function cargarProductosAdmin() {
    const token = getToken(); 
    try {
        const response = await fetch('http://127.0.0.1:8000/menu', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) { throw new Error('No se pudieron cargar los productos.'); }
        
        const productos = await response.json();
        productListContainer.innerHTML = ''; 
        
        if (productos.length === 0) {
            productListContainer.innerHTML = '<p>No hay productos en el menú.</p>';
            return;
        }
        
        productos.forEach(producto => {
            const productoDiv = document.createElement('div');
            productoDiv.className = 'product-item';
            productoDiv.innerHTML = `
                <div class="product-item-info">
                    <strong>${producto.name}</strong>
                    <span>($${producto.price ? producto.price.toFixed(0) : 'N/A'})</span>
                </div>
                <div class="product-item-actions">
                    <button class="edit-product-button">Editar</button>
                    <button class="delete-product-button" data-id="${producto.id}">Eliminar</button>
                </div>
            `;
            productoDiv.querySelector('.edit-product-button').addEventListener('click', () => {
                prepararEdicion(producto);
            });
            productoDiv.querySelector('.delete-product-button').addEventListener('click', () => {
                eliminarProducto(producto.id, producto.name);
            });
            productListContainer.appendChild(productoDiv);
        });
    } catch (error) {
        console.error('Error al cargar productos:', error);
        productListContainer.innerHTML = '<p>Error al cargar productos.</p>';
    }
}

// --- Función para preparar el modal de edición (sin cambios) ---
function prepararEdicion(producto) {
    currentEditingId = producto.id;
    document.getElementById('modal-title').textContent = 'Editar Producto';
    document.getElementById('product-name').value = producto.name;
    document.getElementById('product-description').value = producto.description;
    document.getElementById('product-price').value = producto.price;
    document.getElementById('modal-overlay').classList.remove('hidden');
}

// --- Función de Eliminar Productos (sin cambios) ---
async function eliminarProducto(productoId, productoNombre) {
    if (!confirm(`¿Estás seguro de que quieres eliminar "${productoNombre}"? Esta acción no se puede deshacer.`)) {
        return; 
    }
    const token = getToken(); 
    try {
        const response = await fetch(`http://127.0.0.1:8000/menu/${productoId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al eliminar el producto.');
        }
        alert(`¡Producto "${productoNombre}" eliminado con éxito!`);
        cargarProductosAdmin(); 
    } catch (error) {
        console.error('Error al eliminar:', error);
        alert(error.message); 
    }
}

// --- Funciones de Gestión de Pedidos (sin cambios) ---
async function cargarTodosLosPedidosAdmin() {
    const token = getToken();
    const orderListDiv = document.getElementById('admin-order-list');
    
    try {
        const response = await fetch('http://127.0.0.1:8001/pedidos', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) { throw new Error('No se pudieron cargar los pedidos.'); }

        const pedidos = await response.json();
        orderListDiv.innerHTML = ''; 
        if (pedidos.length === 0) {
            orderListDiv.innerHTML = '<p>No hay pedidos en el historial.</p>';
            return;
        }
        
        pedidos.reverse().forEach(pedido => {
            const pedidoCard = document.createElement('div');
            pedidoCard.className = 'order-card-admin';
            
            const isPagado = pedido.status === 'Pagado';
            if (isPagado) {
                pedidoCard.classList.add('pagado');
            }
            
            const itemsString = (pedido.items && pedido.items.length > 0) ? pedido.items.join(', ') : 'N/A';
            const fecha = pedido.created_at ? new Date(pedido.created_at).toLocaleString('es-CL') : 'N/A';
            const total = pedido.total ? pedido.total.toFixed(0) : 'N/A';
            const status = pedido.status || 'N/A';
            const table = pedido.table_number || 'N/A';
            
            const hideButtonHtml = isPagado 
                ? `<button class="hide-order-button" title="Ocultar de la lista">&times;</button>`
                : '';
            
            pedidoCard.innerHTML = `
                ${hideButtonHtml}
                <h3>Pedido #${pedido.id} <span class="status ${status.replace(' ', '-')}">${status}</span></h3>
                <p><strong>Mesa:</strong> ${table}</p>
                <p><strong>Items:</strong> ${itemsString}</p>
                <p><strong>Total:</strong> $${total}</p>
                <p><strong>Fecha:</strong> ${fecha}</p>
                <div class="order-actions">
                    <button class="pay-button" data-id="${pedido.id}" ${isPagado ? 'disabled' : ''}>
                        ${isPagado ? 'Pagado' : 'Procesar Pago'}
                    </button>
                    <button class="receipt-button" data-id="${pedido.id}" ${!isPagado ? 'disabled' : ''}>
                        Generar Boleta
                    </button>
                </div>
            `;
            
            if (!isPagado) {
                pedidoCard.querySelector('.pay-button').addEventListener('click', (e) => {
                    const orderId = e.target.dataset.id;
                    const paymentModalTitle = document.getElementById('payment-modal-title');
                    const paymentModalOverlay = document.getElementById('payment-modal-overlay');
                    currentPayingOrderId = orderId; 
                    paymentModalTitle.textContent = `Procesar Pago Pedido #${orderId}`;
                    document.getElementById('payment-message').textContent = '';
                    document.getElementById('payment-form').reset();
                    paymentModalOverlay.classList.remove('hidden');
                });
            }

            if (isPagado) {
                pedidoCard.querySelector('.receipt-button').addEventListener('click', (e) => {
                    const orderId = e.target.dataset.id;
                    generarBoleta(orderId); 
                });
                
                pedidoCard.querySelector('.hide-order-button').addEventListener('click', () => {
                    pedidoCard.style.display = 'none';
                });
            }
            
            orderListDiv.appendChild(pedidoCard);
        });

    } catch (error) {
        console.error('Error al cargar pedidos:', error);
        orderListDiv.innerHTML = '<p>Error al cargar el historial.</p>';
    }
}

async function generarBoleta(orderId) {
    const token = getToken();
    try {
        const response = await fetch(`http://127.0.0.1:8001/pedidos/${orderId}/ticket`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al generar la boleta.');
        }
        
        const boleta = await response.json();
        
        const items = boleta.items.join('\n - ');
        alert(
            `--- BOLETA Pedido #${boleta.order_id} ---\n` +
            `Fecha: ${new Date(boleta.issued_at).toLocaleString('es-CL')}\n` +
            `Mesa: ${boleta.table_number}\n\n` +
            `--- Items ---\n - ${items}\n\n` +
            `Método de Pago: ${boleta.payment_method}\n` +
            `TOTAL: $${boleta.total.toFixed(0)}`
        );

    } catch (error) {
        console.error('Error al generar boleta:', error);
        alert(error.message);
    }
}