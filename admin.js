// admin.js

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

// --- Variables globales ---
let currentEditingId = null;
let currentPayingOrderId = null; 

// --- Lógica Principal (Al cargar la página) ---
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

    // 3. GESTIÓN DE USUARIOS (REGISTRO)
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

    // 4. GESTIÓN DE MENÚ (Carga inicial)
    cargarProductosAdmin();
    
    // 5. MODALES DE PRODUCTOS
    const modalOverlay = document.getElementById('modal-overlay');
    const modalTitle = document.getElementById('modal-title');
    const createProductForm = document.getElementById('create-product-form');
    const createProductMessage = document.getElementById('create-product-message');
    const showCreateFormButton = document.getElementById('show-create-form-button');
    const closeModalButton = document.getElementById('close-modal-button');

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
        modalOverlay.classList.remove('hidden');
    });
    
    closeModalButton.addEventListener('click', hideProductModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) hideProductModal();
    });
    
    createProductForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        createProductMessage.textContent = '';
        const token = getToken();
        // Convertimos el precio a float, si falla pone 0 (el backend validará si es <= 0)
        const priceVal = parseFloat(document.getElementById('product-price').value);
        
        const productData = {
            name: document.getElementById('product-name').value,
            description: document.getElementById('product-description').value,
            price: isNaN(priceVal) ? 0 : priceVal
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
                // Manejo de errores detallado de Pydantic
                let errorMessage = errorData.detail || 'Error al guardar.';
                if (Array.isArray(errorData.detail)) {
                    errorMessage = errorData.detail.map(e => e.msg).join(' | ');
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

    // 6. GESTIÓN DE PEDIDOS (Carga inicial)
    cargarTodosLosPedidosAdmin();

    // 7. MODAL DE PAGO
    const paymentModalOverlay = document.getElementById('payment-modal-overlay');
    const closePaymentModalButton = document.getElementById('close-payment-modal-button');
    const paymentForm = document.getElementById('payment-form');
    const paymentMessage = document.getElementById('payment-message');

    function hidePaymentModal() {
        paymentModalOverlay.classList.add('hidden');
        currentPayingOrderId = null; 
    }

    closePaymentModalButton.addEventListener('click', hidePaymentModal);
    paymentModalOverlay.addEventListener('click', (e) => {
        if (e.target === paymentModalOverlay) hidePaymentModal();
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

    // 8. REPORTES
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
            const fechaParts = reporte.fecha.split('-');
            const fechaFormateada = new Date(fechaParts[0], fechaParts[1] - 1, fechaParts[2]).toLocaleDateString('es-CL');

            reportResultsDiv.innerHTML = `
                <p><strong>Fecha del Reporte:</strong> ${fechaFormateada}</p>
                <p class="report-total">Ventas Totales: $${reporte.total_ventas.toFixed(0)}</p>
            `;
        } catch (error) {
            console.error('Error al obtener reporte:', error);
            reportResultsDiv.innerHTML = `<p style="color:red;">${error.message}</p>`;
        }
    });

    // --- 9. GESTIÓN DE MESAS Y QRs (NUEVO) ---
    // Esta parte estaba mal pegada antes. Ahora está correctamente integrada.
    
    const createTableForm = document.getElementById('create-table-form');
    
    // Cargar mesas al inicio
    cargarMesas();

    createTableForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('new-table-name').value;
        const section = document.getElementById('new-table-section').value;
        const token = getToken();

        try {
            const response = await fetch('http://127.0.0.1:8001/tables', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ name, section })
            });
            
            if(!response.ok) {
                const err = await response.json();
                alert(err.detail || 'Error al crear mesa');
                return;
            }
            createTableForm.reset();
            cargarMesas(); // Recargar la lista
            alert("¡Mesa creada!");
        } catch (error) {
            console.error(error);
            alert("Error de conexión al crear mesa");
        }
    });

    // Modal de QR
    const qrModal = document.getElementById('qr-modal-overlay');
    document.getElementById('close-qr-modal').addEventListener('click', () => qrModal.classList.add('hidden'));

}); // --- FIN DEL DOMContentLoaded ---


// --- FUNCIONES AUXILIARES (Fuera del DOMContentLoaded) ---

