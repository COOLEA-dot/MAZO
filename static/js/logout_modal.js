document.addEventListener('DOMContentLoaded', function () {
    const logoutLink = document.getElementById('logout-link');
    const logoutModal = document.getElementById('logout-modal');
    const confirmLogout = document.getElementById('confirm-logout');
    const cancelLogout = document.getElementById('cancel-logout');

    // Obtener la URL del logout desde el atributo data
    const logoutUrl = logoutLink.getAttribute('data-logout-url');

    // Mostrar modal al hacer clic en "Cerrar sesión"
    logoutLink.addEventListener('click', function (e) {
        e.preventDefault();
        logoutModal.style.display = 'flex';
    });

    // Confirmar cierre de sesión
    confirmLogout.addEventListener('click', function () {
        window.location.href = logoutUrl;  // Redirige al logout
    });

    // Cancelar cierre de sesión
    cancelLogout.addEventListener('click', function () {
        logoutModal.style.display = 'none';
    });

    // Cerrar modal al hacer clic fuera del contenido
    window.addEventListener('click', function (e) {
        if (e.target === logoutModal) {
            logoutModal.style.display = 'none';
        }
    });
});


