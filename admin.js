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
    
    // 4. GESTIÓN DE CATEGORÍAS
    const createCategoryForm = document.getElementById('create-category-form');
    const categoryMessage = document.getElementById('category-message');

    // Cargar categorías al inicio
    cargarCategorias();

    createCategoryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        categoryMessage.textContent = '';
        categoryMessage.className = '';
        const name = document.getElementById('new-category-name').value;
        const token = getToken();

        try {
            const response = await fetch('http://127.0.0.1:8000/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ name })
            });
            
            if(!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Error al crear la categoría');
            }
            createCategoryForm.reset();
            categoryMessage.textContent = `Categoría "${name}" creada con éxito.`;
            categoryMessage.className = 'success';
            cargarCategorias(); 
            cargarSelectCategorias(); 
        } catch (error) {
            console.error(error);
            categoryMessage.textContent = error.message;
            categoryMessage.className = 'error';
        }
    });

    // 5. GESTIÓN DE MENÚ (Carga inicial)
    cargarProductosAdmin();
    // Cargar el select del modal de productos
    cargarSelectCategorias(); 
    
    // 6. MODALES DE PRODUCTOS
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
        cargarSelectCategorias(); 
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
        
        const priceVal = parseFloat(document.getElementById('product-price').value);
        const categoryId = document.getElementById('product-category').value; 
        
        const productData = {
            name: document.getElementById('product-name').value,
            description: document.getElementById('product-description').value,
            price: isNaN(priceVal) ? 0 : priceVal,
            category_id: parseInt(categoryId)
        };
        try {
            let response;
            let successMessage;
            
            let url = 'http://127.0.0.1:8000/menu';
            let method = 'POST';

            if (currentEditingId) {
                url = `http://127.0.0.1:8000/menu/${currentEditingId}`;
                method = 'PUT';
            }

            response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(productData)
            });
            
            if (currentEditingId) {
                successMessage = `¡Producto "${productData.name}" actualizado con éxito!`;
            } else {
                successMessage = `¡Producto "${productData.name}" creado con éxito!`;
            }
            
            if (!response.ok) {
                const errorData = await response.json();
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

    // 7. GESTIÓN DE PEDIDOS (Carga inicial)
    cargarTodosLosPedidosAdmin();

    // 8. MODAL DE PAGO
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

    // 9. REPORTES
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

    // 10. GESTIÓN DE MESAS Y QRs
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

    // --- 11. GESTIÓN DE PERSONALIZACIÓN (AJUSTES DE MENÚ) ---
    const settingsForm = document.getElementById('settings-form');
    const settingsMessage = document.getElementById('settings-message');

    // Cargar configuración actual al inicio
    cargarSettings();

    settingsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        settingsMessage.textContent = '';
        settingsMessage.className = '';
        
        // Capturamos los campos de Contenido Fijo
        const menuTitle = document.getElementById('menu-title').value;
        const headerImageUrl = document.getElementById('header-image-url').value;
        
        // Capturamos los campos de Colores
        // ELIMINADO: const principal = document.getElementById('color-principal').value;
        const secundario = document.getElementById('color-secundario').value;
        const modo = document.querySelector('input[name="modo-visual"]:checked').value;
        
        const token = getToken();
        const newSettings = {
            // ELIMINADO: color_principal: principal,
            color_secundario: secundario,
            modo_visual: modo,
            
            // CAMPOS CORRECTOS
            menu_title: menuTitle, 
            header_image_url: headerImageUrl
        };

        try {
            const response = await fetch('http://127.0.0.1:8000/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(newSettings)
            });
            
            if(!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Error al guardar configuración');
            }
            
            settingsMessage.textContent = '¡Configuración de contenido y colores guardada con éxito!';
            settingsMessage.className = 'success';
        } catch (error) {
            console.error(error);
            settingsMessage.textContent = error.message;
            settingsMessage.className = 'error';
        }
    });


}); // --- FIN DEL DOMContentLoaded ---


// --- FUNCIONES AUXILIARES ---