async function cargarProductosAdmin() {
    const productListContainer = document.getElementById('product-list-container');
    const token = getToken(); 
    try {
        const response = await fetch('http://127.0.0.1:8000/menu', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Error de conexión');
        
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

function prepararEdicion(producto) {
    currentEditingId = producto.id;
    document.getElementById('modal-title').textContent = 'Editar Producto';
    document.getElementById('product-name').value = producto.name;
    document.getElementById('product-description').value = producto.description;
    document.getElementById('product-price').value = producto.price;
    document.getElementById('modal-overlay').classList.remove('hidden');
}

async function eliminarProducto(productoId, productoNombre) {
    if (!confirm(`¿Eliminar "${productoNombre}"?`)) return;
    const token = getToken(); 
    try {
        const response = await fetch(`http://127.0.0.1:8000/menu/${productoId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error();
        alert(`¡Producto eliminado!`);
        cargarProductosAdmin(); 
    } catch (error) {
        alert('Error al eliminar producto.'); 
    }
}

// --- Gestión de Pedidos ---
async function cargarTodosLosPedidosAdmin() {
    const token = getToken();
    const orderListDiv = document.getElementById('admin-order-list');
    
    try {
        const response = await fetch('http://127.0.0.1:8001/pedidos', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error();

        const pedidos = await response.json();
        orderListDiv.innerHTML = ''; 
        if (pedidos.length === 0) {
            orderListDiv.innerHTML = '<p>No hay pedidos.</p>';
            return;
        }
        
        pedidos.reverse().forEach(pedido => {
            const pedidoCard = document.createElement('div');
            pedidoCard.className = 'order-card-admin';
            
            const isPagado = pedido.status === 'Pagado';
            if (isPagado) pedidoCard.classList.add('pagado');
            
            const itemsString = (pedido.items && pedido.items.length > 0) ? pedido.items.join(', ') : 'N/A';
            const total = pedido.total ? pedido.total.toFixed(0) : 'N/A';
            const status = pedido.status || 'N/A';
            const table = pedido.table_number || 'N/A';
            
            const hideButtonHtml = isPagado 
                ? `<button class="hide-order-button" title="Ocultar">&times;</button>`
                : '';
            
            pedidoCard.innerHTML = `
                ${hideButtonHtml}
                <h3>Pedido #${pedido.id} <span class="status ${status.replace(' ', '-')}">${status}</span></h3>
                <p><strong>Mesa:</strong> ${table}</p>
                <p><strong>Items:</strong> ${itemsString}</p>
                <p><strong>Total:</strong> $${total}</p>
                <div class="order-actions">
                    <button class="pay-button" data-id="${pedido.id}" ${isPagado ? 'disabled' : ''}>
                        ${isPagado ? 'Pagado' : 'Pagar'}
                    </button>
                    <button class="receipt-button" data-id="${pedido.id}" ${!isPagado ? 'disabled' : ''}>
                        Boleta
                    </button>
                </div>
            `;
            
            if (!isPagado) {
                pedidoCard.querySelector('.pay-button').addEventListener('click', (e) => {
                    const orderId = e.target.dataset.id;
                    currentPayingOrderId = orderId; 
                    document.getElementById('payment-modal-title').textContent = `Pago Pedido #${orderId}`;
                    document.getElementById('payment-message').textContent = '';
                    document.getElementById('payment-form').reset();
                    document.getElementById('payment-modal-overlay').classList.remove('hidden');
                });
            }

            if (isPagado) {
                pedidoCard.querySelector('.receipt-button').addEventListener('click', (e) => generarBoleta(e.target.dataset.id));
                pedidoCard.querySelector('.hide-order-button').addEventListener('click', () => pedidoCard.style.display = 'none');
            }
            orderListDiv.appendChild(pedidoCard);
        });

    } catch (error) {
        console.error(error);
        orderListDiv.innerHTML = '<p>Error al cargar historial.</p>';
    }
}

async function generarBoleta(orderId) {
    const token = getToken();
    try {
        const response = await fetch(`http://127.0.0.1:8001/pedidos/${orderId}/ticket`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Error al generar boleta');
        
        const boleta = await response.json();
        const items = boleta.items.join('\n - ');
        alert(
            `--- BOLETA #${boleta.order_id} ---\n` +
            `Fecha: ${new Date(boleta.issued_at).toLocaleString('es-CL')}\n` +
            `Mesa: ${boleta.table_number}\n` +
            `Items:\n - ${items}\n` +
            `TOTAL: $${boleta.total.toFixed(0)}\n` +
            `Pago: ${boleta.payment_method}`
        );
    } catch (error) {
        alert(error.message);
    }
}

// --- Gestión de Mesas (Funciones Auxiliares) ---
async function cargarMesas() {
    const tablesListContainer = document.getElementById('tables-list-container');
    const token = getToken();
    try {
        const response = await fetch('http://127.0.0.1:8001/tables', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const mesas = await response.json();
        
        tablesListContainer.innerHTML = '';
        mesas.forEach(mesa => {
            const div = document.createElement('div');
            div.className = 'product-item'; 
            div.innerHTML = `
                <div class="product-item-info">
                    <strong>${mesa.name}</strong> - <small>${mesa.section}</small>
                </div>
                <button class="edit-product-button show-qr-btn" data-id="${mesa.id}" data-name="${mesa.name}" data-qrid="${mesa.qr_id}">
                    Ver QR
                </button>
            `;
            tablesListContainer.appendChild(div);
        });

        document.querySelectorAll('.show-qr-btn').forEach(btn => {
            btn.addEventListener('click', (e) => mostrarQR(e.target.dataset.id, e.target.dataset.name, e.target.dataset.qrid));
        });

    } catch (error) {
        console.error("Error al cargar mesas:", error);
    }
}

async function mostrarQR(id, name, qrId) {
    const token = getToken();
    const qrModal = document.getElementById('qr-modal-overlay');
    const qrContainer = document.getElementById('qr-image-container');
    const qrLinkText = document.getElementById('qr-link-text');
    const openQrLinkBtn = document.getElementById('open-qr-link');

    const response = await fetch(`http://127.0.0.1:8001/tables/${id}/qr`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    if(response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        
        qrContainer.innerHTML = `<img src="${imageUrl}" alt="QR ${name}" style="max-width: 200px;">`;
        
        const link = `http://127.0.0.1:5500/index.html?mesa=${qrId}`;
        qrLinkText.textContent = link;
        openQrLinkBtn.href = link;
        
        qrModal.classList.remove('hidden');
    }
}