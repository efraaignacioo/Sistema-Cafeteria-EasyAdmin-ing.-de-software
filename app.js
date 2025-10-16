// Esta línea espera a que toda la página HTML se cargue antes de ejecutar el código.
document.addEventListener('DOMContentLoaded', () => {
    cargarMenu();
});

// --- Función para cargar los productos desde tu API de Python ---
function cargarMenu() {
    // Esta es la URL de tu API. Si ejecutas Python en tu misma PC, esta URL debería funcionar.
    const url = 'http://127.0.0.1:8000/menu';

    // "fetch" es como "ir a buscar". Va a la URL que le dimos a buscar los datos.
    fetch(url)
        .then(response => {
            // Cuando el servidor responde, primero revisamos si todo salió bien.
            if (!response.ok) {
                throw new Error('La respuesta del servidor no fue buena');
            }
            // Convertimos la respuesta (que es texto) a un formato que JavaScript entiende (JSON).
            return response.json();
        })
        .then(productos => {
            // ¡Aquí ya tenemos la lista de productos!
            // Ahora llamamos a otra función para que los dibuje en la pantalla.
            mostrarMenu(productos);
        })
        .catch(error => {
            // Si algo sale mal (ej: el servidor de Python no está encendido), mostramos un error.
            console.error('Hubo un problema al cargar el menú:', error);
            const menuContainer = document.getElementById('menu-container');
            menuContainer.innerHTML = '<p>Error al cargar el menú. Intenta más tarde.</p>';
        });
}

// --- Función para dibujar los productos en la pantalla ---
function mostrarMenu(productos) {
    const menuContainer = document.getElementById('menu-container');

    // Por ahora, para simplificar, asumimos que todos son de la categoría "Cafetería".
    // Más adelante podemos agruparlos por "Cafés", "Pastelería", etc.
    
    const categoriaDiv = document.createElement('div');
    categoriaDiv.className = 'category';

    const titulo = document.createElement('h2');
    titulo.textContent = 'Nuestro Menú';
    categoriaDiv.appendChild(titulo);

    // Recorremos la lista de productos que nos dio el servidor.
    productos.forEach(producto => {
        // Por cada producto, creamos los elementos HTML.
        const itemDiv = document.createElement('div');
        itemDiv.className = 'menu-item';

        const nombreSpan = document.createElement('span');
        nombreSpan.textContent = producto.name; // Usamos el nombre del producto

        const boton = document.createElement('button');
        boton.className = 'add-button';
        boton.textContent = '+';

        // Armamos la "tarjeta" del producto
        itemDiv.appendChild(nombreSpan);
        itemDiv.appendChild(boton);

        // Agregamos la tarjeta completa a la categoría
        categoriaDiv.appendChild(itemDiv);
    });

    // Finalmente, agregamos toda la categoría a la pantalla.
    menuContainer.appendChild(categoriaDiv);
}