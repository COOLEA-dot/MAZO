// Conexión al servidor Socket.IO (no usar ws:// ni wss:// manualmente)
const socket = io("/", {
  path: "/socket.io",
  transports: ["websocket", "polling"], // deja ambas para entorno cloud
  withCredentials: true                 // si usas sesión por cookies
});

// Variables globales (como ya tenías)
const chatBox = document.getElementById('chat-box');
let usernames = [chatBox.dataset.username, chatBox.dataset.recipient];
let room = `chat_${usernames.sort().join('_')}`;
let username = chatBox.dataset.username;
let recipient = chatBox.dataset.recipient;
console.log(room, username, recipient);

// Gestión de selección de archivos (igual que tenías)
let selectedFiles = [];

document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('file-input');
  const messageTextarea = document.getElementById('message');
  const previewContainer = document.getElementById('file-preview-container');

  fileInput?.addEventListener('change', () => {
    const newFiles = Array.from(fileInput.files);
    selectedFiles.push(...newFiles);
    renderFilePreview();
    fileInput.value = '';
  });

  function renderFilePreview() {
    if (!previewContainer) return;
    previewContainer.innerHTML = '';
    selectedFiles.forEach((file, index) => {
      const preview = document.createElement('div');
      preview.className = 'file-preview';

      const name = document.createElement('span');
      name.textContent = file.name;

      const remove = document.createElement('span');
      remove.className = 'remove-file';
      remove.textContent = '✖';
      remove.addEventListener('click', () => {
        selectedFiles.splice(index, 1);
        renderFilePreview();
      });

      preview.appendChild(name);
      preview.appendChild(remove);
      previewContainer.appendChild(preview);
    });
  }

  // ⬇️ Enviar mensaje (con append optimista)
  const form = document.getElementById('message-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const content = (messageTextarea?.value || '').trim();
    if (!content && selectedFiles.length === 0) return;

    // 1) Append optimista (para que el emisor lo vea ya)
    const tmpId = 'tmp-' + Date.now();
    displayMessage({
      username,
      message: content,
      message_id: tmpId,
      file_url: "",        // si envías archivos, rellena según tu flujo
      thumbnail_url: ""
    });

    // 2) Construye payload para el servidor
    const payload = {
      username,
      recipient,
      message: content
      // file: ... // Si vas a mandar archivos aquí, añade tu lógica Base64 o ruta
    };

    // 3) Emit con ACK (el backend debe ser @socketio.on('send_message') y devolver dict)
    socket.emit('send_message', payload, (ack) => {
      if (!ack || !ack.ok) {
        console.error('Fallo al enviar', ack);
        // Opcional: marca el mensaje optimista como error
        // markMessageAsError(tmpId);
        return;
      }
      // Opcional: reemplaza el tmpId por el id real
      // replaceTempId(tmpId, ack.message_id);
    });

    // 4) Limpia UI
    if (messageTextarea) messageTextarea.value = '';
    if (fileInput) fileInput.value = '';
    selectedFiles = [];
    renderFilePreview();
  });
});

// Conexión inicial
socket.on('connect', function () {
  console.log('Conectado al servidor');

  if (room && username && recipient) {
    socket.emit('join', { room: room });
    socket.emit('get_previous_messages', { room: room });
  } else {
    console.error('No se han asignado correctamente las variables: room, username, recipient');
  }
});

// 🔁 Rehacer join tras reconexión (clave en Render)
socket.on('reconnect', () => {
  console.log('Reconectado, rehaciendo join a la sala', room);
  if (room) {
    socket.emit('join', { room: room });
  }
});

// Recibe los mensajes previos al cargar el chat
socket.on('previous_messages', function (messages) {
  console.log('Mensajes previos recibidos:', messages);
  messages.forEach(displayMessage);
});

// Recibe mensajes nuevos (incluido el propio emisor)
socket.on('receive_message', function (data) {
  console.log('📥 Mensaje recibido en receive_message:', data, 'Usuario actual:', username);
  displayMessage(data);
});

// Recibe mensajes editados
socket.on('message_edited', function (data) {
    const messageElement = document.querySelector(`[data-message-id="${data.message_id}"] .message-text`);
    if (messageElement) {
        messageElement.innerHTML = `<strong>${data.username}:</strong> ${data.new_message}`;
    }
});

// Recibe mensajes eliminados
socket.on('message_deleted', function (data) {
    const messageElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
    if (messageElement) {
        messageElement.remove();
    }
});

