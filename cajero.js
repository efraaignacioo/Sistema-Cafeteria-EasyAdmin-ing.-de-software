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

// --- (NUEVO) Variable global para el carrito ---
let carritoActual = [];

// --- Lógica de la Página ---
document.addEventListener('DOMContentLoaded', () => {
    
    // 1. VERIFICAR SI EL USUARIO ES CAJERO O ADMIN
    const token = getToken();
    
    if (!token) {
        alert('Debes iniciar sesión para acceder.');
        window.location.href = 'login.html';
        return;
    }
    
    const userData = parseJwt(token);
    
    // ¡Permitimos que 'cajero' Y 'admin' entren!
    if (!userData || !['cajero', 'admin'].includes(userData.role)) {
        alert('No tienes permisos de cajero o administrador.');
        window.location.href = 'login.html'; 
        return;
    }
    
    console.log(`Acceso de ${userData.role} concedido.`);

    
    // 2. LÓGICA DEL BOTÓN "CERRAR SESIÓN"
    const logoutButton = document.getElementById('logout-button');
    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('accessToken');
        alert('Sesión cerrada.');
        window.location.href = 'login.html';
    });
    
    // --- (NUEVO) Lógica para el Carrito ---
    const addToCartButton = document.getElementById('add-to-cart-button');
    const selectProductos = document.getElementById('menu-products');

    // Al hacer clic en "Añadir al Carrito"
    addToCartButton.addEventListener('click', () => {
        const productoSeleccionado = selectProductos.value;
        if (productoSeleccionado) {
            // 1. Añadimos el nombre al array
            carritoActual.push(productoSeleccionado);
            // 2. Actualizamos la lista visual
            actualizarCarritoVisual();
        }
    });

    // --- (NUEVO) Lógica para Crear el Pedido ---
    const createOrderForm = document.getElementById('create-order-form');
    const createOrderMessage = document.getElementById('create-order-message');

    createOrderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        createOrderMessage.textContent = '';
        createOrderMessage.className = '';

        const tableNumberInput = document.getElementById('table-number');
        
        // Verificamos que el carrito no esté vacío
        if (carritoActual.length === 0) {
            createOrderMessage.textContent = 'Error: El carrito está vacío.';
            createOrderMessage.className = 'error';
            return;
        }

        // Verificamos que el número de mesa no esté vacío
        if (!tableNumberInput.value) {
            createOrderMessage.textContent = 'Error: Debes ingresar un número de mesa.';
            createOrderMessage.className = 'error';
            return;
        }

        // 1. Preparamos el pedido para enviar
        const nuevoPedido = {
            items: carritoActual, // Nuestro array de productos
            table_number: parseInt(tableNumberInput.value)
        };

        const token = getToken();

        try {
            // 2. Enviamos el pedido al order-service (puerto 8001)
            const response = await fetch('http://127.0.0.1:8001/pedidos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(nuevoPedido)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error al crear el pedido.');
            }

            // 3. ¡Éxito!
            createOrderMessage.textContent = '¡Pedido creado con éxito!';
            createOrderMessage.className = 'success';
            
            // 4. Limpiamos el formulario y el carrito
            createOrderForm.reset(); // Esto limpia el input de la mesa
            carritoActual = [];
            actualizarCarritoVisual(); // Esto limpia el carrito visual
            
            // 5. ¡Recargamos la lista de pedidos!
            cargarTodosLosPedidos();

        } catch (error) {
            console.error('Error al crear pedido:', error);
            createOrderMessage.textContent = error.message;
            createOrderMessage.className = 'error';
        }
    });

    // --- (MODIFICADO) Llamadas de Carga Inicial ---
    
    // 3. Cargar todos los pedidos al iniciar
    cargarTodosLosPedidos();

    // 4. Cargar los productos en el formulario
    cargarProductosParaFormulario();

});
// --- FIN DEL DOMContentLoaded ---


// --- Función para Cargar el Historial de Pedidos ---
// (Esta función ya la tenías, la mantenemos igual)
async function cargarTodosLosPedidos() {
    const token = getToken();
    const orderListDiv = document.getElementById('order-list');
    
    try {
        const response = await fetch('http://127.0.0.1:8001/pedidos', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('No se pudieron cargar los pedidos.');
        }

        const pedidos = await response.json();
        orderListDiv.innerHTML = ''; 

        if (pedidos.length === 0) {
            orderListDiv.innerHTML = '<p>No hay pedidos en el historial.</p>';
            return;
        }
        
        pedidos.reverse().forEach(pedido => {
            const pedidoCard = document.createElement('div');
            pedidoCard.className = 'order-card-cajero';
            
            if (pedido.status === 'Pagado') {
                pedidoCard.classList.add('pagado');
            }
            
            const itemsString = pedido.items.join(', ');
            // Corrección: Asegurarse de que created_at existe antes de formatear
            const fecha = pedido.created_at ? new Date(pedido.created_at).toLocaleString('es-CL') : 'Fecha no disponible';

            pedidoCard.innerHTML = `
                <h3>Pedido #${pedido.id} <span class="status ${String(pedido.status).replace(' ', '-')}">${pedido.status}</span></h3>
                <p><strong>Mesa:</strong> ${pedido.table_number}</p>
                <p><strong>Items:</strong> ${itemsString}</p>
                <p><strong>Total:</strong> $${pedido.total ? pedido.total.toFixed(0) : 'N/A'}</p>
                <p><strong>Fecha:</strong> ${fecha}</p>
            `;
            
            orderListDiv.appendChild(pedidoCard);
        });

    } catch (error) {
        console.error('Error al cargar pedidos:', error);
        orderListDiv.innerHTML = '<p>Error al cargar el historial.</p>';
    }
}

// --- (NUEVO) Función para Cargar Productos en el Formulario ---
async function cargarProductosParaFormulario() {
    const token = getToken();
    const selectProductos = document.getElementById('menu-products');
    
    try {
        // ¡Hablamos con el product-service (puerto 8000)!
        const response = await fetch('http://127.0.0.1:8000/menu', {
            method: 'GET',
            // OJO: El /menu es público, pero si estuviera protegido,
            // necesitaríamos enviar el token así:
            // headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error('No se pudieron cargar los productos.');
        }

        const productos = await response.json();
        
        selectProductos.innerHTML = '<option value="">Selecciona un producto...</option>';
        
        productos.forEach(producto => {
            const option = document.createElement('option');
            option.value = producto.name;
            // Mostramos nombre y precio en la opción
            option.textContent = `${producto.name} - $${producto.price ? producto.price.toFixed(0) : 'N/A'}`;
            selectProductos.appendChild(option);
        });

    } catch (error) {
        console.error('Error al cargar productos:', error);
        selectProductos.innerHTML = '<option value="">Error al cargar productos</option>';
    }
}

// --- (NUEVO) Función para "dibujar" el carrito ---
function actualizarCarritoVisual() {
    const cartList = document.getElementById('cart-list');
    cartList.innerHTML = ''; // Limpiamos la lista
    carritoActual.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        cartList.appendChild(li);
    });
}