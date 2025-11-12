document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');

    loginForm.addEventListener('submit', (e) => {
        // Evita que el formulario se envíe de la forma tradicional (recargando la página)
        e.preventDefault();
        
        // Limpiamos errores anteriores
        errorMessage.textContent = '';

        // Obtenemos los valores del formulario
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // --- ¡Este es el paso clave! ---
        // Tu backend espera datos de tipo "form-data", no JSON.
        // Usamos URLSearchParams para construir este formato.
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        // Hacemos la llamada 'fetch' al servicio de autenticación
        // ¡Nota que usamos el puerto 8002!
        fetch('http://127.0.0.1:8002/auth/token', {
            method: 'POST',
            headers: {
                // Este header es necesario para que el backend entienda el formato
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData 
        })
        .then(response => {
            // Si la respuesta no es OK (ej: 401 - No autorizado), lanzamos un error
            if (!response.ok) {
                return response.json().then(err => { 
                    // Lanzamos un error con el mensaje del backend (ej: "Incorrect username or password")
                    throw new Error(err.detail || 'Error desconocido'); 
                });
            }
            // Si todo sale bien, convertimos la respuesta a JSON
            return response.json();
        })
        .then(data => {
            // ¡Éxito! Tenemos el token.
            console.log('Login exitoso:', data);
            
            // Guardamos el "carnet de acceso" (token) en el navegador
            localStorage.setItem('accessToken', data.access_token);
            
            // Mostramos un mensaje de éxito y podríamos redirigir al usuario
            errorMessage.textContent = '¡Bienvenido!';
            errorMessage.style.color = '#8A9A5B'; // Verde
            
            // Opcional: Redirigir al usuario al KDS o a otra página después de 1 segundo
            // setTimeout(() => {
            //    window.location.href = '/kds.html'; // Redirige al KDS
            // }, 1000);
        })
        .catch(error => {
            // Capturamos cualquier error (contraseña incorrecta, etc.)
            console.error('Error en el login:', error);
            errorMessage.textContent = error.message;
        });
    });
});