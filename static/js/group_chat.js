document.addEventListener('DOMContentLoaded', async () => {
    await initSocket();
    joinGroupRoom();
    attachGroupMessageFormHandler();
    attachGroupMediaHandlers();
    injectOptionsIcons();
});



function getCsrfToken() {
    // 1️⃣ Meta tag (recomendado)
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    // 2️⃣ Fallback por input hidden
    const input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;

    console.warn('[CSRF] token no encontrado');
    return null;
}

/* ===============================
   SOCKET INIT
   =============================== */
function initSocket() {
    if (window.socket) return;

    window.socket = io({
        path: '/socket.io',
        transports: ['websocket', 'polling'],
        withCredentials: true
    });

    window.socket.on('connect', () => {
        console.log('[group] socket connected', window.socket.id);
    });

    window.socket.on('group_message', handleIncomingGroupMessage);

    window.socket.on('group_message_edited', (data) => {
        const { message_id, new_content } = data;

        const msgEl = document.querySelector(
            `.chat-message[data-message-id="${message_id}"]`
        );
        if (!msgEl) return;

        const textEl = msgEl.querySelector('.message-text');
        if (textEl) textEl.textContent = new_content;
    });

    window.socket.on('group_message_deleted', (data) => {
        const el = document.querySelector(
            `.chat-message[data-message-id="${data.message_id}"]`
        );
        if (el) el.remove();
    });
}


/* ===============================
   JOIN GROUP
   =============================== */
function joinGroupRoom() {
    const chatBox = document.getElementById('chat-box');
    const groupId = chatBox?.dataset?.groupId;
    if (!groupId) return;

    console.log('[group] join_group', groupId);
    socket.emit('join_group', { group_id: Number(groupId) });
}

/* ===============================
   SEND MESSAGE
   =============================== */
function attachGroupMessageFormHandler() {
    const form = document.getElementById('group-message-form');
    const textarea = document.getElementById('message');
    const fileInput = document.getElementById('file-input');

    // ⛔ PROTECCIÓN
    if (!form || !textarea || !fileInput) {
        console.warn('[group] form elements not found');
        return;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = textarea.value.trim();
        const file = fileInput.files.length > 0 ? fileInput.files[0] : null;

        if (!text && !file) return;

        console.log('[group] submit message', { text, file });

        await sendGroupMessage({
            text,
            file,
            filename: file ? file.name : null
        });

        textarea.value = '';
        fileInput.value = '';
    });
}

