document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', function (event) {

        // 🔗 Abrir modal de compartir
        const shareBtn = event.target.closest('.share-button');
        if (shareBtn) {
            const videoId = shareBtn.dataset.videoId;
            const modal = document.getElementById(`share-modal-${videoId}`);
            if (modal) modal.classList.remove('hidden');
        }

        // ❌ Cerrar modal de compartir
        const closeBtn = event.target.closest('.close-share-modal');
        if (closeBtn) {
            const videoId = closeBtn.dataset.videoId;
            const modal = document.getElementById(`share-modal-${videoId}`);
            if (modal) modal.classList.add('hidden');
        }

        // 🖤 Cerrar modal share al tocar fuera
        if (event.target.classList.contains('share-modal')) {
            event.target.classList.add('hidden');
        }

        // 🔒 Cerrar modal block al tocar fuera
        const blockModal = document.getElementById("blockModal");
        if (event.target === blockModal) {
            closeBlockModal();
        }

        // 🚩 Cerrar modal report al tocar fuera
        const reportModal = document.getElementById("reportModal");
        if (event.target === reportModal) {
            closeReportModal();
        }
    });
});


// 👉 Compartir escribiendo username
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
        if (modal) modal.classList.add('hidden');
    }
}


// 👉 Compartir directo
function shareInChatDirect(username, videoId) {
    const videoUrl = window.location.origin + `/video/${videoId}`;

    const socket = io();
    socket.emit("share_video", {
        recipient_username: username,
        video_url: videoUrl
    });

    showFlashMessage(`✅ Video compartido con ${username}`);

    const modal = document.getElementById(`share-modal-${videoId}`);
    if (modal) modal.classList.add('hidden');
}


// ===============================
// 🚩 REPORT SYSTEM
// ===============================

let videoToReport = null;
let userToReport = null;

// Abrir modal desde video
function reportVideo(videoId) {
    videoToReport = videoId;
    userToReport = null;

    const modal = document.getElementById("reportModal");
    if (modal) modal.classList.remove("hidden");
}

// Abrir modal desde perfil
function reportUser(userId) {
    userToReport = userId;
    videoToReport = null;

    const modal = document.getElementById("reportModal");
    if (modal) modal.classList.remove("hidden");
}

// Cerrar modal
function closeReportModal() {
    const modal = document.getElementById("reportModal");
    if (modal) modal.classList.add("hidden");

    const input = document.getElementById("reportReason");
    if (input) input.value = "";

    videoToReport = null;
    userToReport = null;
}

// Enviar reporte
function submitReport() {
    const reasonInput = document.getElementById("reportReason");
    const reason = reasonInput ? reasonInput.value.trim() : "";

    if (!reason) {
        alert("Escribe un motivo");
        return;
    }

    const form = document.getElementById("reportForm");
    if (!form) {
        console.error("❌ reportForm no encontrado");
        return;
    }

    const formData = new FormData(form);
    formData.append("reason", reason);

    let url = "";

    // 🔥 CASO VIDEO
    if (videoToReport) {
        const videoInput = document.getElementById("reportVideoId");
        if (videoInput) videoInput.value = videoToReport;

        url = `/report_video/${videoToReport}`;
    }

    // 🔥 CASO USUARIO
    else if (userToReport) {
        url = `/report_user/${userToReport}`;
    }

    fetch(url, {
        method: "POST",
        body: formData
    })
    .then(async res => {
        if (!res.ok) {
            const text = await res.text();
            console.error("❌ ERROR REPORT:", text);
            throw new Error("Error en servidor");
        }
        return res.json();
    })
    .then(() => {
        closeReportModal();
        showFlashMessage("🚩 Reporte enviado correctamente");
    })
    .catch(err => {
        console.error(err);
        showFlashMessage("❌ Error al enviar reporte");
    });
}


// ===============================
// 🚫 BLOCK SYSTEM
// ===============================

let userToBlock = null;

// Abrir modal
function blockUser(userId) {
    userToBlock = userId;

    const modal = document.getElementById("blockModal");
    if (!modal) {
        console.error("❌ blockModal no encontrado");
        return;
    }

    modal.classList.remove("hidden");
}

// Cerrar modal
function closeBlockModal() {
    const modal = document.getElementById("blockModal");
    if (modal) modal.classList.add("hidden");

    userToBlock = null;
}

// Confirmar bloqueo
function confirmBlock() {
    if (!userToBlock) return;

    console.log("🔒 Bloqueando usuario:", userToBlock);

    const form = document.getElementById("blockForm");
    if (!form) {
        console.error("❌ blockForm no encontrado");
        return;
    }

    const formData = new FormData(form);

    fetch(`/block_user/${userToBlock}`, {
        method: "POST",
        body: formData
    })
    .then(async res => {
        if (!res.ok) {
            const text = await res.text();
            console.error("❌ ERROR BACKEND:", text);
            throw new Error("Error en servidor");
        }
        return res.json();
    })
    .then(() => {
        closeBlockModal();

        showFlashMessage("🚫 Usuario bloqueado");

        // 🔥 DETECTAR SI ESTÁS EN PERFIL
        const isProfilePage = window.location.pathname.includes("/profile");

        if (isProfilePage) {
            // 💥 REDIRIGIR AL HOME (CLAVE PARA APPLE)
            window.location.href = "/";
            return;
        }

        // 🔥 HOME (eliminar video actual correctamente)
        const activeVideoItem = document.querySelector(".video-item");

        if (activeVideoItem) {
            activeVideoItem.remove(); // 💥 elimina el video actual
        }

        // 🔥 SCROLL al siguiente video (efecto TikTok)
        window.scrollBy({
            top: window.innerHeight,
            behavior: "smooth"
        });

        // 🔥 FALLBACK por seguridad (Apple-friendly)
        setTimeout(() => {
            location.reload();
        }, 800);
    })
    .catch(err => {
        console.error(err);
        showFlashMessage("❌ Error al bloquear usuario");
    });
}


// ===============================
// 🧠 GLOBAL MODAL CONTROL
// ===============================

document.addEventListener("click", function (e) {

    const reportModal = document.getElementById("reportModal");
    if (e.target === reportModal) {
        closeReportModal();
    }

    const blockModal = document.getElementById("blockModal");
    if (e.target === blockModal) {
        closeBlockModal();
    }
});


// ===============================
// ✅ FLASH MESSAGE
// ===============================

function showFlashMessage(message) {
    const flash = document.createElement("div");
    flash.className = "flash-message";
    flash.textContent = message;
    document.body.appendChild(flash);

    setTimeout(() => {
        flash.classList.add("show");
        setTimeout(() => {
            flash.classList.remove("show");
            setTimeout(() => flash.remove(), 500);
        }, 3000);
    }, 100);
}