// Enviar un nuevo mensaje
document.getElementById('message-form').addEventListener('submit', function (e) {
    e.preventDefault();

    const messageInput = document.getElementById('message');
    const fileInput = document.getElementById('file-input');
    const message = messageInput.value.trim();
    const maxFileSize = 5 * 1024 * 1024;

    const sendMessageToServer = (fileData = null, realFileUrl = null, filename = null) => {
        socket.emit('message', {
            username: username,
            recipient: recipient,
            message: message,
            file: fileData || realFileUrl,
            filename: filename || null
        });
    };

    if (selectedFiles.length > 0) {
        selectedFiles.forEach(file => {
            if (file.size <= maxFileSize) {
                const reader = new FileReader();
                reader.onload = function (event) {
                    sendMessageToServer(event.target.result, null, file.name);
                };
                reader.readAsDataURL(file);
            } else {
                const formData = new FormData();
                formData.append('file', file);

                const csrfToken = document.getElementById('csrf-token').value;

                fetch('/upload_file', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.file_url) {
                        sendMessageToServer(null, data.file_url, file.name);
                    } else {
                        console.error('Error al subir el archivo');
                    }
                })
                .catch(error => console.error('Error al subir el archivo:', error));
            }
        });
    } else if (message) {
        sendMessageToServer();
    }

    // Limpiar
    messageInput.value = '';
    fileInput.value = '';
    selectedFiles = [];
    updateFilePreview();
});

function displayMessage(data) {
    if (!data || !data.username || !data.message_id) return;

    const messagesContainer = document.getElementById('chat-box');
    console.log('Actualizando mensaje', data);

    const existingElement = document.querySelector(`[data-message-id="${data.message_id}"]`);
    const isMyMessage = data.username === username;

    // 🔧 Convertir a URL absoluta usando location.origin
    const toAbsoluteUrl = (path) => {
        if (!path) return '';
        if (path.startsWith('http')) return path;
        if (!path.startsWith('/')) path = '/' + path;
        return window.location.origin + path;
    };

    const fileUrl = toAbsoluteUrl(data.file_url);
    const thumbnailUrl = toAbsoluteUrl(data.thumbnail_url);

    let mediaContent = '';
    const filename = data.filename || (data.file_url ? data.file_url.split('/').pop() : '');
    const ext = filename.toLowerCase();

    if (data.file_url) {
        if (ext.endsWith('.mp4') || ext.endsWith('.mov') || ext.endsWith('.webm')) {
            const thumbnail = thumbnailUrl || toAbsoluteUrl("static/chat_uploads/thumbnails/default-thumbnail.jpg");
            mediaContent = `
                <div class="video-thumbnail" onclick="openVideoModal('${fileUrl}')">
                    <img src="${thumbnail}" class="chat-thumbnail" alt="Miniatura de video">
                    <i class="fa fa-play play-icon"></i>
                </div>`;
        } else if (ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.png') || ext.endsWith('.gif')) {
            mediaContent = `<img src="${fileUrl}" class="chat-thumbnail" alt="Imagen enviada" onclick="openImageModal('${fileUrl}')">`;
        } else if (ext.endsWith('.pdf')) {
            mediaContent = `
                <div class="file-thumbnail" onclick="window.location.href='${fileUrl}'">
                    <i class="fas fa-file-pdf file-icon pdf"></i>
                    <div class="file-name">${filename}</div>
                </div>`;
        } else if (ext.endsWith('.docx') || ext.endsWith('.pptx') || ext.endsWith('.xls') || ext.endsWith('.xlsx')) {
            let iconClass = 'fa-file-alt';
            if (ext.endsWith('.docx')) iconClass = 'fa-file-word file-icon word';
            if (ext.endsWith('.xls') || ext.endsWith('.xlsx')) iconClass = 'fa-file-excel file-icon excel';
            if (ext.endsWith('.pptx')) iconClass = 'fa-file-powerpoint file-icon ppt';

            mediaContent = `
                <div class="file-thumbnail" onclick="window.location.href='${fileUrl}'">
                    <i class="fas ${iconClass}"></i>
                    <div class="file-name">${filename}</div>
                </div>`;
        } else {
            mediaContent = `
                <i class="fas fa-file file-icon"></i>
                <a href="${fileUrl}" target="_blank">Descargar archivo</a>`;
        }
    } else if (data.message) {
        mediaContent = `<p class="message-text">${data.message}</p>`;
    }

    const messageOptions = isMyMessage ? `
        <div class="message-options">
            <span class="options-icon">⋮</span>
            <div class="options-menu">
                <button class="edit-message">Editar</button>
                <button class="delete-message">Borrar</button>
            </div>
        </div>` : '';

    const fullMessageHTML = `
        <div class="chat-message ${isMyMessage ? 'my-message' : 'other-message'}" data-message-id="${data.message_id}">
            <div class="message-content">
                ${mediaContent}
                ${messageOptions}
            </div>
        </div>`;

    if (existingElement) {
        existingElement.outerHTML = fullMessageHTML;
    } else {
        messagesContainer.insertAdjacentHTML('beforeend', fullMessageHTML);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }
}

