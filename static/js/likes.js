document.addEventListener("DOMContentLoaded", () => {
    const likeButtons = document.querySelectorAll('.like-button');
    
    likeButtons.forEach(button => {
        const likeCountSpan = button.querySelector('.like-count');

        button.addEventListener('click', () => {
            const videoId = button.getAttribute('data-video-id');
            const isLiked = button.classList.contains('liked');
            
            const method = isLiked ? 'DELETE' : 'POST';  // Si ya está "liked", hacer DELETE
            const url = `/like/${videoId}`;
            
            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log(data); // Para depuración

                if (data.success) {
                    if (data.liked) {
                        button.classList.add('liked');  // Agregar la clase "liked" si se añadió el like
                    } else {
                        button.classList.remove('liked');  // Eliminar la clase "liked" si se quitó el like
                    }

                    // Actualizar el número de likes con el valor nuevo que el backend devuelve
                    likeCountSpan.textContent = data.new_likes;
                } else {
                    alert("Hubo un problema al procesar tu solicitud.");
                }
            })
            .catch(error => {
                console.error('Error en la solicitud:', error);
            });
        });
    });
});
