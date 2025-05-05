document.addEventListener("DOMContentLoaded", function () {
    const videos = document.querySelectorAll(".video-item");
    let currentIndex = 0;

    function showVideo(index) {
        videos.forEach((video, i) => {
            video.style.display = i === index ? "block" : "none";
        });
    }

    document.getElementById("next-video").addEventListener("click", function () {
        if (currentIndex < videos.length - 1) {
            currentIndex++;
            showVideo(currentIndex);
        }
    });

    document.getElementById("prev-video").addEventListener("click", function () {
        if (currentIndex > 0) {
            currentIndex--;
            showVideo(currentIndex);
        }
    });

    showVideo(currentIndex);
});