// FUNCIÓN AUXILIAR: Cargar configuración para el formulario
async function cargarSettings() {
    const token = getToken(); 
    
    try {
        const response = await fetch('http://127.0.0.1:8000/settings', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) throw new Error('Error al cargar la configuración inicial.');

        const settings = await response.json();
        
        // CARGAR NUEVOS CAMPOS DE CONTENIDO
        document.getElementById('menu-title').value = settings.menu_title || 'Menú Principal';
        document.getElementById('header-image-url').value = settings.header_image_url || '';

        // Cargar los selectores de color
        // ELIMINADO: document.getElementById('color-principal').value = settings.color_principal;
        document.getElementById('color-secundario').value = settings.color_secundario;
        
        // Cargar el modo visual (radio button)
        const radio = document.getElementById(`mode-${settings.modo_visual}`);
        if(radio) radio.checked = true;

    } catch (error) {
        console.error('Error al cargar settings:', error);
    }
}

// FUNCIÓN: Cargar Categorías en el listado
async function cargarCategorias() {
    const container = document.getElementById('category-list-container');
    const token = getToken();
    container.innerHTML = '<p>Cargando...</p>';

    try {
        const response = await fetch('http://127.0.0.1:8000/categories', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Error al cargar categorías.');
        
        const categorias = await response.json();
        container.innerHTML = ''; 
        
        if (categorias.length === 0) {
            container.innerHTML = '<p>No hay categorías registradas.</p>';
            return;
        }
        
        categorias.forEach(cat => {
            const catDiv = document.createElement('div');
            catDiv.className = 'product-item'; 
            catDiv.innerHTML = `
                <div class="product-item-info">
                    <strong>${cat.name}</strong>
                    <small>(ID: ${cat.id})</small>
                </div>
                <button class="delete-category-button delete-product-button" data-id="${cat.id}" data-name="${cat.name}">Eliminar</button>
            `;
            catDiv.querySelector('.delete-category-button').addEventListener('click', () => {
                eliminarCategoria(cat.id, cat.name);
            });
            container.appendChild(catDiv);
        });
    } catch (error) {
        console.error('Error al cargar categorías:', error);
        container.innerHTML = `<p class="error">${error.message}</p>`;
    }
}

// FUNCIÓN: Cargar Categorías en el select del modal de productos
async function cargarSelectCategorias() {
    const select = document.getElementById('product-category');
    const token = getToken();
    select.innerHTML = '<option value="">Cargando categorías...</option>';

    try {
        const response = await fetch('http://127.0.0.1:8000/categories', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error('Error al cargar categorías.');
        
        const categorias = await response.json();
        select.innerHTML = '<option value="">Selecciona una categoría...</option>'; 
        
        categorias.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.name;
            select.appendChild(option);
        });

    } catch (error) {
        console.error('Error al cargar select categorías:', error);
        select.innerHTML = '<option value="">Error al cargar</option>';
    }
}

// FUNCIÓN: Eliminar Categoría
async function eliminarCategoria(categoryId, categoryName) {
    if (!confirm(`¿Eliminar la categoría "${categoryName}"? Los productos asociados serán desvinculados.`)) return;
    const token = getToken(); 
    const categoryMessage = document.getElementById('category-message');
    categoryMessage.textContent = '';
    categoryMessage.className = '';

    try {
        const response = await fetch(`http://127.0.0.1:8000/categories/${categoryId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) {
             const errorData = await response.json();
             throw new Error(errorData.detail || 'Error al eliminar la categoría.');
        }
        
        categoryMessage.textContent = `¡Categoría "${categoryName}" eliminada!`;
        categoryMessage.className = 'success';
        cargarCategorias(); 
        cargarSelectCategorias(); 
        cargarProductosAdmin(); 
    } catch (error) {
        categoryMessage.textContent = error.message;
        categoryMessage.className = 'error';
    }
}

// FUNCIÓN: cargarProductosAdmin
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
            // Muestra la categoría
            const categoryName = producto.category_name || 'Sin Categoría';
            productoDiv.innerHTML = `
                <div class="product-item-info">
                    <strong>${producto.name}</strong> 
                    <small>[${categoryName}]</small> 
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

// FUNCIÓN: prepararEdicion
function prepararEdicion(producto) {
    currentEditingId = producto.id;
    document.getElementById('modal-title').textContent = 'Editar Producto';
    document.getElementById('product-name').value = producto.name;
    document.getElementById('product-description').value = producto.description;
    document.getElementById('product-price').value = producto.price;
    // Establece la categoría actual en el select
    document.getElementById('product-category').value = producto.category_id; 
    document.getElementById('modal-overlay').classList.remove('hidden');
}

// FUNCIÓN: eliminarProducto
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

// FUNCIÓN: cargarTodosLosPedidosAdmin
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

// FUNCIÓN: generarBoleta
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

// FUNCIÓN: cargarMesas
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

// FUNCIÓN: mostrarQR
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