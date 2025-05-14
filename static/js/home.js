document.addEventListener("DOMContentLoaded", () => {
    const videoItems = document.querySelectorAll(".video-item");
    const videos = document.querySelectorAll(".video-element");
    let currentIndex = 0;
    let startY = 0;

    function updateClasses() {
        videoItems.forEach((item, index) => {
            item.classList.remove("active", "prev", "next");

            if (index === currentIndex) {
                item.classList.add("active");
                playVideo(videos[index]);
            } else if (index === currentIndex - 1) {
                item.classList.add("prev");
            } else if (index === currentIndex + 1) {
                item.classList.add("next");
            }
        });

        pauseOtherVideos(videos[currentIndex]);
    }

    function playVideo(video) {
        if (video && video.paused) {
            video.play().catch(err => console.error("No se pudo reproducir:", err));
        }
    }

    function pauseOtherVideos(current) {
        videos.forEach(v => {
            if (v !== current) {
                v.pause();
                v.currentTime = 0;
            }
        });
    }

    function changeVideo(direction) {
        const newIndex = currentIndex + direction;
        if (newIndex >= 0 && newIndex < videoItems.length) {
            currentIndex = newIndex;
            updateClasses();
        }
    }

    const container = document.querySelector(".video-container");

    container.addEventListener("touchstart", (e) => {
        startY = e.touches[0].clientY;
    });

    container.addEventListener("touchend", (e) => {
        const endY = e.changedTouches[0].clientY;
        const deltaY = endY - startY;

        if (Math.abs(deltaY) > 50) {
            if (deltaY > 0) {
                changeVideo(-1); // abajo
            } else {
                changeVideo(1); // arriba
            }
        }
    });

    // Botones
    document.getElementById("next-video").addEventListener("click", () => changeVideo(1));
    document.getElementById("prev-video").addEventListener("click", () => changeVideo(-1));

    updateClasses();
});
