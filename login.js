// --- INICIO: Nueva función para "leer" el token ---
// Un token JWT tiene 3 partes separadas por puntos. La parte del medio (payload)
// contiene los datos del usuario (como el rol), codificados en Base64.
// Esta función decodifica esa parte para que podamos leerla.
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1]; // Obtenemos la parte del medio (payload)
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        console.error("Error al leer el token:", e);
        return null;
    }
}
// --- FIN: Nueva función ---


document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        errorMessage.textContent = '';
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        // 1. Hacemos la llamada al servicio de autenticación
        fetch('http://127.0.0.1:8002/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData 
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { 
                    throw new Error(err.detail || 'Error desconocido'); 
                });
            }
            return response.json();
        })
        .then(data => {
            // ¡Éxito! Tenemos el token.
            console.log('Login exitoso:', data);
            
            // 2. Guardamos el token en el navegador
            localStorage.setItem('accessToken', data.access_token);
            
            // --- ¡AQUÍ ESTÁ LA NUEVA LÓGICA DE REDIRECCIÓN! ---
            
            // 3. Leemos el token para saber qué rol tiene el usuario
            const tokenData = parseJwt(data.access_token);
            
            if (!tokenData || !tokenData.role) {
                errorMessage.textContent = 'Error: No se pudo verificar el rol del usuario.';
                return;
            }

            console.log('Rol detectado:', tokenData.role);

            // 4. Redirigimos a la página correcta según el rol
            // (Usamos 500ms de espera para que el usuario vea el mensaje)
            
            if (tokenData.role === 'admin') {
                errorMessage.textContent = '¡Bienvenido Administrador! Redirigiendo...';
                errorMessage.style.color = '#8A9A5B'; // Verde
                setTimeout(() => {
                    window.location.href = 'admin.html'; // ¡A la nueva página de Admin!
                }, 500);

            } else if (tokenData.role === 'cocinero') {
                errorMessage.textContent = '¡Bienvenido Cocinero! Redirigiendo al KDS...';
                errorMessage.style.color = '#8A9A5B';
                setTimeout(() => {
                    window.location.href = 'kds.html'; // ¡Al KDS!
                }, 500);

            } else if (tokenData.role === 'cajero') {
                errorMessage.textContent = '¡Bienvenido Cajero! Redirigiendo...';
                errorMessage.style.color = '#8A9A5B';
                setTimeout(() => {
                    // Crearemos 'cajero.html' en el futuro
                    window.location.href = 'cajero.html'; 
                }, 500);

            } else {
                errorMessage.textContent = `Rol '${tokenData.role}' no reconocido.`;
            }
            // --- FIN DE LA NUEVA LÓGICA ---
        })
        .catch(error => {
            console.error('Error en el login:', error);
            errorMessage.textContent = error.message;
        });
    });
});