// Delegación de eventos para editar/eliminar mensajes
document.addEventListener('click', function (event) {
    const target = event.target;

    // EDITAR MENSAJE en línea
    if (target.classList.contains('edit-message')) {
        event.preventDefault();

        const messageElement = target.closest('.chat-message');
        const messageTextElem = messageElement.querySelector('.message-text');
        if (!messageTextElem) return;

        const originalText = messageTextElem.innerText.replace(/^\w+: /, '');
        const username = messageTextElem.querySelector('strong')?.innerText.replace(':', '') || '';

        // Crear input de edición
        const input = document.createElement('input');
        input.type = 'text';
        input.value = originalText;
        input.classList.add('edit-input');

        messageTextElem.replaceWith(input);
        input.focus();

        // Guardar al presionar Enter o cancelar con Escape
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                const newMessage = input.value.trim();

                if (newMessage && newMessage !== originalText) {
                    socket.emit('edit_message', {
                        message_id: messageElement.dataset.messageId,
                        new_content: newMessage
                    });

                    input.replaceWith(createMessageTextElement(username, newMessage));
                } else {
                    input.replaceWith(createMessageTextElement(username, originalText));
                }

                document.removeEventListener('click', handleClickOutside);
            } else if (e.key === 'Escape') {
                input.replaceWith(createMessageTextElement(username, originalText));
                document.removeEventListener('click', handleClickOutside);
            }
        });

        // Guardar o cancelar si hace clic fuera del input
        function handleClickOutside(e) {
            if (e.target !== input && !input.contains(e.target)) {
                const newMessage = input.value.trim();

                if (newMessage && newMessage !== originalText) {
                    socket.emit('edit_message', {
                        message_id: messageElement.dataset.messageId,
                        new_content: newMessage
                    });

                    input.replaceWith(createMessageTextElement(username, newMessage));
                } else {
                    input.replaceWith(createMessageTextElement(username, originalText));
                }

                document.removeEventListener('click', handleClickOutside);
            }
        }

        // Escuchar clics fuera del input (después del evento actual)
        setTimeout(() => {
            document.addEventListener('click', handleClickOutside);
        }, 0);
    }

    // ELIMINAR MENSAJE
    if (target.classList.contains('delete-message')) {
        event.preventDefault();

        const messageElement = target.closest('.chat-message');

        if (confirm("¿Estás seguro de eliminar este mensaje?")) {
            socket.emit('delete_message', {
                message_id: messageElement.dataset.messageId
            });

            messageElement.remove();
            closeOtherMenus();
        }
    }
});

// ESCUCHAR mensaje editado desde el servidor y actualizarlo en tiempo real
socket.on('message_edited', (data) => {
    const messageElement = document.querySelector(`.chat-message[data-message-id="${data.message_id}"]`);
    if (messageElement) {
        const oldInput = messageElement.querySelector('.edit-input');
        if (oldInput) {
            oldInput.replaceWith(createMessageTextElement(data.username, data.new_message));
        } else {
            const messageTextElem = messageElement.querySelector('.message-text');
            if (messageTextElem) {
                messageTextElem.innerHTML = `<strong>${data.username}:</strong> ${data.new_message}`;
            }
        }
    }
});

// Función auxiliar para recrear el mensaje HTML
function createMessageTextElement(username, message) {
    const p = document.createElement('p');
    p.classList.add('message-text');
    p.innerHTML = `<strong>${username}:</strong> ${message}`;
    return p;
}

// ✅ Función para enviar archivos con vista previa (segura y robusta)
function updateFilePreview(files) {
    const previewContainer = document.getElementById('file-preview-container');
    previewContainer.innerHTML = ''; // Limpiar previews anteriores

    if (!files || files.length === 0) {
        return; // Si no hay archivos válidos, salir
    }

    Array.from(files).forEach((file, index) => {
        const previewItem = document.createElement('div');
        previewItem.classList.add('file-preview-item');
        previewItem.innerHTML = `
            <span>${file.name}</span>
            <button type="button" class="remove-file" data-index="${index}">&times;</button>
        `;
        previewContainer.appendChild(previewItem);
    });

    // 🧹 Botones para eliminar archivos seleccionados
    previewContainer.querySelectorAll('.remove-file').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            const dt = new DataTransfer();
            const input = document.getElementById('file-input');
            const currentFiles = Array.from(input.files);

            currentFiles.forEach((file, i) => {
                if (i !== index) dt.items.add(file);
            });

            input.files = dt.files;
            updateFilePreview(dt.files); // Recargar vista previa actualizada
        });
    });
}

