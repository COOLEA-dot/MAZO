document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', function (event) {
        const shareBtn = event.target.closest('.share-button');
        if (shareBtn) {
            const videoId = shareBtn.dataset.videoId;
            const modal = document.getElementById(`share-modal-${videoId}`);
            if (modal) {
                modal.classList.remove('hidden');
            }
        }

        const closeBtn = event.target.closest('.close-share-modal');
        if (closeBtn) {
            const videoId = closeBtn.dataset.videoId;
            const modal = document.getElementById(`share-modal-${videoId}`);
            if (modal) {
                modal.classList.add('hidden');
            }
        }

        const isShareModal = event.target.classList.contains('share-modal');
        if (isShareModal) {
            event.target.classList.add('hidden');
        }
    });
});

// 👉 Función para compartir por chat escribiendo el nombre del usuario
function shareInChat(videoId, form) {
    const input = form.querySelector('input[name="recipient"]');
    const username = input.value.trim();
    if (username !== "") {
        const videoUrl = window.location.origin + `/video/${videoId}`;

        const socket = io();
        socket.emit("share_video", {
            recipient_username: username,
            video_url: videoUrl
        });

        showFlashMessage(`✅ Video compartido con ${username}`);

        input.value = "";

        const modal = document.getElementById(`share-modal-${videoId}`);
        if (modal) {
            modal.classList.add('hidden');
        }
    }
}

// 👉 Función para compartir directamente con usuarios con los que ya hay chats abiertos
function shareInChatDirect(username, videoId) {
    const videoUrl = window.location.origin + `/video/${videoId}`;

    const socket = io();
    socket.emit("share_video", {
        recipient_username: username,
        video_url: videoUrl
    });

    showFlashMessage(`✅ Video compartido con ${username}`);

    const modal = document.getElementById(`share-modal-${videoId}`);
    if (modal) {
        modal.classList.add('hidden');
    }
}

// ✅ Función para mostrar notificaciones tipo flash en la esquina
function showFlashMessage(message) {
    const flash = document.createElement("div");
    flash.className = "flash-message";
    flash.textContent = message;
    document.body.appendChild(flash);

    setTimeout(() => {
        flash.classList.add("show");
        setTimeout(() => {
            flash.classList.remove("show");
            setTimeout(() => {
                flash.remove();
            }, 500);
        }, 3000);
    }, 100);
}
