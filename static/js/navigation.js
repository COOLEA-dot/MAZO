document.addEventListener("DOMContentLoaded", function () {
    const videos = document.querySelectorAll(".video-item");
    let currentIndex = 0;

    function showVideo(index) {
        videos.forEach((video, i) => {
            video.style.display = i === index ? "block" : "none";
            const videoElement = video.querySelector("video");
            if (videoElement) {
                if (i === index) {
                    videoElement.play();
                } else {
                    videoElement.pause();
                }
            }
        });
    }

    // Botones (solo en escritorio)
    const nextBtn = document.getElementById("next-video");
    const prevBtn = document.getElementById("prev-video");

    if (nextBtn && prevBtn) {
        nextBtn.addEventListener("click", function () {
            if (currentIndex < videos.length - 1) {
                currentIndex++;
                showVideo(currentIndex);
            }
        });

        prevBtn.addEventListener("click", function () {
            if (currentIndex > 0) {
                currentIndex--;
                showVideo(currentIndex);
            }
        });
    }

    // Inicializar
    showVideo(currentIndex);

    // 👇 Swipe para móviles
    let touchStartY = 0;

    document.addEventListener("touchstart", (e) => {
        touchStartY = e.changedTouches[0].clientY;
    });

    document.addEventListener("touchend", (e) => {
        const touchEndY = e.changedTouches[0].clientY;
        const deltaY = touchStartY - touchEndY;

        if (Math.abs(deltaY) > 50) {
            if (deltaY > 0 && currentIndex < videos.length - 1) {
                currentIndex++;
            } else if (deltaY < 0 && currentIndex > 0) {
                currentIndex--;
            }
            showVideo(currentIndex);
        }
    });
});