// Cerrar menús de opciones (los tres puntitos)
function closeOtherMenus() {
    document.querySelectorAll('.options-menu').forEach(menu => {
        menu.style.display = 'none';
    });
}

// Función auxiliar para cerrar menús de opciones
function closeOtherMenus() {
    document.querySelectorAll('.options-menu').forEach(menu => {
        menu.style.display = 'none';
    });
}

// Cerrar menús flotantes (si tienes lógica para mostrar/ocultar menú de opciones)
function closeOtherMenus() {
    document.querySelectorAll('.options-menu').forEach(menu => {
        menu.style.display = 'none';
    });
}

// Escuchar el mensaje procesado desde el servidor y reemplazar el temporal
socket.on('message', function (data) {
    // Eliminar el mensaje temporal si hay un temp_id
    if (data.temp_id) {
        const tempMsg = document.querySelector(`[data-message-id="${data.temp_id}"]`);
        if (tempMsg) tempMsg.remove();
    }

    displayMessage(data);
});

// Función para cerrar otros menús de opciones abiertos
function closeOtherMenus() {
    document.querySelectorAll('.options-menu.active').forEach(menu => {
        menu.classList.remove('active');
    });
}

// Delegación de eventos para abrir/cerrar el menú de opciones
document.addEventListener('click', function (event) {
    const target = event.target;

    // Si se hace clic en los tres puntos, mostrar el menú
    if (target.classList.contains('options-icon')) {
        event.stopPropagation(); // Evitar que se cierren de inmediato
        closeOtherMenus(); // Cerrar otros menús antes de abrir el actual

        const optionsMenu = target.nextElementSibling;
        if (optionsMenu) {
            optionsMenu.classList.toggle('active');
        }
    } else {
        // Cerrar menús si se hace clic fuera de ellos
        closeOtherMenus();
    }
});

// Función para abrir una imagen en el modal 
function openImageModal(imageUrl) {
    const modal = document.getElementById("image-modal");
    const imageElement = document.getElementById("modal-image");
    const downloadLink = document.getElementById("download-link");

    // Asignar la URL de la imagen y mostrarla en el modal
    imageElement.src = imageUrl;

    // Asignar la URL al enlace de descarga
    downloadLink.href = imageUrl;
    downloadLink.setAttribute("download", imageUrl.split('/').pop()); // Nombre correcto

    // Mostrar el modal
    modal.style.display = "flex";
}

// Función para cerrar el modal al hacer clic fuera de la imagen
document.getElementById("image-modal").addEventListener("click", function(event) {
    const imageElement = document.getElementById("modal-image");

    // Verificar si se hizo clic fuera de la imagen
    if (event.target === this) {
        closeImageModal(); // Llamar a la función para cerrar el modal
    }
});

// Función para cerrar el modal
function closeImageModal() {
    const modal = document.getElementById("image-modal");
    const imageElement = document.getElementById("modal-image");

    imageElement.src = ""; // Limpiar la fuente de la imagen
    modal.style.display = "none"; // Ocultar el modal
}


// Función para abrir un video en el modal
function openVideoModal(videoUrl) {
    const modal = document.getElementById("video-modal");
    const videoElement = document.getElementById("modal-video");
    const downloadLink = document.getElementById("video-download-link");

    // Asignar la URL del video y reproducir automáticamente
    videoElement.src = videoUrl;
    videoElement.play();

    // Asignar la URL al enlace de descarga
    downloadLink.href = videoUrl;
    downloadLink.setAttribute("download", videoUrl.split('/').pop()); // Nombre correcto

    // Mostrar el modal
    modal.style.display = "flex";
}

// Función para cerrar el modal al hacer clic fuera del video
document.getElementById("video-modal").addEventListener("click", function(event) {
    const videoElement = document.getElementById("modal-video");

    // Verificar si se hizo clic fuera del video
    if (event.target === this) {
        videoElement.pause();
        videoElement.src = ""; // Limpiar la fuente
        this.style.display = "none"; // Ocultar el modal
    }
});

