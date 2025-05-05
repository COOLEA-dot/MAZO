document.addEventListener("DOMContentLoaded", function () {
    const videoItems = document.querySelectorAll('.video-item');
    const videos = document.querySelectorAll('.video-element');

    if (videos.length === 0 || videoItems.length === 0) {
        console.error('No se encontraron videos en la página');
        return;
    }

    let currentVideoIndex = 0;

    // Verifica si el video está en pantalla
    function isInViewport(video) {
        const rect = video.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight)
        );
    }

    // Pausar y reiniciar todos menos el actual
    function pauseOtherVideos(currentVideo) {
        videos.forEach((video) => {
            if (video !== currentVideo) {
                video.pause();
                video.currentTime = 0;
            }
        });
    }

    // Reproducir el video si está listo
    function playVideo(video) {
        if (video && video.paused && video.src) {
            video.play().catch(error => {
                console.error('Error al intentar reproducir el video:', error);
            });
        }
    }

    // Cambiar al video siguiente o anterior
    function changeVideo(direction) {
        const nextIndex = currentVideoIndex + direction;

        if (nextIndex >= 0 && nextIndex < videoItems.length) {
            // Ocultar video actual
            videoItems[currentVideoIndex].classList.add("hidden");

            // Mostrar el nuevo video
            videoItems[nextIndex].classList.remove("hidden");

            const nextVideo = videos[nextIndex];
            playVideo(nextVideo);
            pauseOtherVideos(nextVideo);

            currentVideoIndex = nextIndex;
        }
    }

    // Navegación con teclado
    document.addEventListener("keydown", function (event) {
        if (event.key === "ArrowDown") {
            changeVideo(1);
        } else if (event.key === "ArrowUp") {
            changeVideo(-1);
        }
    });

    // Botones de navegación
    document.getElementById("next-video").addEventListener("click", function () {
        changeVideo(1);
    });

    document.getElementById("prev-video").addEventListener("click", function () {
        changeVideo(-1);
    });

    // Cambio de video al hacer scroll
    window.addEventListener('scroll', function () {
        videos.forEach((video, index) => {
            if (isInViewport(video)) {
                if (index !== currentVideoIndex) {
                    changeVideo(index - currentVideoIndex);
                }
            }
        });
    });

    // Mostrar el primer video correctamente al cargar
    videoItems[currentVideoIndex].classList.remove("hidden");
    playVideo(videos[currentVideoIndex]);
});
