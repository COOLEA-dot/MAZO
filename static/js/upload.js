document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("video_file");
    const form = document.getElementById("uploadForm");

    if (!input || !form) return;

    const MAX_SIZE_IOS = 50 * 1024 * 1024;   // 50MB (Apple-safe)
    const MAX_SIZE_OTHER = 200 * 1024 * 1024; // 200MB
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

    input.addEventListener("change", () => {
        const file = input.files[0];
        if (!file) return;

        // Validar tipo
        if (!file.type.startsWith("video/")) {
            alert("El archivo seleccionado no es un vídeo válido");
            input.value = "";
            return;
        }

        // Validar tamaño
        const maxSize = isIOS ? MAX_SIZE_IOS : MAX_SIZE_OTHER;
        if (file.size > maxSize) {
            alert(
                isIOS
                    ? "En iPhone/iPad el vídeo no puede superar los 50MB"
                    : "El vídeo no puede superar los 200MB"
            );
            input.value = "";
            return;
        }
    });

    // Seguridad extra: bloquear submit si no hay archivo válido
    form.addEventListener("submit", (e) => {
        const file = input.files[0];
        if (!file) {
            alert("Selecciona un vídeo antes de subir");
            e.preventDefault();
        }
    });
});
