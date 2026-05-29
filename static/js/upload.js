document.addEventListener("DOMContentLoaded", () => {

    const input = document.getElementById("video_file");
    const form = document.getElementById("uploadForm");

    if (!input || !form) return;

    // =====================================
    // ELEMENTOS PREVIEW
    // =====================================

    const previewContainer =
        document.getElementById("video-preview-container");

    const videoPreview =
        document.getElementById("videoPreview");

    const titleInput =
        document.getElementById("title");

    const descriptionInput =
        document.getElementById("description");

    const hashtagsInput =
        document.getElementById("hashtags");

    const previewTitle =
        document.getElementById("previewTitle");

    const previewDescription =
        document.getElementById("previewDescription");

    const previewHashtags =
        document.getElementById("previewHashtags");

    const warning =
        document.getElementById("videoWarning");

    // =====================================
    // CONFIG SUBIDA
    // =====================================

    const MAX_SIZE_IOS = 50 * 1024 * 1024;
    const MAX_SIZE_OTHER = 200 * 1024 * 1024;

    const isIOS =
        /iPad|iPhone|iPod/.test(navigator.userAgent);

    // =====================================
    // SELECCIONAR VIDEO
    // =====================================

    input.addEventListener("change", () => {

        const file = input.files[0];

        if (!file) return;

        // =====================
        // VALIDAR TIPO
        // =====================

        if (!file.type.startsWith("video/")) {

            alert(
                "El archivo seleccionado no es un vídeo válido"
            );

            input.value = "";
            return;
        }

        // =====================
        // VALIDAR TAMAÑO
        // =====================

        const maxSize =
            isIOS
                ? MAX_SIZE_IOS
                : MAX_SIZE_OTHER;

        if (file.size > maxSize) {

            alert(
                isIOS
                    ? "En iPhone/iPad el vídeo no puede superar los 50MB"
                    : "El vídeo no puede superar los 200MB"
            );

            input.value = "";
            return;
        }

        // =====================
        // PREVIEW VIDEO
        // =====================

        const videoURL =
            URL.createObjectURL(file);

        videoPreview.src =
            videoURL;

        previewContainer
            .classList
            .remove("hidden");

        // Esperar metadatos
        videoPreview.onloadedmetadata = () => {

            videoPreview.play()
                .catch(() => {});

            // =====================
            // AVISO VIDEO HORIZONTAL
            // =====================

            const isHorizontal =
                videoPreview.videoWidth >
                videoPreview.videoHeight;

            if (isHorizontal) {

                warning
                    .classList
                    .remove("hidden");

            } else {

                warning
                    .classList
                    .add("hidden");
            }
        };
    });

    // =====================================
    // TITULO EN TIEMPO REAL
    // =====================================

    titleInput.addEventListener("input", () => {

        previewTitle.textContent =
            titleInput.value.trim()
            || "Título del video";
    });

    // =====================================
    // DESCRIPCION EN TIEMPO REAL
    // =====================================

    descriptionInput.addEventListener("input", () => {

        previewDescription.textContent =
            descriptionInput.value.trim()
            || "Descripción del video";
    });

    // =====================================
    // HASHTAGS EN TIEMPO REAL
    // =====================================

    hashtagsInput.addEventListener("input", () => {

        const tags =
            hashtagsInput.value
                .split(",")
                .map(tag => tag.trim())
                .filter(tag => tag !== "");

        previewHashtags.innerHTML =
            tags
                .map(tag =>
                    `#${tag.replace("#", "")}`
                )
                .join(" ");
    });

    // =====================================
    // SEGURIDAD SUBMIT
    // =====================================

    form.addEventListener("submit", (e) => {

        const file = input.files[0];

        if (!file) {

            alert(
                "Selecciona un vídeo antes de subir"
            );

            e.preventDefault();
        }
    });

});