function renderGroupMessage(payload) {
    const chatBox = document.getElementById('chat-box');
    const myUsername = chatBox.dataset.myUsername;
    const isMine = payload.username === myUsername;

    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${isMine ? 'my-message' : 'other-message'}`;
    wrapper.dataset.messageId = payload.message_id;

    const content = document.createElement('div');
    content.className = 'message-content';

    if (!isMine) {
        const author = document.createElement('strong');
        author.textContent = payload.username;
        author.style.fontSize = '12px';
        author.style.display = 'block';
        author.style.marginBottom = '4px';
        content.appendChild(author);
    }

    /* ===== CONTENIDO ===== */
    if (payload.file_url) {
        const ext = payload.file_url.split('.').pop().toLowerCase();

        if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
            const img = document.createElement('img');
            img.src = payload.file_url;
            img.className = 'chat-thumbnail';
            img.dataset.fileUrl = payload.file_url;
            content.appendChild(img);

        } else if (['mp4','webm','mov','avi','mpg'].includes(ext)) {
            const videoThumb = document.createElement('div');
            videoThumb.className = 'video-thumbnail';
            videoThumb.dataset.fileUrl = payload.file_url;

            const img = document.createElement('img');
            img.src = payload.thumbnail_url || '/static/chat_uploads/thumbnails/default-thumbnail.jpg';
            img.className = 'chat-thumbnail';

            const play = document.createElement('i');
            play.className = 'fa fa-play play-icon';

            videoThumb.appendChild(img);
            videoThumb.appendChild(play);
            content.appendChild(videoThumb);

        } else {
            const file = document.createElement('div');
            file.className = 'file-thumbnail';
            file.dataset.fileUrl = payload.file_url;
            file.innerHTML = `
                <i class="fas fa-file"></i>
                <div class="file-name">${payload.file_url.split('/').pop()}</div>
            `;
            content.appendChild(file);
        }
    } else {
        const p = document.createElement('p');
        p.className = 'message-text';
        p.textContent = payload.message;
        content.appendChild(p);
    }

    /* ===== OPCIONES (SOLO PROPIOS) ===== */
    if (isMine) {
        const options = document.createElement('div');
        options.className = 'message-options';

        const icon = document.createElement('span');
        icon.className = 'options-icon';
        icon.textContent = '⋮';

        options.appendChild(icon);
        content.appendChild(options);
    }

    wrapper.appendChild(content);
    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}


async function sendGroupMessage({ text = '', file = null, filename = null }) {
    const chatBox = document.getElementById('chat-box');
    const groupId = Number(chatBox.dataset.groupId);

    const payload = {
        group_id: groupId,
        message: text || ''
    };

    // =========================
    // SI HAY ARCHIVO
    // =========================
    if (file) {
        // Archivo pequeño → Base64
        if (file instanceof File && file.size <= 200000) {
            const base64 = await fileToBase64(file);
            payload.file = base64;
            payload.filename = file.name;

        // Archivo grande → upload_file
        } else if (file instanceof File) {
            const uploadResp = await uploadFileToServer(file);
            payload.file = uploadResp.stream_url || uploadResp.file_path;
            payload.filename = file.name;

        // Ya es URL (por ejemplo reenviado)
        } else if (typeof file === 'string') {
            payload.file = file;
            payload.filename = filename || file.split('/').pop();
        }
    }

    console.log('[group] send_group_message', payload);

    socket.emit('send_group_message', payload, (ack) => {
        console.log('[group] ACK', ack);
    });
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

async function uploadFileToServer(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('filename', file.name);
    formData.append('folder', 'static/chat_uploads');

    const csrfToken = getCsrfToken();

    const res = await fetch('/upload_file', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    });

    if (!res.ok) {
        const txt = await res.text();
        console.error('[upload_file] error response:', txt);
        throw new Error('Upload failed');
    }

    return await res.json();
}

/* ===============================
   RECEIVE MESSAGE
   =============================== */
function handleIncomingGroupMessage(payload) {
    console.log('[group] received', payload);

    const chatBox = document.getElementById('chat-box');
    const myUsername = chatBox.dataset.myUsername;
    const isMine = payload.username === myUsername;

    const wrapper = document.createElement('div');
    wrapper.className = `chat-message ${isMine ? 'my-message' : 'other-message'}`;

    const content = document.createElement('div');
    content.className = 'message-content';

    if (!isMine) {
        const author = document.createElement('strong');
        author.textContent = payload.username;
        author.style.fontSize = '12px';
        author.style.display = 'block';
        author.style.marginBottom = '4px';
        content.appendChild(author);
    }

    // =========================
    // ARCHIVOS
    // =========================
    if (payload.file_url) {
        const ext = payload.file_url.split('.').pop().toLowerCase();

        // 🖼️ IMAGEN
        if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
            const img = document.createElement('img');
            img.src = payload.file_url;
            img.className = 'chat-thumbnail';
            img.style.cursor = 'pointer';
            img.onclick = () => openImageModal(payload.file_url);
            content.appendChild(img);

        // 🎥 VIDEO
        } else if (['mp4', 'webm', 'mov', 'avi', 'mpg'].includes(ext)) {
            const thumbWrapper = document.createElement('div');
            thumbWrapper.className = 'video-thumbnail';
            thumbWrapper.style.cursor = 'pointer';
            thumbWrapper.dataset.fileUrl = payload.file_url;

            if (payload.thumbnail_url) {
                const thumb = document.createElement('img');
                thumb.src = payload.thumbnail_url;
                thumb.className = 'chat-thumbnail';
                thumbWrapper.appendChild(thumb);
            } else {
                const placeholder = document.createElement('div');
                placeholder.textContent = '▶ Video';
                placeholder.className = 'video-placeholder';
                thumbWrapper.appendChild(placeholder);
            }

            
            content.appendChild(thumbWrapper);

        // 📎 ARCHIVO
        } else {
            const file = document.createElement('div');
            file.className = 'file-thumbnail';
            file.style.cursor = 'pointer';
            file.innerHTML = `
                <i class="fas fa-file"></i>
                <span>${payload.file_url.split('/').pop()}</span>
            `;
            
            content.appendChild(file);
        }

    // =========================
    // TEXTO
    // =========================
    } else {
        const p = document.createElement('p');
        p.className = 'message-text';
        p.textContent = payload.message;
        content.appendChild(p);
    }

    wrapper.appendChild(content);
    chatBox.appendChild(wrapper);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function attachGroupMediaHandlers() {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return;

    chatBox.addEventListener('click', (e) => {

        /* ===== 🎥 VIDEOS (PRIMERO, MUY IMPORTANTE) ===== */
        const videoThumb = e.target.closest('.video-thumbnail');
        if (videoThumb) {
            e.preventDefault();
            e.stopPropagation();

            const src = videoThumb.dataset.fileUrl;
            if (src) {
                showGroupVideoModal(src); // ⬅️ SIEMPRE EL MP4
            }
            return;
        }

        /* ===== 🖼️ IMÁGENES (SOLO IMÁGENES REALES) ===== */
        const img = e.target.closest('.chat-thumbnail');
        if (
            img &&
            img.tagName === 'IMG' &&
            !img.closest('.video-thumbnail') // ⛔ evita miniaturas de vídeo
        ) {
            e.preventDefault();
            e.stopPropagation();
            openImageModal(img.src);
            return;
        }

        /* ===== 📎 ARCHIVOS ===== */
        const fileThumb = e.target.closest('.file-thumbnail');
        if (fileThumb) {
            e.preventDefault();
            e.stopPropagation();
            const src = fileThumb.dataset.fileUrl;
            if (src) window.open(src, '_blank');
        }
    });
}


function openImageModal(src) {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image');

    img.src = src;
    modal.style.display = 'flex';
}

function showGroupVideoModal(url, filename = null) {
    const modal = document.getElementById('video-modal');
    const video = document.getElementById('modal-video');
    const download = document.getElementById('video-download-link');

    if (!modal || !video) return;

    // 🧹 limpiar completamente
    video.pause();
    while (video.firstChild) video.removeChild(video.firstChild);

    // 🎥 source real
    const src = document.createElement('source');
    src.src = url;

    const ext = (url.split('.').pop() || '').toLowerCase();
    src.type = (ext === 'mp4' || ext === 'm4v')
        ? 'video/mp4'
        : `video/${ext}`;

    video.appendChild(src);
    video.load();

    try { video.play().catch(() => {}); } catch (e) {}

    // ⬇️ activar botón DESCARGAR
    if (download) {
        download.href = url;
        download.setAttribute(
            'download',
            filename || url.split('/').pop()
        );
        download.style.display = 'inline-block';
    }

    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
}


document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();

        const modal = btn.closest('.modal');
        modal.style.display = 'none';

        const video = modal.querySelector('video');
        if (video) {
            video.pause();
            video.removeAttribute('src');
            video.load();
        }
    });
});

document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';

            const video = modal.querySelector('video');
            if (video) {
                video.pause();
                video.removeAttribute('src');
                video.load();
            }
        }
    });
});

/* ====================================================
   Popup de opciones (Editar / Borrar) — GRUPO
   Copiado 1:1 desde chat.js
   ==================================================== */

(function () {
  const popupId = 'mazo-options-popup';
  let popup = document.getElementById(popupId);

  function createPopup() {
    if (popup) return popup;

    popup = document.createElement('div');
    popup.id = popupId;
    popup.setAttribute('role', 'menu');
    popup.style.position = 'absolute';
    popup.style.minWidth = '120px';
    popup.style.background = '#fff';
    popup.style.border = '1px solid rgba(0,0,0,0.08)';
    popup.style.boxShadow = '0 6px 18px rgba(0,0,0,0.12)';
    popup.style.borderRadius = '8px';
    popup.style.padding = '6px';
    popup.style.zIndex = 3000;
    popup.style.display = 'none';
    popup.style.fontSize = '14px';
    popup.style.userSelect = 'none';

    const arrow = document.createElement('div');
    arrow.style.position = 'absolute';
    arrow.style.width = '10px';
    arrow.style.height = '10px';
    arrow.style.transform = 'rotate(45deg)';
    arrow.style.background = '#fff';
    arrow.style.borderLeft = '1px solid rgba(0,0,0,0.06)';
    arrow.style.borderTop = '1px solid rgba(0,0,0,0.06)';
    arrow.style.zIndex = -1;
    arrow.className = 'mazo-popup-arrow';
    popup.appendChild(arrow);

    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'mazo-popup-btn mazo-popup-edit';
    btnEdit.textContent = 'Editar';

    const btnDelete = document.createElement('button');
    btnDelete.type = 'button';
    btnDelete.className = 'mazo-popup-btn mazo-popup-delete';
    btnDelete.textContent = 'Borrar';
    btnDelete.style.color = '#d33';

    [btnEdit, btnDelete].forEach(b => {
      b.style.display = 'block';
      b.style.width = '100%';
      b.style.padding = '8px 10px';
      b.style.background = 'transparent';
      b.style.border = 'none';
      b.style.textAlign = 'left';
      b.style.cursor = 'pointer';
      b.style.borderRadius = '6px';

      b.addEventListener('mouseenter', () => b.style.background = 'rgba(0,0,0,0.04)');
      b.addEventListener('mouseleave', () => b.style.background = 'transparent');
    });

    popup.appendChild(btnEdit);
    popup.appendChild(btnDelete);
    document.body.appendChild(popup);

    return popup;
  }

  let currentTarget = null;

  function openPopup(buttonEl, messageId) {
    const p = createPopup();
    currentTarget = { buttonEl, messageId };

    const rect = buttonEl.getBoundingClientRect();
    const preferLeft = rect.left + rect.width + 8 + p.offsetWidth > window.innerWidth;

    let top = window.scrollY + rect.top + (rect.height / 2) - 20;
    let left = preferLeft
      ? window.scrollX + rect.left - p.offsetWidth - 8
      : window.scrollX + rect.left + rect.width + 8;

    const maxTop = window.scrollY + window.innerHeight - p.offsetHeight - 12;
    if (top > maxTop) top = maxTop;
    if (top < 12) top = 12;

    p.style.left = `${left}px`;
    p.style.top = `${top}px`;
    p.style.display = 'block';
    p.dataset.currentMessageId = messageId || '';

    const arrow = p.querySelector('.mazo-popup-arrow');
    if (arrow) {
      arrow.style.left = preferLeft ? `${p.offsetWidth - 18}px` : `8px`;
      arrow.style.top = '-6px';
    }
  }

  function closePopup() {
    const p = createPopup();
    p.style.display = 'none';
    currentTarget = null;
  }

  document.addEventListener('click', (e) => {
    const icon = e.target.closest('.options-icon, .options-icon *');
    if (icon) {
      const btn = icon.closest('.options-icon') || e.target;
      const msgEl = btn.closest('.chat-message');
      if (!msgEl) return;

      const messageId = msgEl.dataset.messageId;
      if (currentTarget && currentTarget.messageId === messageId) {
        closePopup();
        return;
      }
      openPopup(btn, messageId);
      e.stopPropagation();
      return;
    }

    const popupEl = document.getElementById(popupId);
    if (popupEl && popupEl.style.display === 'block' && !e.target.closest('#' + popupId)) {
      closePopup();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePopup();
  });

  document.body.addEventListener('click', (e) => {
    const p = createPopup();
    if (p.style.display !== 'block') return;

    const editBtn = e.target.closest('.mazo-popup-edit');
    const deleteBtn = e.target.closest('.mazo-popup-delete');
    if (!editBtn && !deleteBtn) return;

    const messageId = currentTarget?.messageId;
    if (!messageId) return closePopup();

    if (editBtn) {
      openInlineEditorForMessage(messageId);
    } else if (deleteBtn) {
      confirmAndDeleteMessage(messageId);
    }

    setTimeout(closePopup, 50);
    e.stopPropagation();
  });

  window.addEventListener('resize', closePopup);
  window.addEventListener('scroll', closePopup, true);
})();


async function emitEditGroupMessage(messageId, newContent, timeoutMs = 7000) {
  return new Promise((resolve) => {
    let called = false;

    socket.emit(
      'edit_group_message',
      { message_id: messageId, new_content: newContent },
      (ack) => {
        called = true;
        resolve(ack || null);
      }
    );

    setTimeout(() => {
      if (!called) resolve(null);
    }, timeoutMs);
  });
}

function confirmAndDeleteMessage(messageId) {
  if (!messageId) return;

  if (!confirm('¿Eliminar este mensaje?')) return;

  deleteGroupMessage(messageId);
}

async function deleteGroupMessage(messageId) {
  try {
    console.log('[group] delete message', messageId);

    const ack = await emitDeleteGroupMessage(messageId);

    if (ack && ack.ok === false) {
      alert('No se pudo borrar el mensaje');
      return;
    }

    // Fallback: eliminar del DOM si el backend no emite evento
    const el = document.querySelector(
      `.chat-message[data-message-id="${messageId}"]`
    );
    if (el) el.remove();

  } catch (err) {
    console.error('[group] delete error', err);
    alert('Error al borrar el mensaje');
  }
}
async function emitDeleteGroupMessage(messageId, timeoutMs = 7000) {
  return new Promise((resolve) => {
    let called = false;

    if (!window.socket) {
      console.error('[group] socket no disponible');
      resolve(null);
      return;
    }

    window.socket.emit(
      'delete_group_message',
      { message_id: messageId },
      (ack) => {
        called = true;
        resolve(ack || null);
      }
    );

    setTimeout(() => {
      if (!called) resolve(null);
    }, timeoutMs);
  });
}
/* ==========================================================
   EDITAR MENSAJE (INLINE) — CHAT DE GRUPO
   ========================================================== */

/* ---------- SOCKET EMIT ---------- */
async function emitEditGroupMessage(messageId, newContent, timeoutMs = 7000) {
  if (!messageId) throw new Error('messageId required');
  if (!window.socket || typeof window.socket.emit !== 'function') {
    throw new Error('socket_not_initialized');
  }

  console.log('[group edit] emit ->', { message_id: messageId, new_content: newContent });

  return new Promise((resolve) => {
    let called = false;

    window.socket.emit(
      'edit_group_message',
      { message_id: messageId, new_content: newContent },
      (ack) => {
        called = true;
        console.log('[group edit] ACK:', ack);
        resolve(ack || null);
      }
    );

    setTimeout(() => {
      if (!called) {
        console.warn('[group edit] ACK timeout');
        resolve(null);
      }
    }, timeoutMs);
  });
}

/* ---------- FUNCIÓN LÓGICA ---------- */
async function editGroupMessage(messageId, newText) {
  try {
    await emitEditGroupMessage(messageId, newText);
  } catch (err) {
    console.error('[group] edit error', err);
    throw err;
  }
}

/* ---------- INLINE EDITOR ---------- */
function openInlineEditorForMessage(messageId) {
  console.log('[group inline edit] open', messageId);

  if (!messageId) {
    const popup = document.getElementById('mazo-options-popup');
    messageId = popup?.dataset?.currentMessageId;
  }
  if (!messageId) return;

  const msgEl = document.querySelector(
    `.chat-message[data-message-id="${messageId}"]`
  );
  if (!msgEl) return;

  // evitar duplicados
  if (msgEl.querySelector('.inline-edit-wrapper')) {
    msgEl.querySelector('textarea')?.focus();
    return;
  }

  const textEl = msgEl.querySelector('.message-text');
  if (!textEl) return;

  const originalText = textEl.textContent.trim();

  /* ---------- UI ---------- */
  const wrap = document.createElement('div');
  wrap.className = 'inline-edit-wrapper';
  wrap.style.display = 'flex';
  wrap.style.flexDirection = 'column';
  wrap.style.gap = '8px';
  wrap.style.marginTop = '6px';

  const textarea = document.createElement('textarea');
  textarea.value = originalText;
  textarea.rows = Math.min(6, Math.max(2, originalText.split('\n').length));
  textarea.style.width = '100%';
  textarea.style.padding = '8px';
  textarea.style.borderRadius = '8px';
  textarea.style.border = '1px solid rgba(0,0,0,0.15)';
  textarea.style.fontSize = '0.95rem';

  const buttons = document.createElement('div');
  buttons.style.display = 'flex';
  buttons.style.justifyContent = 'flex-end';
  buttons.style.gap = '8px';

  const btnSave = document.createElement('button');
  btnSave.textContent = 'Guardar';
  btnSave.style.background = '#0b76ff';
  btnSave.style.color = '#fff';
  btnSave.style.border = 'none';
  btnSave.style.borderRadius = '8px';
  btnSave.style.padding = '6px 10px';
  btnSave.style.cursor = 'pointer';

  const btnCancel = document.createElement('button');
  btnCancel.textContent = 'Cancelar';
  btnCancel.style.border = '1px solid rgba(0,0,0,0.15)';
  btnCancel.style.background = '#fff';
  btnCancel.style.borderRadius = '8px';
  btnCancel.style.padding = '6px 10px';
  btnCancel.style.cursor = 'pointer';

  buttons.appendChild(btnCancel);
  buttons.appendChild(btnSave);

  wrap.appendChild(textarea);
  wrap.appendChild(buttons);

  textEl.style.display = 'none';
  textEl.parentElement.appendChild(wrap);

  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);

  /* ---------- HELPERS ---------- */
  function cleanup() {
    wrap.remove();
    textEl.style.display = '';
  }

  async function save() {
    const newText = textarea.value.trim();
    btnSave.disabled = true;
    btnCancel.disabled = true;
    btnSave.textContent = 'Guardando…';

    try {
      await editGroupMessage(messageId, newText);
      textEl.textContent = newText;
      textEl.style.display = '';

      if (!msgEl.querySelector('.edited-badge')) {
        const badge = document.createElement('span');
        badge.className = 'edited-badge';
        badge.textContent = ' (editado)';
        badge.style.fontSize = '0.8rem';
        badge.style.opacity = '0.8';
        textEl.parentElement.appendChild(badge);
      }
    } catch (err) {
      alert('Error al editar el mensaje');
      console.error(err);
    } finally {
      cleanup();
    }
  }

  function cancel() {
    cleanup();
  }

  /* ---------- EVENTS ---------- */
  btnSave.addEventListener('click', save);
  btnCancel.addEventListener('click', cancel);

  textarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      save();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      cancel();
    }
  });
}

/* ---------- COMPAT ---------- */
function openEditModal(messageId) {
  openInlineEditorForMessage(messageId);
}

/* ---------- SOCKET UPDATE ---------- */
window.socket?.on('group_message_edited', (data) => {
  const { message_id, new_content } = data;

  const msgEl = document.querySelector(
    `.chat-message[data-message-id="${message_id}"]`
  );
  if (!msgEl) return;

  const textEl = msgEl.querySelector('.message-text');
  if (textEl) textEl.textContent = new_content;
});
