// ==============================
// registerSocketHandlers (ACTUALIZADA)
// ==============================
function registerSocketHandlers(s) {
  if (!s || typeof s.on !== 'function') {
    console.warn('registerSocketHandlers: socket no válido');
    return;
  }
  if (s._mazo_handlers_registered) {
    console.log('registerSocketHandlers: handlers ya registrados, no duplicar.');
    return;
  }

  // Helper seguro para registrar handlers (evita que un handler rompa el registro)
  const safeRegister = (eventName, handler) => {
    try {
      s.on(eventName, handler);
    } catch (err) {
      console.warn(`registerSocketHandlers: error registrando handler ${eventName}`, err);
    }
  };

  // Helper para extraer el objeto "message" del payload en distintas formas
  const normalizePayloadMessage = (payload) => {
    if (!payload) return null;
    if (payload.id || payload.message_id || payload.content || payload.file_url) return payload;
    if (payload.message) return payload.message;
    return payload;
  };

  // Eventos de conexión / depuración
  safeRegister('connect', () => {
    console.log('[socket] connect id=', s.id);
    // Intentar auto-join si la función existe (pequeña espera para evitar race)
    if (typeof autoJoinRoom === 'function') {
      try {
        setTimeout(() => {
          try { autoJoinRoom(); } catch (e) { console.warn('autoJoinRoom error on connect', e); }
        }, 80);
      } catch (e) {
        console.warn('registerSocketHandlers: fallo intentando autoJoinRoom', e);
      }
    }
  });

  // Mejor logging en connect_error (muestra objeto y posible response)
  safeRegister('connect_error', (err) => {
    try {
      // socket.io puede entregar objetos complejos; intentamos serializar algo útil
      console.error('[socket] connect_error', err);
      if (err && err.message) console.error('[socket] connect_error message:', err.message);
      if (err && err.data) console.error('[socket] connect_error data:', err.data);
    } catch (e) {
      console.error('[socket] connect_error (logging failed)', e);
    }
  });

  safeRegister('reconnect', (attempt) => console.log('[socket] reconnect attempt=', attempt));
  safeRegister('reconnect_attempt', (n) => console.log('[socket] reconnect_attempt', n));
  safeRegister('disconnect', (reason) => console.log('[socket] disconnect', reason));
  safeRegister('error', (err) => console.warn('[socket] error', err));

  // Eventos de aplicación (mensajería)
  safeRegister('receive_message', (payload) => {
    console.log('[socket] receive_message raw payload:', payload);
    try {
      const msg = normalizePayloadMessage(payload);
      if (msg && (msg.id || msg.message_id || msg.content || msg.file_url || msg.username)) {
        try {
          handleSocketNewMessage({ message: msg, room_id: payload.room_id || payload.room || null });
        } catch (e) {
          try { handleSocketNewMessage(msg); } catch (ee) { console.warn('handleSocketNewMessage fallback error', ee); }
        }
      } else {
        try { handleSocketNewMessage({ message: payload, room_id: payload.room_id || payload.room || null }); }
        catch (e) { console.warn('handleSocketNewMessage final fallback error', e); }
      }
    } catch (e) {
      console.warn('handleSocketNewMessage error', e);
    }
  });

  safeRegister('message_edited', (payload) => {
    console.log('[socket] message_edited payload:', payload);
    try {
      if (typeof handleSocketEditedMessage === 'function') {
        handleSocketEditedMessage({ message: payload });
      } else {
        console.warn('handleSocketEditedMessage no definido');
      }
    } catch (e) {
      console.warn('handleSocketEditedMessage error', e);
    }
  });

  safeRegister('message_deleted', (payload) => {
    console.log('[socket] message_deleted payload:', payload);
    try {
      if (typeof handleSocketDeletedMessage === 'function') {
        handleSocketDeletedMessage(payload);
      } else {
        console.warn('handleSocketDeletedMessage no definido');
      }
    } catch (e) {
      console.warn('handleSocketDeletedMessage error', e);
    }
  });

  // Eventos de sala / presencia
  safeRegister('join_ack', (payload) => {
    console.log('[socket] join_ack:', payload);
    try {
      if (payload && payload.ok) {
        // marca que el socket está en la room (útil para lógica local)
        s._mazo_joined_room = payload.room || true;
      } else {
        s._mazo_joined_room = false;
      }
    } catch (e) {
      console.warn('join_ack handler error', e);
    }
  });

  safeRegister('user_joined', (payload) => {
    console.log('[socket] user_joined:', payload);
    try {
      if (typeof onUserJoined === 'function') {
        try { onUserJoined(payload.username); } catch(e){ console.warn('onUserJoined handler error', e); }
      }
    } catch (e) {
      console.warn('user_joined handler error', e);
    }
  });

  // Eventos opcionales
  safeRegister('user_left', (payload) => { console.log('[socket] user_left', payload); });
  safeRegister('typing', (payload) => { /* opcional: mostrar indicador de tecleo */ });

  // Marca para evitar duplicados
  s._mazo_handlers_registered = true;
  console.log('registerSocketHandlers: handlers registrados.');

  // Si tienes una cola de safeOn, registrarla ahora
  if (typeof flushSafeOnQueue === 'function') {
    try {
      flushSafeOnQueue();
    } catch (e) {
      console.warn('registerSocketHandlers: flushSafeOnQueue falló', e);
    }
  }
}


// ==============================
// initSocket (ACTUALIZADA)
// ==============================
// INIT SOCKET con PRE-FLIGHT y logging extendido
async function socketPreflightCheck(path = (CHAT_CONFIG && CHAT_CONFIG.SOCKET_PATH) ? CHAT_CONFIG.SOCKET_PATH : '/socket.io') {
  try {
    const origin = window.location.origin.replace(/\/$/, '');
    // engine.io polling handshake URL (EIO=4 para socket.io v4)
    const testUrl = `${origin}${path}/?EIO=4&transport=polling&t=${Date.now()}`;
    console.log('[PRE-FLIGHT] probing socket endpoint:', testUrl);

    const res = await fetch(testUrl, { method: 'GET', credentials: 'include' });
    console.log('[PRE-FLIGHT] status:', res.status, res.statusText);
    const text = await res.text().catch(()=>null);
    if (text) {
      // limitar longitud por si es enorme
      console.log('[PRE-FLIGHT] body (truncated 2000):', text.length > 2000 ? (text.slice(0,2000) + '...') : text);
    } else {
      console.log('[PRE-FLIGHT] no body returned or could not parse as text (maybe 204 or streaming)');
    }
    return { ok: res.ok, status: res.status, text };
  } catch (err) {
    console.warn('[PRE-FLIGHT] fetch error:', err);
    return { ok: false, error: err };
  }
}

async function initSocketWithDiagnostics(namespace = '') {
  if (typeof io === 'undefined') {
    console.error('[initSocket] socket.io client (io) NO está cargado.');
    return null;
  }

  const path = (CHAT_CONFIG && CHAT_CONFIG.SOCKET_PATH) ? CHAT_CONFIG.SOCKET_PATH : '/socket.io';
  const origin = window.location.origin.replace(/\/$/, '');
  // Mostrar la URL exacta que vamos a usar para socket
  let socketUrl = origin;
  if (namespace && namespace.trim()) {
    socketUrl = namespace.startsWith('/') ? (origin + namespace) : (origin + '/' + namespace.replace(/^\/+/, ''));
  }
  console.log('[initSocketWithDiagnostics] origin=', origin, ' path=', path, ' socketUrl=', socketUrl);

  // Preflight: intenta GET a engine.io polling para ver respuesta del servidor
  const pre = await socketPreflightCheck(path);
  if (!pre.ok) {
    console.warn('[initSocketWithDiagnostics] PRE-FLIGHT indica problema. Continuo de todas formas (pero revisa la Response anterior).');
  } else {
    console.log('[initSocketWithDiagnostics] PRE-FLIGHT OK (server responde).');
  }

  // opciones robustas
  const opts = {
    path,
    transports: ['websocket', 'polling'],
    withCredentials: true,
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: 12,
    reconnectionDelay: 500,
    timeout: 20000
  };

  try {
    console.log('[initSocketWithDiagnostics] creando socket con URL=', socketUrl, ' opts=', opts);
    // si ya hay socket y está vivo, reutilizar
    if (window.socket && typeof window.socket.on === 'function') {
      console.log('[initSocketWithDiagnostics] reutilizando socket existente', window.socket);
    } else {
      window.socket = io(socketUrl, opts);
    }
  } catch (err) {
    console.error('[initSocketWithDiagnostics] error creando socket:', err);
    return null;
  }

  // register handlers if not already
  if (typeof registerSocketHandlers === 'function') registerSocketHandlers(window.socket);

  // extra debug handlers
  window.socket.on('connect', () => {
    console.log('[DIAG] socket connected id=', window.socket.id, ' transport=', window.socket.io?.engine?.transport?.name);
  });

  window.socket.on('connect_error', (err) => {
    console.error('[DIAG] connect_error (full object):', err);
    try {
      // socket.io err puede tener data/message/description/transport
      console.error('[DIAG] connect_error message:', err && err.message);
      console.error('[DIAG] connect_error transport:', err && err.transport);
      console.error('[DIAG] connect_error description:', err && err.description);
      console.error('[DIAG] connect_error data:', err && err.data);
      // si existe body text dentro err.data, mostrarlo truncado
      if (err && err.data && typeof err.data === 'string') {
        console.error('[DIAG] connect_error data text (truncated 2000):', err.data.length>2000 ? err.data.slice(0,2000)+'...' : err.data);
      }
    } catch(e) {
      console.warn('[DIAG] error logging connect_error details', e);
    }
  });

  window.socket.on('disconnect', (reason) => {
    console.log('[DIAG] socket disconnect reason=', reason);
  });

  // también loguear transport errors desde engine.io (si disponible)
  try {
    const eng = window.socket.io && window.socket.io.engine;
    if (eng) {
      eng.on('packet', (p) => { /* opcional: console.log('[engine] packet', p); */ });
      eng.on('drain', () => console.log('[engine] drain'));
      eng.on('upgrade', () => console.log('[engine] transport upgraded to', eng.transport.name));
      eng.on('close', () => console.log('[engine] engine closed'));
      eng.on('error', (e) => console.warn('[engine] error', e));
    }
  } catch(e){ /* ignore */ }

  return window.socket;
}

// Reemplaza llamadas a initSocket() por initSocketWithDiagnostics() en tu arranque
document.addEventListener('DOMContentLoaded', () => {
  // llama a la versión diagnóstica
  initSocketWithDiagnostics().then(s => {
    if (!s) console.warn('[startup] socket no inicializado');
    else console.log('[startup] socket inicializado (diagnostic)');
    if (typeof startChat === 'function') startChat();
  }).catch(err => {
    console.error('[startup] initSocketWithDiagnostics fallo', err);
    if (typeof startChat === 'function') startChat();
  });
});


const CHAT_CONFIG = {
  SOCKET_PATH: '/socket.io',

  ENDPOINTS: {
    // función que construye la URL HTTP real para enviar mensajes a un recipient_id
    sendMessageHttp: (recipientId) => `/chat/${recipientId}`,
    // no hay endpoint separado de upload en el backend que pegaste:
    // si en el futuro creas uno, añádelo aquí.
  },
  // tamaño máximo para enviar como dataURL/base64 desde cliente
  MAX_BASE64_SIZE: 200_000
};

function getCsrfToken() {
  const m = document.querySelector('meta[name="csrf-token"]');
  if (m) return m.content;
  const inp = document.querySelector('input[name="csrf_token"]');
  return inp ? inp.value : null;
}

function safeFetch(url, options = {}) {
  // añade CSRF cuando haya token
  const token = getCsrfToken();
  const headers = options.headers || {};
  if (token && !headers['X-CSRFToken'] && !headers['X-CSRF-Token']) {
    headers['X-CSRFToken'] = token;
  }
  return fetch(url, {...options, headers});
}

function formatTime(ts) {
  const d = new Date(ts);
  return d.toLocaleString(); // puedes personalizar
}

/* ==========================
   ROOM MANAGEMENT
   ========================== */
async function createRoom(data) {
  // data: {participant_ids: [...], title: '...'} por ejemplo
  const res = await safeFetch(CHAT_CONFIG.ENDPOINTS.createRoom, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error('Error creando room');
  return await res.json(); // devuelve {room_id, ...}
}

function joinRoom(roomId) {
  if (!socket) initSocket();
  socket.emit('join', {room: roomId});
  // también puedes actualizar UI (marcar room activo)
}
/* -------------------------
   UTIL: obtener contenedor
   ------------------------- */
function getChatContainer() {
  // Preferencias: #chat-messages -> #chat -> #chat-box
  return document.querySelector('#chat-messages') ||
         document.querySelector('#chat') ||
         document.querySelector('#chat-box') ||
         document.body;
}

/* =========================
   TEMPORAL MESSAGE (display)
   ========================= */

/**
 * displayTempMessage(options)
 * - options: { text, filePreviewHTML, filename, isFile }
 * - devuelve tempId (string) y crea un elemento .chat-message.temporary
 */
/* =========================
   TEMPORAL MESSAGE (display) - CON BOTONES
   ========================= */

function displayTempMessage({ text = '', filePreviewHTML = '', filename = '', isFile = false, isOwner = true } = {}) {
  const container = getChatContainer();
  if (!container) {
    console.warn('[displayTempMessage] contenedor chat no encontrado');
    return null;
  }

  const tempId = `temp_${Date.now()}_${Math.floor(Math.random()*9000)+1000}`;
  const wrapper = document.createElement('div');

  // Mantener las clases que usa tu CSS: .chat-message .my-message o .other-message
  wrapper.className = isOwner ? 'chat-message my-message temporary' : 'chat-message other-message temporary';
  wrapper.dataset.messageId = tempId;

  // Opciones (icono de tres puntos). El popup de opciones (mazo-options-popup) usa delegación
  const optionsHtml = isOwner ? `
    <div class="message-options" aria-hidden="true">
      <span class="options-icon" title="Opciones">⋮</span>
    </div>
  ` : '';

  let innerHTML = `<div class="message-content">`;

  // si es archivo, mostrar preview simple
  if (isFile && filePreviewHTML) {
    innerHTML += `<div class="msg-file">${filePreviewHTML}</div>`;
  } else {
    innerHTML += `<p class="message-text">${escapeHtml(text || '')}</p>`;
  }

  // Añadir opciones y un badge "Enviando..."
  innerHTML += `${optionsHtml}<div class="msg-meta"><span class="sending-badge">Enviando…</span></div>`;
  innerHTML += `</div>`; // .message-content

  wrapper.innerHTML = innerHTML;

  // Insertar en el DOM
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;

  // Guardar en mapping temporal
  window._mazo_temp_messages = window._mazo_temp_messages || {};
  window._mazo_temp_messages[tempId] = {
    el: wrapper,
    createdAt: Date.now(),
    text,
    filename,
    replaced: false,
    isOwner
  };

  console.log('[displayTempMessage] creado tempId=', tempId, 'text=', text, 'filename=', filename);
  return tempId;
}

function replaceTempWithReal(tempId, realData = {}) {
  if (!tempId || !window._mazo_temp_messages || !window._mazo_temp_messages[tempId]) {
    console.warn('[replaceTempWithReal] temp no encontrado:', tempId);
    return null;
  }

  try {
    const entry = window._mazo_temp_messages[tempId];
    const el = entry.el;
    if (!el) {
      delete window._mazo_temp_messages[tempId];
      return null;
    }
    if (entry.replaced) {
      console.log('[replaceTempWithReal] temp ya reemplazado', tempId);
      return el;
    }

    const realId = realData.message_id || realData.id || (realData.message && realData.message.id) || null;
    const realText = (realData.message || realData.text || realData.content) ?? entry.text;
    const fileUrl = realData.file_url || realData.stream_url || (realData.file && realData.file.url) || '';
    const thumb = realData.thumbnail_url || realData.thumbnail || '';

    // actualizar dataset y clases
    if (realId) el.dataset.messageId = realId;
    el.classList.remove('temporary');
    entry.replaced = true;

    // conservar si era owner para clases/estilo
    const isOwner = entry.isOwner;
    if (isOwner) {
      el.classList.remove('other-message');
      if (!el.classList.contains('my-message')) el.classList.add('my-message');
    } else {
      el.classList.remove('my-message');
      if (!el.classList.contains('other-message')) el.classList.add('other-message');
    }

    // Actualizar contenido
    const contentEl = el.querySelector('.message-content') || el;
    // limpiar para re-render
    contentEl.innerHTML = '';

    // Recrear texto o file preview con la misma estructura que los mensajes definitivos
    if (fileUrl) {
      const fn = realData.file_name || entry.filename || fileUrl.split('/').pop() || '';
      const ext = (fn.split('.').pop() || '').toLowerCase();
      if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
        contentEl.innerHTML = `<img src="${fileUrl}" class="chat-thumbnail" alt="${escapeHtml(fn)}">`;
      } else if (['mp4','webm','mov','avi','mpg'].includes(ext)) {
        const thumbHTML = thumb ? `<img src="${thumb}" class="chat-thumbnail">` : `<div class="video-placeholder">Vídeo</div>`;
        contentEl.innerHTML = `${thumbHTML}<div class="video-play">▶</div>`;
      } else {
        contentEl.innerHTML = `<div class="file-thumbnail"><i class="fas fa-file file-icon"></i><a href="${fileUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(fn || fileUrl)}</a></div>`;
      }
    } else {
      contentEl.innerHTML = `<p class="message-text">${escapeHtml(realText || '')}</p>`;
    }

    // Restaurar/añadir el icono de opciones si eres owner
    if (isOwner) {
      // si no existe, añadirlo (para mensajes temporales siempre lo hemos añadido)
      if (!contentEl.querySelector('.message-options')) {
        const optDiv = document.createElement('div');
        optDiv.className = 'message-options';
        optDiv.innerHTML = `<span class="options-icon" title="Opciones">⋮</span>`;
        // colocarlo al final (o ajustar posición según tu CSS)
        contentEl.appendChild(optDiv);
      }
    } else {
      // asegurarse de no mostrar opciones en mensajes de otros
      const opt = contentEl.querySelector('.message-options');
      if (opt) opt.remove();
    }

    // eliminar badge "Enviando"
    const badge = el.querySelector('.sending-badge');
    if (badge) badge.remove();

    // scroll a fondo
    const container = getChatContainer();
    if (container) container.scrollTop = container.scrollHeight;

    console.log('[replaceTempWithReal] temp reemplazado', tempId, '-> realId=', realId, 'fileUrl=', fileUrl);

    // limpiar mapping después de 60s
    setTimeout(() => { try { delete window._mazo_temp_messages[tempId]; } catch(e){} }, 60_000);
    return el;
  } catch (err) {
    console.error('[replaceTempWithReal] error', err);
    return null;
  }
}

/**
 * replaceTempWithReal(tempId, realData)
 * - realData: lo que obtienes del servidor (ack o payload): { message_id, file_url, thumbnail_url, message, timestamp, ... }
 */
function replaceTempWithReal(tempId, realData = {}) {
  if (!tempId || !window._mazo_temp_messages || !window._mazo_temp_messages[tempId]) {
    console.warn('[replaceTempWithReal] temp no encontrado:', tempId);
    return null;
  }

  try {
    const entry = window._mazo_temp_messages[tempId];
    const el = entry.el;
    if (!el) {
      delete window._mazo_temp_messages[tempId];
      return null;
    }

    if (entry.replaced) {
      console.log('[replaceTempWithReal] temp ya reemplazado', tempId);
      return el;
    }

    const realId = realData.message_id || realData.id || (realData.message && realData.message.id) || null;
    const realText = (realData.message || realData.text || realData.content) ?? entry.text;
    const fileUrl = realData.file_url || realData.stream_url || (realData.file && realData.file.url) || '';
    const thumb = realData.thumbnail_url || realData.thumbnail || '';

    // Actualizar dataset y clases
    if (realId) el.dataset.messageId = realId;
    el.classList.remove('temporary');
    entry.replaced = true;

    // Reemplazar contenido
    const msgTextEl = el.querySelector('.message-text') || el.querySelector('.msg-text');
    if (msgTextEl) {
      msgTextEl.textContent = realText || '';
    } else {
      // crear si no existe (p.ej. archivo -> render file)
      const contentEl = el.querySelector('.message-content') || el;
      contentEl.innerHTML = '';
      if (fileUrl) {
        // crear preview sencillo: imagen/video/link según extensión
        const fn = fileUrl.split('/').pop() || '';
        const ext = (fn.split('.').pop() || '').toLowerCase();
        if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
          contentEl.innerHTML = `<img src="${fileUrl}" class="chat-thumbnail" alt="${escapeHtml(fn)}">`;
        } else if (['mp4','webm','mov','avi','mpg'].includes(ext)) {
          const thumbHTML = thumb ? `<img src="${thumb}" class="chat-thumbnail">` : `<div class="video-placeholder">Vídeo</div>`;
          contentEl.innerHTML = `${thumbHTML}<div class="video-play">▶</div>`;
        } else {
          contentEl.innerHTML = `<a href="${fileUrl}" target="_blank" rel="noopener noreferrer">${escapeHtml(fn || fileUrl)}</a>`;
        }
      } else {
        contentEl.innerHTML = `<p class="message-text">${escapeHtml(realText || '')}</p>`;
      }
    }

    // eliminar badge "Enviando"
    const badge = el.querySelector('.sending-badge');
    if (badge) badge.remove();

    // scroll a fondo
    const container = getChatContainer();
    if (container) container.scrollTop = container.scrollHeight;

    console.log('[replaceTempWithReal] temp reemplazado', tempId, '-> realId=', realId, 'fileUrl=', fileUrl);
    // borrar del mapping después de un rato para evitar memory leaks
    setTimeout(() => { try { delete window._mazo_temp_messages[tempId]; } catch(e){} }, 60_000);
    return el;
  } catch (err) {
    console.error('[replaceTempWithReal] error', err);
    return null;
  }
}

/* =========================
   Ajustes en el envío
   ========================= */

/**
 * emitSendMessageWithAck wrapper (ya la tienes),
 * pero aquí añadimos la lógica que crea el temporal antes de emitir
 * y reemplaza cuando llega ack.
 */
const _orig_emitSendMessageWithAck_v2 = (typeof emitSendMessageWithAck === 'function') ? emitSendMessageWithAck : null;
if (_orig_emitSendMessageWithAck_v2) {
  emitSendMessageWithAck = async function(payload, timeoutMs = 8000) {
    // Si payload contiene __mazo_tempId ya creado, no creamos otro
    let tempId = payload && payload.__mazo_tempId ? payload.__mazo_tempId : null;

    // Si no hay tempId, crear temporal en UI (texto o archivo)
    if (!tempId) {
      const text = payload && payload.message ? payload.message : '';
      let isFile = false;
      let previewHTML = '';
      if (payload && payload.file) {
        // si payload.file parece ser dataURL o URL
        isFile = true;
        // No hacemos preview complejo aquí; solo un placeholder
        previewHTML = `<span class="file-name">${escapeHtml(payload.filename || (typeof payload.file === 'string' ? payload.file.split('/').pop() : 'Archivo'))}</span>`;
      }
      tempId = displayTempMessage({ text, filePreviewHTML: previewHTML, filename: payload.filename, isFile });
      // marcarlo en el payload para que no se doble creen
      try { payload.__mazo_tempId = tempId; } catch(e){}
    }

    console.log('[emitSendMessageWithAck wrapper] payload (con tempId):', payload, 'timeoutMs=', timeoutMs);

    // llamar al original (emit)
    let ack = null;
    try {
      ack = await _orig_emitSendMessageWithAck_v2(payload, timeoutMs);
      console.log('[emitSendMessageWithAck wrapper] ack recibido:', ack);
    } catch (err) {
      console.error('[emitSendMessageWithAck wrapper] error emit:', err);
      // no lanzamos error final para que el temporal quede visible
      ack = null;
    }

    // Si ack devuelve info útil (message_id, file_url...), reemplazamos el temp
    if (ack && (ack.message_id || ack.file_url || ack.ok)) {
      // ack puede venir como objeto simple o {ok:true, message_id:...}
      // pasamos ack directamente a replace
      try {
        replaceTempWithReal(tempId, ack);
      } catch (e) { console.warn('replaceTempWithReal fallo con ack', e); }
    } else {
      // si no hay ack, dejamos temporal (ya se mostró). Podríamos marcar como "pendiente".
      console.warn('[emitSendMessageWithAck wrapper] no se recibió ack válido, mensaje temporal permanece:', tempId);
    }

    return ack;
  };
}

/* =========================
   Modificar sendMessageSocket y wrappers
   ========================= */

// Reemplazar sendMessageSocket por esta versión (usa wrapper emitSendMessageWithAck actualizado)
async function sendMessageSocket({ recipientUsername, text = '', file = null, filename = null }) {
  if (!recipientUsername) throw new Error('recipientUsername required for socket send');

  const payload = { recipient: recipientUsername, message: text || '' };
  if (file) payload.file = file;
  if (filename) payload.filename = filename;

  console.log('[sendMessageSocket] emitiendo con temp preview payload:', payload);

  // emitSendMessageWithAck (wrapper) se encargará de crear el temporal y reemplazarlo al recibir ack
  try {
    const ack = await emitSendMessageWithAck(payload, 8000);
    console.log('[sendMessageSocket] ack final:', ack);
    return ack;
  } catch (err) {
    console.error('[sendMessageSocket] error final:', err);
    throw err;
  }
}

/* =========================
   Evitar duplicados al recibir por socket
   ========================= */

/**
 * Ajuste en handleSocketNewMessage:
 * - Si recibimos un mensaje cuyo id ya está presente -> ignorar (o actualizar)
 * - Si recibimos un mensaje que coincide textualmente con un temporal que no fue reemplazado -> reemplazar
 *
 * Recomendación: si tu server devuelve ACK (message_id) en respuesta al emit, replaceTempWithReal() ya habrá actualizado.
 * Este handler intenta deduplicar:
 */
function _handleSocketNewMessageDedup({ message: payload, room_id = null } = {}) {
  const p = payload || {};
  console.log('[handleSocketNewMessage] raw payload:', p, 'room:', room_id);

  // identificar id real
  const realId = p.message_id || p.id || p.msg_id || null;
  const text = (p.message !== undefined) ? p.message : (p.content || p.text || '');
  const fileUrl = p.file_url || '';

  // 1) si ya existe un elemento con data-message-id == realId -> actualizar y salir
  if (realId) {
    const exists = document.querySelector(`[data-message-id="${realId}"]`);
    if (exists) {
      console.log('[handleSocketNewMessage] mensaje ya existe en DOM, actualizando si hace falta', realId);
      // aquí podrías actualizar campos (por simplicidad, no re-renderizamos entero)
      const msgTextEl = exists.querySelector('.message-text');
      if (msgTextEl && text) msgTextEl.textContent = text;
      return;
    }
  }

  // 2) intentar emparejar con temporales no reemplazados por texto+archivo
  const temps = document.querySelectorAll('.chat-message.temporary');
  for (const t of temps) {
    const mid = t.dataset?.messageId;
    const tmpEntry = (window._mazo_temp_messages && window._mazo_temp_messages[mid]) || null;
    if (!tmpEntry) continue;
    // si coincide archivo (filename or file url) o texto exacto, considerarlo la misma
    const tmpText = tmpEntry.text || '';
    const tmpFn = tmpEntry.filename || '';
    const maybeMatchByText = tmpText && text && tmpText.trim() === text.trim();
    const maybeMatchByFn = (tmpFn && p.file_name && tmpFn === p.file_name) || (tmpFn && fileUrl && fileUrl.includes(tmpFn));
    if (maybeMatchByText || maybeMatchByFn) {
      console.log('[handleSocketNewMessage] coincidencia temporal encontrada, reemplazando', mid, '->', realId);
      replaceTempWithReal(mid, p);
      return;
    }
  }

  // 3) si no hay coincidencias temporales -> render normal (texto o archivo)
  // Reusamos tu lógica previa para render
  // Normalizar autor
  const author = {
    username: p.username || p.author?.username || p.sender || 'unknown',
    avatar: p.avatar || p.author?.avatar || p.profile_pic || '/static/profile_pics/default.jpg'
  };

  const id = realId;
  const created_at = p.timestamp || p.created_at || new Date().toISOString();

  if (fileUrl && fileUrl !== '') {
    // construir messageObj similar al tuyo
    const filename = p.file_name || (fileUrl.split('/').pop() || '');
    const ext = (filename.split('.').pop() || '').toLowerCase();
    let mime = '';
    if (['jpg','jpeg','png','gif','webp'].includes(ext)) mime = 'image/' + ext;
    if (['mp4','webm','mov','avi','mpg'].includes(ext)) mime = 'video/' + ext;

    const messageObj = {
      id,
      author,
      file: { url: fileUrl, filename, mime },
      created_at,
      is_owner: (author.username === (document.querySelector('#chat')?.dataset?.myUsername))
    };
    if (p.message) messageObj.text = p.message;
    if (p.thumbnail_url) messageObj.file.thumbnail = p.thumbnail_url;

    if (typeof renderFileMessage === 'function') {
      renderFileMessage(getChatContainer(), messageObj);
    } else {
      console.warn('renderFileMessage no definido', messageObj);
    }
    return;
  }

  // texto simple
  const messageObj = {
    id,
    author,
    text,
    created_at,
    is_owner: (author.username === (document.querySelector('#chat')?.dataset?.myUsername))
  };
  if (typeof renderTextMessage === 'function') {
    renderTextMessage(getChatContainer(), messageObj);
  } else {
    console.warn('renderTextMessage no definido', messageObj);
  }
}

/* -----------------------------
   SENDING MESSAGES (adaptado)
   ----------------------------- */


const UPLOAD_ENDPOINT = '/upload_file'; // tu endpoint en Flask
// Asume que CHAT_CONFIG.ENDPOINTS.sendMessageHttp(recipientId) existe y CHAT_CONFIG.MAX_BASE64_SIZE

// Emite por socket con ACK y timeout
function emitSendMessageWithAck(payload, timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    if (!window.socket || typeof window.socket.emit !== 'function') {
      return reject(new Error('socket_not_initialized'));
    }
    console.log('[emit] send_message payload:', payload);
    let called = false;
    try {
      window.socket.emit('send_message', payload, (ack) => {
        called = true;
        console.log('[emit] ACK recibido:', ack);
        resolve(ack);
      });
    } catch (err) {
      return reject(err);
    }
    // timeout si el server no responde con callback
    setTimeout(() => {
      if (!called) {
        console.warn('[emit] ACK timeout, resolviendo sin ack (server puede no usar ack).');
        resolve(null); // no fallamos; el servidor puede no enviar ack
      }
    }, timeoutMs);
  });
}

// Envía el mensaje por socket (payload que espera tu backend)
async function sendMessageSocket({ recipientUsername, text = '', file = null, filename = null }) {
  if (!recipientUsername) throw new Error('recipientUsername required for socket send');
  const payload = { recipient: recipientUsername, message: text || '' };
  if (file) payload.file = file;
  if (filename) payload.filename = filename;
  // si quieres, puedes esperar al ACK:
  return await emitSendMessageWithAck(payload);
}

// Convierte File -> data:<mime>;base64,...
function fileToDataURL(file) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result); // "data:...;base64,..."
    fr.onerror = (e) => reject(e);
    fr.readAsDataURL(file);
  });
}

// Sube archivo grande al servidor vía FormData -> /upload_file
async function uploadFileToServer(file, opts = {}) {
  try {
    const form = new FormData();
    form.append('file', file);
    // si quieres especificar carpeta: form.append('folder', 'static/chat_uploads')
    if (opts.filename) form.append('filename', opts.filename);
    if (opts.folder) form.append('folder', opts.folder);

    console.log('[uploadFileToServer] subiendo archivo:', file.name, file.size);
    const res = await fetch(UPLOAD_ENDPOINT, {
      method: 'POST',
      body: form,
      headers: {} // no Content-Type (browser lo pone)
    });
    if (!res.ok) {
      const txt = await res.text().catch(()=>null);
      console.error('[uploadFileToServer] respuesta no ok', res.status, txt);
      throw new Error('upload_failed:' + res.status);
    }
    const j = await res.json().catch(()=>null);
    console.log('[uploadFileToServer] respuesta:', j);
    return j;
  } catch (err) {
    console.error('[uploadFileToServer] error', err);
    throw err;
  }
}

// Fallback: enviar por HTTP POST a /chat/<recipientId> (tu endpoint send_message_http)
async function sendTextMessageHttp(recipientId, text) {
  console.log('[sendTextMessageHttp] recipientId:', recipientId, 'text:', text);
  try {
    const res = await sendMessageHttp(recipientId, { text, files: [] });
    console.log('[sendTextMessageHttp] respuesta HTTP:', res);
    return res;
  } catch (err) {
    console.error('[sendTextMessageHttp] error:', err);
    throw err;
  }
}

async function sendFileMessageHttp(recipientId, fileOrFiles, text = '') {
  console.log('[sendFileMessageHttp] recipientId:', recipientId, 'files:', fileOrFiles, 'text:', text);
  try {
    // si fileOrFiles es un array o File
    const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
    const res = await sendMessageHttp(recipientId, { text, files });
    console.log('[sendFileMessageHttp] respuesta HTTP:', res);
    return res;
  } catch (err) {
    console.error('[sendFileMessageHttp] error:', err);
    throw err;
  }
}

/**
 * Wrappers genéricos que la UI puede llamar:
 * - Si pasas recipient as number -> se usa HTTP alias
 * - Si pasas recipient as string -> se usa socket (username)
 */
async function sendTextMessage(recipientIdentifier, text) {
  console.log('[sendTextMessage] recipientIdentifier:', recipientIdentifier, 'text:', text);
  try {
    if (typeof recipientIdentifier === 'number' || /^\d+$/.test(String(recipientIdentifier))) {
      // numeric id -> HTTP endpoint
      return await sendTextMessageHttp(Number(recipientIdentifier), text);
    } else {
      // assume username -> socket
      return await sendMessageSocket({ recipientUsername: String(recipientIdentifier), text });
    }
  } catch (err) {
    console.error('[sendTextMessage] fallo enviando:', err);
    throw err;
  }
}

async function sendFileMessage(recipientIdentifier, file, text = '') {
  console.log('[sendFileMessage] recipientIdentifier:', recipientIdentifier, 'file:', file && file.name ? file.name : file, 'text:', text);
  try {
    if (typeof recipientIdentifier === 'number' || /^\d+$/.test(String(recipientIdentifier))) {
      // send via HTTP (recipient id required)
      return await sendFileMessageHttp(Number(recipientIdentifier), file, text);
    } else {
      // recipient is username -> use socket path (file could be File object OR a URL/string)
      // If it's a File object, use existing logic: small -> dataURL via socket, large -> upload then notify
      if (file instanceof File) {
        if (file.size <= (CHAT_CONFIG?.MAX_BASE64_SIZE || 200000)) {
          const durl = await fileToDataURL(file);
          return await sendMessageSocket({ recipientUsername: String(recipientIdentifier), text, file: durl, filename: file.name });
        } else {
          // upload then notify via socket
          const uploadResp = await uploadFileToServer(file, { filename: file.name });
          const streamUrl = uploadResp && (uploadResp.stream_url || uploadResp.file_path || uploadResp.file_url);
          return await sendMessageSocket({ recipientUsername: String(recipientIdentifier), text, file: streamUrl, filename: file.name });
        }
      } else {
        // file is probably a URL (string) or already-streamable
        return await sendMessageSocket({ recipientUsername: String(recipientIdentifier), text, file: file, filename: typeof file === 'string' ? file.split('/').pop() : undefined });
      }
    }
  } catch (err) {
    console.error('[sendFileMessage] fallo enviando:', err);
    throw err;
  }
}

/* ====== Añadir más logs a las funciones de envío (si no están) ====== */

// Asegurarnos de loguear éxito/ack en rutas críticas:
const _orig_emitSendMessageWithAck = emitSendMessageWithAck;
emitSendMessageWithAck = async function(payload, timeoutMs = 8000) {
  console.log('[emitSendMessageWithAck] enviando payload:', payload);
  try {
    const ack = await _orig_emitSendMessageWithAck(payload, timeoutMs);
    console.log('[emitSendMessageWithAck] ack/result:', ack);
    return ack;
  } catch (err) {
    console.error('[emitSendMessageWithAck] error:', err);
    throw err;
  }
};

// si quieres logs para el envío HTTP (ya los tenemos en sendTextMessageHttp/sendFileMessageHttp)
// pero añadir una copia para seguridad:
const _orig_sendMessageHttp = typeof sendMessageHttp === 'function' ? sendMessageHttp : null;
if (_orig_sendMessageHttp) {
  sendMessageHttp = async function(recipientId, opts) {
    console.log('[sendMessageHttp wrapper] recipientId:', recipientId, 'opts:', opts);
    try {
      const res = await _orig_sendMessageHttp(recipientId, opts);
      console.log('[sendMessageHttp wrapper] respuesta:', res);
      return res;
    } catch (err) {
      console.error('[sendMessageHttp wrapper] error:', err);
      throw err;
    }
  };
}

function attachMessageFormHandler() {
  const form = document.querySelector('#message-form');
  if (!form) { console.warn('attachMessageFormHandler: #message-form no encontrado'); return; }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const textarea = document.querySelector('#message');
    const messageText = textarea ? textarea.value.trim() : '';
    const fileInput = document.querySelector('#file-input');
    const files = fileInput ? Array.from(fileInput.files) : [];
    // detect recipients from DOM
    const chatEl = document.querySelector('#chat');
    const recipientUsername = (chatEl && chatEl.dataset && chatEl.dataset.recipientUsername) || document.querySelector('#chat-recipient-username')?.value;
    const recipientId = (chatEl && chatEl.dataset && chatEl.dataset.recipientId) || document.querySelector('#chat-recipient-id')?.value;

    console.log('[UI] submit -> text:', messageText, 'files:', files.map(f=>f.name), 'recipientUsername:', recipientUsername, 'recipientId:', recipientId);

    try {
      // Validación mínima
      if (!recipientUsername && !recipientId) throw new Error('No recipient info found');

      // Si no hay archivos, prefer socket para texto en tiempo real
      if (files.length === 0) {
        if (window.socket && window.socket.connected && recipientUsername) {
          await sendMessageSocket({ recipientUsername, text: messageText });
        } else {
          // fallback HTTP (usa recipientId)
          await sendMessageHttp(recipientId, { text: messageText, files: [] });
        }
      } else {
        // Hay archivos: decidir por tamaño
        // Si todos son pequeños -> enviarlos por socket uno a uno como dataURL
        const allSmall = files.every(f => f.size <= CHAT_CONFIG.MAX_BASE64_SIZE);
        if (allSmall && window.socket && window.socket.connected && recipientUsername) {
          // si hay texto + varios archivos: enviar el texto como un mensaje y luego archivos como mensajes separados
          if (messageText) {
            await sendMessageSocket({ recipientUsername, text: messageText });
          }
          for (const f of files) {
            const durl = await fileToDataURL(f);
            await sendMessageSocket({ recipientUsername, file: durl, filename: f.name });
          }
        } else {
          // Subir via /upload_file (primero) usando FormData y luego notificar por socket
          // Si tu backend espera /chat/<id> con files en formdata, podrías enviar ahí; aquí usamos /upload_file para obtener stream_url
          for (const f of files) {
            try {
              const uploadResp = await uploadFileToServer(f, { filename: f.name });
              // uploadResp expected: { success: true, file_path, stream_url, thumbnail_url }
              const streamUrl = uploadResp && (uploadResp.stream_url || uploadResp.file_path || uploadResp.file_url);
              // enviar mensaje por socket con file=streamUrl (o file_path si prefieres)
              if (window.socket && window.socket.connected && recipientUsername) {
                // incluir texto sólo en el first file (si había texto)
                const textToSend = messageText || '';
                await sendMessageSocket({ recipientUsername, text: textToSend, file: streamUrl, filename: f.name });
                // clear text after sending it once
                messageText = '';
              } else {
                // fallback: enviar por HTTP /chat/<recipientId> usando formdata
                await sendMessageHttp(recipientId, { text: messageText, files: [f] });
                messageText = '';
              }
            } catch (err) {
              console.error('Error subiendo archivo', err);
              alert('Error subiendo archivo: ' + (err.message || err));
            }
          } // end for files
        }
      } // end else files

      // limpiar UI al final
      if (textarea) textarea.value = '';
      if (fileInput) fileInput.value = '';
      const preview = document.querySelector('#file-preview-container');
      if (preview) preview.innerHTML = '';
    } catch (err) {
      console.error('Error enviando mensaje:', err);
      alert('Error enviando mensaje: ' + (err.message || err));
    }
  });
}

// Inicializa handler al cargar (si attach ya no está registrado)
document.addEventListener('DOMContentLoaded', () => {
  attachMessageFormHandler();
});

/* ================================
   Small popup menu (Editar / Borrar)
   Insertar ANTES de las funciones de editar/borrar
   ================================ */

/* ====================================================
   Popup de opciones (Editar / Borrar) + Edit / Delete
   Reemplaza la versión anterior completa por este bloque
   ==================================================== */

(function () {
  // Crear un único popup reutilizable
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

    // Arrow
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

    // Opciones
    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'mazo-popup-btn mazo-popup-edit';
    btnEdit.textContent = 'Editar';
    btnEdit.style.display = 'block';
    btnEdit.style.width = '100%';
    btnEdit.style.padding = '8px 10px';
    btnEdit.style.background = 'transparent';
    btnEdit.style.border = 'none';
    btnEdit.style.textAlign = 'left';
    btnEdit.style.cursor = 'pointer';
    btnEdit.style.borderRadius = '6px';

    const btnDelete = document.createElement('button');
    btnDelete.type = 'button';
    btnDelete.className = 'mazo-popup-btn mazo-popup-delete';
    btnDelete.textContent = 'Borrar';
    btnDelete.style.display = 'block';
    btnDelete.style.width = '100%';
    btnDelete.style.padding = '8px 10px';
    btnDelete.style.background = 'transparent';
    btnDelete.style.border = 'none';
    btnDelete.style.textAlign = 'left';
    btnDelete.style.cursor = 'pointer';
    btnDelete.style.color = '#d33';
    btnDelete.style.borderRadius = '6px';

    // hover styles
    [btnEdit, btnDelete].forEach(b => {
      b.addEventListener('mouseenter', () => b.style.background = 'rgba(0,0,0,0.04)');
      b.addEventListener('mouseleave', () => b.style.background = 'transparent');
    });

    popup.appendChild(btnEdit);
    popup.appendChild(btnDelete);

    document.body.appendChild(popup);

    return popup;
  }

  // Estado actual (messageId del popup abierto)
  let currentTarget = null; // { buttonEl, messageId }

  function openPopup(buttonEl, messageId) {
    const p = createPopup();
    currentTarget = { buttonEl, messageId };

    // Posicionar popup junto al botón (preferiblemente a la derecha)
    const rect = buttonEl.getBoundingClientRect();

    // calcular posición preferida: a la derecha del botón, alineado verticalmente
    const preferLeft = rect.left + rect.width + 8 + p.offsetWidth > window.innerWidth;
    let top = window.scrollY + rect.top + (rect.height / 2) - 20; // ajustar para centrar
    let left;

    if (preferLeft) {
      // posicionar a la izquierda del botón
      left = window.scrollX + rect.left - p.offsetWidth - 8;
    } else {
      left = window.scrollX + rect.left + rect.width + 8;
    }

    // Asegurar que no salga por abajo o arriba de la ventana
    const maxTop = window.scrollY + window.innerHeight - p.offsetHeight - 12;
    if (top > maxTop) top = maxTop;
    if (top < 12) top = 12;

    p.style.left = `${left}px`;
    p.style.top = `${top}px`;
    p.style.display = 'block';
    // Guardar messageId en dataset del popup para accesos desde fuera
    p.dataset.currentMessageId = messageId || '';
    // focus al primer botón
    const firstBtn = p.querySelector('button');
    if (firstBtn) firstBtn.focus();

    // añadir atributo data para el arrow posicionamiento
    const arrow = p.querySelector('.mazo-popup-arrow');
    if (arrow) {
      // colocar arrow cerca del botón (simple centering para apariencia)
      arrow.style.left = preferLeft ? `${p.offsetWidth - 18}px` : `8px`;
      arrow.style.top = '-6px';
    }
  }

  function closePopup() {
    const p = createPopup();
    // limpiar id vinculado
    try { delete p.dataset.currentMessageId; } catch (e) { p.removeAttribute('data-current-message-id'); }
    p.style.display = 'none';
    currentTarget = null;
  }

  // Delegación: manejar clicks en .options-icon
  document.addEventListener('click', (e) => {
    const icon = e.target.closest('.options-icon, .options-icon *');
    if (icon) {
      // Encontrar el message container
      const btn = icon.closest('.options-icon') || e.target;
      // subir hasta .chat-message para detectar id
      const msgEl = btn.closest('.chat-message');
      if (!msgEl) {
        console.warn('No se encontró elemento .chat-message padre.');
        return;
      }
      const messageId = msgEl.dataset?.messageId || msgEl.getAttribute('data-message-id');
      // abrir/alternar popup
      const p = createPopup();
      // Si ya está abierto para el mismo messageId -> cerrar
      if (currentTarget && currentTarget.messageId === messageId) {
        closePopup();
        return;
      }
      openPopup(btn, messageId);
      e.stopPropagation();
      return;
    }

    // Si hiciste click fuera del popup -> cerrarlo
    const popupEl = document.getElementById(popupId);
    if (popupEl && popupEl.style.display === 'block') {
      if (!e.target.closest('#' + popupId)) {
        closePopup();
      }
    }
  });

  // Tecla ESC para cerrar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closePopup();
  });

  // Manejar acciones de Edit / Delete (versión robusta)
  document.body.addEventListener('click', (e) => {
    const p = createPopup();
    if (p.style.display !== 'block') return;

    const editBtn = e.target.closest('.mazo-popup-edit');
    const deleteBtn = e.target.closest('.mazo-popup-delete');

    if (!editBtn && !deleteBtn) return;

    // obtener messageId actual (primero desde currentTarget, luego desde dataset del popup)
    const messageId = (currentTarget && currentTarget.messageId) || p.dataset?.currentMessageId || null;
    if (!messageId) {
      console.warn('Mazopopup: no messageId disponible al pulsar Edit/Delete');
      closePopup();
      return;
    }

    console.log('Mazopopup click action:', editBtn ? 'edit' : 'delete', 'messageId=', messageId);

    if (editBtn) {
      // preferir edición inline siempre
      try {
        openInlineEditorForMessage(messageId);
      } catch (err) {
        console.warn('openInlineEditorForMessage fallo, intentando openEditModal fallback', err);
        if (typeof openEditModal === 'function') {
          try { openEditModal(messageId); } catch(e){ console.warn('fallback openEditModal fallo', e); }
        }
      }
      // esperar un poco antes de cerrar el popup para evitar condiciones de carrera
      setTimeout(() => closePopup(), 50);
      e.stopPropagation();
      return;
    }

    if (deleteBtn) {
      try {
        if (typeof confirmAndDeleteMessage === 'function') {
          confirmAndDeleteMessage(messageId);
        } else if (typeof deleteMessage === 'function') {
          if (confirm('¿Eliminar mensaje?')) deleteMessage(messageId);
        } else {
          console.warn('No hay función confirmAndDeleteMessage ni deleteMessage definida.');
        }
      } catch (err) {
        console.warn('Error al invocar función de borrado:', err);
      }
      // cerrar popup tras pequeña espera
      setTimeout(() => closePopup(), 50);
      e.stopPropagation();
      return;
    }
  });

  // Cerrar popup al redimensionar o hacer scroll (para reposicionarlo)
  window.addEventListener('resize', () => closePopup());
  window.addEventListener('scroll', () => closePopup(), true /* capture to catch scroll inside containers */);
})();

/* ==========================
   EDIT / DELETE
   ========================== */

/**
 * Enviar petición de edición por socket (usa ACK si el backend retorna)
 * payload: { message_id, new_content }
 */
async function emitEditMessage(messageId, newContent, timeoutMs = 7000) {
  if (!messageId) throw new Error('messageId required');
  if (!window.socket || typeof window.socket.emit !== 'function') {
    throw new Error('socket_not_initialized');
  }
  console.log('[edit] emit ->', { message_id: messageId, new_content: newContent });
  return new Promise((resolve, reject) => {
    let called = false;
    try {
      window.socket.emit('edit_message', { message_id: messageId, new_content: newContent }, (ack) => {
        called = true;
        console.log('[edit] ACK:', ack);
        resolve(ack || null);
      });
    } catch (err) {
      reject(err);
    }
    setTimeout(() => {
      if (!called) {
        console.warn('[edit] ACK timeout (server may not ack) — resolve null');
        resolve(null);
      }
    }, timeoutMs);
  });
}

/**
 * Enviar petición de borrado por socket (payload: { message_id })
 */
async function emitDeleteMessage(messageId, timeoutMs = 7000) {
  if (!messageId) throw new Error('messageId required');
  if (!window.socket || typeof window.socket.emit !== 'function') {
    throw new Error('socket_not_initialized');
  }
  console.log('[delete] emit ->', { message_id: messageId });
  return new Promise((resolve, reject) => {
    let called = false;
    try {
      window.socket.emit('delete_message', { message_id: messageId }, (ack) => {
        called = true;
        console.log('[delete] ACK:', ack);
        resolve(ack || null);
      });
    } catch (err) {
      reject(err);
    }
    setTimeout(() => {
      if (!called) {
        console.warn('[delete] ACK timeout (server may not ack) — resolve null');
        resolve(null);
      }
    }, timeoutMs);
  });
}

/* ======= UI helpers ======= */

/* Inline editor: edita dentro de la burbuja sin prompts */
function openInlineEditorForMessage(messageId) {
  console.log('[openInlineEditorForMessage] entrada messageId=', messageId);
  if (!messageId) {
    // intentar leer del popup si no se pasa
    const popup = document.getElementById('mazo-options-popup');
    if (popup && popup.dataset && popup.dataset.currentMessageId) {
      messageId = popup.dataset.currentMessageId;
    }
  }
  if (!messageId) {
    console.warn('openInlineEditorForMessage: no messageId disponible');
    return;
  }

  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  console.log('[openInlineEditorForMessage] msgEl encontrado? ', !!msgEl, msgEl);
  if (!msgEl) {
    console.warn('openInlineEditorForMessage: no se encontró el elemento', messageId);
    return;
  }

  // Evitar duplicados: si ya existe editor en este mensaje, hacer focus
  if (msgEl.querySelector('.inline-edit-wrapper')) {
    msgEl.querySelector('.inline-edit-wrapper textarea')?.focus();
    return;
  }

  // localizar elemento de texto actual (varias posibilidades según tu template)
  const textEl = msgEl.querySelector('.message-text, .msg-text, .msg-body .msg-text, p.message-text');
  const currentText = textEl ? textEl.textContent.trim() : '';

  // crear wrapper del editor
  const wrap = document.createElement('div');
  wrap.className = 'inline-edit-wrapper';
  wrap.style.display = 'flex';
  wrap.style.flexDirection = 'column';
  wrap.style.gap = '8px';
  wrap.style.marginTop = '6px';

  const ta = document.createElement('textarea');
  ta.className = 'inline-edit-textarea';
  ta.value = currentText;
  ta.rows = Math.min(6, Math.max(2, (currentText.split('\n').length || 1)));
  ta.style.width = '100%';
  ta.style.boxSizing = 'border-box';
  ta.style.padding = '8px';
  ta.style.borderRadius = '8px';
  ta.style.border = '1px solid rgba(0,0,0,0.12)';
  ta.style.fontSize = '0.95rem';
  ta.style.resize = 'vertical';

  // buttons container
  const btns = document.createElement('div');
  btns.style.display = 'flex';
  btns.style.gap = '8px';
  btns.style.justifyContent = 'flex-end';

  const btnSave = document.createElement('button');
  btnSave.type = 'button';
  btnSave.className = 'inline-edit-save';
  btnSave.textContent = 'Guardar';
  btnSave.style.padding = '6px 10px';
  btnSave.style.borderRadius = '8px';
  btnSave.style.border = 'none';
  btnSave.style.cursor = 'pointer';
  btnSave.style.background = '#0b76ff';
  btnSave.style.color = '#fff';

  const btnCancel = document.createElement('button');
  btnCancel.type = 'button';
  btnCancel.className = 'inline-edit-cancel';
  btnCancel.textContent = 'Cancelar';
  btnCancel.style.padding = '6px 10px';
  btnCancel.style.borderRadius = '8px';
  btnCancel.style.border = '1px solid rgba(0,0,0,0.08)';
  btnCancel.style.cursor = 'pointer';
  btnCancel.style.background = '#fff';
  btnCancel.style.color = '#111';

  btns.appendChild(btnCancel);
  btns.appendChild(btnSave);

  wrap.appendChild(ta);
  wrap.appendChild(btns);

  // Insertar el editor en el DOM: después del texto existente, o al final de .message-content
  const contentEl = msgEl.querySelector('.message-content') || msgEl;
  if (textEl && textEl.parentElement) {
    textEl.parentElement.insertBefore(wrap, textEl.nextSibling);
    // opcional: ocultar el textEl mientras editamos para evitar duplicados
    textEl.style.display = 'none';
  } else {
    contentEl.appendChild(wrap);
  }

  // focus y seleccionar
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);

  // Helpers para cancelar/guardar
  function cleanupRestore() {
    // eliminar editor y mostrar texto original
    if (wrap && wrap.parentElement) wrap.remove();
    if (textEl) textEl.style.display = '';
  }

  async function doSave() {
    const newText = ta.value.trim();
    if (newText.length === 0) {
      if (!confirm('El mensaje quedará vacío. ¿Continuar?')) return;
    }
    // Desactivar botones para evitar múltiples clicks
    btnSave.disabled = true;
    btnCancel.disabled = true;
    btnSave.textContent = 'Guardando...';

    try {
      // llama a tu función editMessage (emit socket)
      await editMessage(messageId, newText);
      // si editMessage actualiza el DOM vía handleSocketEditedMessage, ya estará.
      // Para robustez, actualizamos localmente aquí también:
      const newTextEl = msgEl.querySelector('.message-text, .msg-text, .msg-body .msg-text, p.message-text') || textEl;
      if (newTextEl) {
        newTextEl.textContent = newText;
        newTextEl.style.display = '';
      }
      // añadir badge editado si no existe
      let editedBadge = msgEl.querySelector('.edited-badge');
      if (!editedBadge) {
        editedBadge = document.createElement('span');
        editedBadge.className = 'edited-badge';
        editedBadge.textContent = ' (editado)';
        editedBadge.style.fontSize = '0.8rem';
        editedBadge.style.opacity = '0.85';
        const head = msgEl.querySelector('.msg-head') || msgEl.querySelector('.message-content');
        if (head) head.appendChild(editedBadge);
      }
    } catch (err) {
      console.error('Error guardando edición:', err);
      alert('Error guardando edición: ' + (err.message || err));
    } finally {
      cleanupRestore();
    }
  }

  function doCancel() {
    cleanupRestore();
  }

  // Eventos
  btnSave.addEventListener('click', doSave);
  btnCancel.addEventListener('click', doCancel);

  // Atajos de teclado: Ctrl/Cmd+Enter = guardar, Esc = cancelar
  function keyHandler(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      doSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      doCancel();
    }
  }
  ta.addEventListener('keydown', keyHandler);

  // asegurarse de limpiar listeners si el popup se cierra
  const cleanupAll = () => {
    ta.removeEventListener('keydown', keyHandler);
  };

  // wrap cleanup al eliminar
  const observer = new MutationObserver(() => {
    if (!document.body.contains(wrap)) {
      cleanupAll();
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

/* Compatibilidad: openEditModal delega a inline editor */
function openEditModal(messageId) {
  openInlineEditorForMessage(messageId);
}


/**
 * confirmAndDeleteMessage(messageId)
 * - confirma y llama a deleteMessage()
 */
function confirmAndDeleteMessage(messageId) {
  if (!confirm('¿Eliminar este mensaje?')) return;
  deleteMessage(messageId);
}

/* ======= impl. editMessage / deleteMessage (wrappers que usan socket y fallback HTTP) ======= */

/**
 * editMessage(messageId, newText)
 * - llama a emitEditMessage() y maneja la respuesta
 * - si el server devuelve ok:false lo muestra en consola/alert
 */
async function editMessage(messageId, newText) {
  try {
    // Si no hay messageId intentamos obtenerlo también del popup
    if (!messageId) {
      const popup = document.getElementById('mazo-options-popup');
      if (popup && popup.dataset && popup.dataset.currentMessageId) {
        messageId = popup.dataset.currentMessageId;
      }
    }

    if (!messageId) throw new Error('messageId required');

    console.log('[editMessage] id:', messageId, 'newText:', newText);
    // Validación mínima
    if (!newText || newText.trim().length === 0) {
      alert('El contenido no puede estar vacío.');
      return;
    }
    
    const ack = await emitEditMessage(messageId, newText.trim());
    // ack puede ser { ok: true } o null (timeout)
    if (ack && ack.ok === false) {
      console.warn('[editMessage] server returned error:', ack);
      alert('No se pudo editar el mensaje: ' + (ack.error || JSON.stringify(ack)));
      return;
    }

    // Si el servidor emitió message_edited, el cliente que lo emitió recibirá el evento
    // pero por si no, actualizamos localmente la burbuja
    handleSocketEditedMessage({ message: { message_id: messageId, new_message: newText.trim(), username: (document.querySelector('#chat')?.dataset?.myUsername) } });

    console.log('[editMessage] edit emitted/sent OK');
  } catch (err) {
    console.error('[editMessage] error:', err);
    alert('Error editando mensaje: ' + (err.message || err));
  }
}
function openInlineEditorForMessage(messageId) {
  if (!messageId) {
    // intentar leer del popup si no se pasa
    const popup = document.getElementById('mazo-options-popup');
    if (popup && popup.dataset && popup.dataset.currentMessageId) {
      messageId = popup.dataset.currentMessageId;
    }
  }
  if (!messageId) {
    console.warn('openInlineEditorForMessage: no messageId disponible');
    return;
  }

  const msgEl = document.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) {
    console.warn('openInlineEditorForMessage: no se encontró el elemento', messageId);
    return;
  }

  // Evitar duplicados: si ya existe editor en este mensaje, hacer focus
  if (msgEl.querySelector('.inline-edit-wrapper')) {
    msgEl.querySelector('.inline-edit-wrapper textarea')?.focus();
    return;
  }

  // localizar elemento de texto actual (varias posibilidades según tu template)
  const textEl = msgEl.querySelector('.message-text, .msg-text, .msg-body .msg-text, p.message-text');
  const currentText = textEl ? textEl.textContent.trim() : '';

  // crear wrapper del editor
  const wrap = document.createElement('div');
  wrap.className = 'inline-edit-wrapper';
  wrap.style.display = 'flex';
  wrap.style.flexDirection = 'column';
  wrap.style.gap = '8px';
  wrap.style.marginTop = '6px';

  const ta = document.createElement('textarea');
  ta.className = 'inline-edit-textarea';
  ta.value = currentText;
  ta.rows = Math.min(6, Math.max(2, (currentText.split('\n').length || 1)));
  ta.style.width = '100%';
  ta.style.boxSizing = 'border-box';
  ta.style.padding = '8px';
  ta.style.borderRadius = '8px';
  ta.style.border = '1px solid rgba(0,0,0,0.12)';
  ta.style.fontSize = '0.95rem';
  ta.style.resize = 'vertical';

  // buttons container
  const btns = document.createElement('div');
  btns.style.display = 'flex';
  btns.style.gap = '8px';
  btns.style.justifyContent = 'flex-end';

  const btnSave = document.createElement('button');
  btnSave.type = 'button';
  btnSave.className = 'inline-edit-save';
  btnSave.textContent = 'Guardar';
  btnSave.style.padding = '6px 10px';
  btnSave.style.borderRadius = '8px';
  btnSave.style.border = 'none';
  btnSave.style.cursor = 'pointer';
  btnSave.style.background = '#0b76ff';
  btnSave.style.color = '#fff';

  const btnCancel = document.createElement('button');
  btnCancel.type = 'button';
  btnCancel.className = 'inline-edit-cancel';
  btnCancel.textContent = 'Cancelar';
  btnCancel.style.padding = '6px 10px';
  btnCancel.style.borderRadius = '8px';
  btnCancel.style.border = '1px solid rgba(0,0,0,0.08)';
  btnCancel.style.cursor = 'pointer';
  btnCancel.style.background = '#fff';
  btnCancel.style.color = '#111';

  btns.appendChild(btnCancel);
  btns.appendChild(btnSave);

  wrap.appendChild(ta);
  wrap.appendChild(btns);

  // Insertar el editor en el DOM: después del texto existente, o al final de .message-content
  const contentEl = msgEl.querySelector('.message-content') || msgEl;
  if (textEl && textEl.parentElement) {
    textEl.parentElement.insertBefore(wrap, textEl.nextSibling);
    // opcional: ocultar el textEl mientras editamos para evitar duplicados
    textEl.style.display = 'none';
  } else {
    contentEl.appendChild(wrap);
  }

  // focus y seleccionar
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);

  // Helpers para cancelar/guardar
  function cleanupRestore() {
    // eliminar editor y mostrar texto original
    if (wrap && wrap.parentElement) wrap.remove();
    if (textEl) textEl.style.display = '';
  }

  async function doSave() {
    const newText = ta.value.trim();
    if (newText.length === 0) {
      if (!confirm('El mensaje quedará vacío. ¿Continuar?')) return;
    }
    // Desactivar botones para evitar múltiples clicks
    btnSave.disabled = true;
    btnCancel.disabled = true;
    btnSave.textContent = 'Guardando...';

    try {
      // llama a tu función editMessage (emit socket)
      await editMessage(messageId, newText);
      // si editMessage actualiza el DOM vía handleSocketEditedMessage, ya estará.
      // Para robustez, actualizamos localmente aquí también:
      const newTextEl = msgEl.querySelector('.message-text, .msg-text, .msg-body .msg-text, p.message-text') || textEl;
      if (newTextEl) {
        newTextEl.textContent = newText;
        newTextEl.style.display = '';
      }
      // añadir badge editado si no existe
      let editedBadge = msgEl.querySelector('.edited-badge');
      if (!editedBadge) {
        editedBadge = document.createElement('span');
        editedBadge.className = 'edited-badge';
        editedBadge.textContent = ' (editado)';
        editedBadge.style.fontSize = '0.8rem';
        editedBadge.style.opacity = '0.85';
        const head = msgEl.querySelector('.msg-head') || msgEl.querySelector('.message-content');
        if (head) head.appendChild(editedBadge);
      }
    } catch (err) {
      console.error('Error guardando edición:', err);
      alert('Error guardando edición: ' + (err.message || err));
    } finally {
      cleanupRestore();
    }
  }

  function doCancel() {
    cleanupRestore();
  }

  // Eventos
  btnSave.addEventListener('click', doSave);
  btnCancel.addEventListener('click', doCancel);

  // Atajos de teclado: Ctrl/Cmd+Enter = guardar, Esc = cancelar
  function keyHandler(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      doSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      doCancel();
    }
  }
  ta.addEventListener('keydown', keyHandler);

  // asegurarse de limpiar listeners si el popup se cierra
  const cleanupAll = () => {
    ta.removeEventListener('keydown', keyHandler);
  };

  // wrap cleanup al eliminar
  const observer = new MutationObserver(() => {
    if (!document.body.contains(wrap)) {
      cleanupAll();
      observer.disconnect();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

function openEditModal(messageId) {
  // preferimos edición inline
  openInlineEditorForMessage(messageId);
}
/**
 * deleteMessage(messageId)
 * - llama a emitDeleteMessage y maneja la respuesta
 */
async function deleteMessage(messageId) {
  try {
    console.log('[deleteMessage] id:', messageId);
    const ack = await emitDeleteMessage(messageId);
    if (ack && ack.ok === false) {
      console.warn('[deleteMessage] server returned error:', ack);
      alert('No se pudo borrar el mensaje: ' + (ack.error || JSON.stringify(ack)));
      return;
    }

    // Si el servidor emitió message_deleted, lo recibirás; si no, borramos localmente
    handleSocketDeletedMessage({ message_id: messageId });

    console.log('[deleteMessage] delete emitted/sent OK');
  } catch (err) {
    console.error('[deleteMessage] error:', err);
    alert('Error borrando mensaje: ' + (err.message || err));
  }
}

/* ======= Handlers que actualizan el DOM cuando llegan eventos del servidor ======= */

/**
 * handleSocketEditedMessage(payload)
 * - payload esperado: { message_id, new_message, username }
 * - actualiza el contenido del DOM para ese message_id
 */
function handleSocketEditedMessage(payload) {
  try {
    const p = payload || {};
    console.log('[handleSocketEditedMessage] payload:', p);
    const id = p.message_id || p.id || p.message?.message_id;
    const text = p.new_message || p.newMessage || p.message?.new_message || p.message?.text || '';
    if (!id) return console.warn('handleSocketEditedMessage: no message_id in payload');

    const msgEl = document.querySelector(`[data-message-id="${id}"]`);
    if (!msgEl) {
      console.warn('handleSocketEditedMessage: no element found for id', id);
      return;
    }

    // actualizar texto en .message-text o .msg-text o .msg-body .msg-text
    let textEl = msgEl.querySelector('.message-text, .msg-text, .msg-body .msg-text, .msg-body p');
    if (!textEl) {
      // Si no existe, crear uno (por ej. si era solo un file antes)
      textEl = document.createElement('p');
      textEl.className = 'message-text';
      msgEl.querySelector('.message-content')?.appendChild(textEl);
    }
    textEl.textContent = text;

    // Marcar visualmente que fue editado (opcional)
    let editedBadge = msgEl.querySelector('.edited-badge');
    if (!editedBadge) {
      editedBadge = document.createElement('span');
      editedBadge.className = 'edited-badge';
      editedBadge.textContent = ' (editado)';
      editedBadge.style.fontSize = '0.8rem';
      editedBadge.style.opacity = '0.8';
      const head = msgEl.querySelector('.msg-head') || msgEl.querySelector('.message-content');
      if (head) head.appendChild(editedBadge);
    }
  } catch (err) {
    console.warn('handleSocketEditedMessage error', err);
  }
}

/**
 * handleSocketDeletedMessage(payload)
 * - payload esperado: { message_id }
 * - elimina el nodo DOM correspondiente
 */
function handleSocketDeletedMessage(payload) {
  try {
    const id = payload?.message_id || payload?.id || payload?.message?.message_id;
    if (!id) return;
    const msgEl = document.querySelector(`[data-message-id="${id}"]`);
    if (!msgEl) {
      console.warn('handleSocketDeletedMessage: element not found for id', id);
      return;
    }

    // si prefieres, animamos la desaparición
    msgEl.style.transition = 'opacity .18s ease, transform .18s ease';
    msgEl.style.opacity = '0';
    msgEl.style.transform = 'translateY(-8px)';
    setTimeout(() => { msgEl.remove(); }, 180);
  } catch (err) {
    console.warn('handleSocketDeletedMessage error', err);
  }
}

/* ========================
   Vinculación: si registerSocketHandlers ya registra `message_edited`/`message_deleted`,
   esas emisiones deberían llegar y llamar a handleSocketEditedMessage / handleSocketDeletedMessage.
   Si no, asegúrate de que registerSocketHandlers llame aquí.
   ======================== */

// Si registerSocketHandlers no llama a estas funciones, force-add listeners:
if (window.socket && typeof window.socket.on === 'function') {
  try {
    // registrar handlers seguros (no duplicar)
    if (!window._mazo_handlers_edit_delete_registered) {
      window.socket.on('message_edited', (payload) => {
        console.log('[socket] event message_edited received:', payload);
        try { handleSocketEditedMessage(payload); } catch(e){ console.warn(e); }
      });
      window.socket.on('message_deleted', (payload) => {
        console.log('[socket] event message_deleted received:', payload);
        try { handleSocketDeletedMessage(payload); } catch(e){ console.warn(e); }
      });
      window._mazo_handlers_edit_delete_registered = true;
    }
  } catch (e) {
    console.warn('Error registrando handlers edit/delete on socket:', e);
  }
}

/* ==========================
   MODALES / UI
   ========================== */
function openEditModal(message) {
  // implementa tu modal preferido; aquí un proceso simple:
  const newText = prompt('Editar mensaje', message.text || '');
  if (newText === null) return; // cancelado
  editMessage(message.id, newText)
    .then(updated => {
      // actualizar DOM optimista
      const el = document.querySelector(`[data-message-id="${message.id}"] .msg-text`);
      if (el) el.innerHTML = nl2br(escapeHtml(updated.text));
    })
    .catch(err => console.error(err));
}

/* ==========================
   SOCKET EVENT HANDLERS
   ========================== */
function handleSocketNewMessage({ message: payload, room_id = null } = {}) {
  const p = message || {};
  console.log('[handleSocketNewMessage] raw payload:', p, 'room:', room_id);

  // elegir contenedor correcto: primero #chat-box (tu plantilla), luego selectores alternativos
  const container = document.querySelector('#chat-box') ||
                    document.querySelector('#chat-messages') ||
                    document.querySelector('#chat') ||
                    (document.body);

  // Normalizar autor
  const author = {
    username: p.username || p.author?.username || p.sender || 'unknown',
    avatar: p.avatar || p.author?.avatar || p.profile_pic || '/static/profile_pics/default.jpg'
  };

  // Normalizar id / timestamp / text
  const id = p.message_id || p.id || p.msg_id || null;
  const created_at = p.timestamp || p.created_at || new Date().toISOString();
  const text = (p.message !== undefined) ? p.message : (p.content || p.text || '');

  // Si viene archivo (stream_url / file_url / file_base64)
  if ((p.file_url && p.file_url !== '') || p.file_base64) {
    let fileUrl = p.file_url || p.file || null;
    // si viene base64 (sin header), agregar data: header si falta
    if (!fileUrl && p.file_base64) {
      fileUrl = p.file_base64.startsWith('data:') ? p.file_base64 : ('data:;base64,' + p.file_base64);
    }

    // Si servidor devolvió objeto upload/file con stream_url, tomarlo
    if (typeof fileUrl === 'object' && fileUrl.stream_url) fileUrl = fileUrl.stream_url;

    const filename = p.file_name || (fileUrl ? (fileUrl.split('/').pop() || '') : '');
    const ext = (filename.split('.').pop() || '').toLowerCase();
    let mime = '';
    if (['jpg','jpeg','png','gif','webp'].includes(ext)) mime = 'image/' + ext;
    if (['mp4','webm','mov','avi','mpg'].includes(ext)) mime = 'video/' + ext;

    const messageObj = {
      id,
      author,
      file: {
        url: fileUrl || '',
        filename,
        mime,
        thumbnail: p.thumbnail_url || p.thumbnail || p.thumbnail_url || ''
      },
      text: text || '',
      created_at,
      is_owner: (author.username === (document.querySelector('#chat-box')?.dataset?.username || document.querySelector('#chat')?.dataset?.myUsername))
    };

    // render using your renderer if exists, otherwise fallback minimal DOM
    if (typeof renderFileMessage === 'function') {
      renderFileMessage(container, messageObj);
    } else {
      // fallback: quick append
      const w = document.createElement('div');
      w.className = 'chat-message file ' + (messageObj.is_owner ? 'my-message' : 'other-message');
      w.dataset.messageId = messageObj.id || '';
      w.innerHTML = `
        <div class="message-content">
          ${messageObj.text ? `<p class="message-text">${escapeHtml(messageObj.text)}</p>` : ''}
          ${mime.startsWith('image/') ? `<img class="chat-thumbnail" src="${messageObj.file.url}" data-file-url="${messageObj.file.url}"/>`
            : mime.startsWith('video/') ? `<div class="video-thumbnail" data-file-url="${messageObj.file.url}"><img src="${messageObj.file.thumbnail||''}" class="chat-thumbnail"/><i class="fa fa-play play-icon"></i></div>`
            : `<div class="file-thumbnail" data-file-url="${messageObj.file.url}"><i class="fas fa-file file-icon"></i><div class="file-name">${escapeHtml(messageObj.file.filename)}</div></div>`}
        </div>`;
      container.appendChild(w);
      container.scrollTop = container.scrollHeight;
    }

    // ensure new elements are visible
    setTimeout(()=> {
      container.scrollTop = container.scrollHeight;
    }, 60);

    return;
  }

  // Texto simple
  const messageObj = {
    id,
    author,
    text,
    created_at,
    is_owner: (author.username === (document.querySelector('#chat-box')?.dataset?.username || document.querySelector('#chat')?.dataset?.myUsername))
  };

  if (typeof renderTextMessage === 'function') {
    renderTextMessage(container, messageObj);
  } else {
    // fallback simple
    const w = document.createElement('div');
    w.className = 'chat-message ' + (messageObj.is_owner ? 'my-message' : 'other-message');
    if (messageObj.id) w.dataset.messageId = messageObj.id;
    const content = document.createElement('div');
    content.className = 'message-content';
    const pEl = document.createElement('p');
    pEl.className = 'message-text';
    pEl.textContent = messageObj.text;
    content.appendChild(pEl);
    w.appendChild(content);
    container.appendChild(w);
  }

  // scroll to bottom
  setTimeout(()=> {
    container.scrollTop = container.scrollHeight;
  }, 40);
}

/* small helper used in fallback render */
function escapeHtml(unsafe) {
  if (!unsafe && unsafe !== 0) return '';
  return String(unsafe)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

/* ===========================
   FIX: abrir modales para imágenes/videos/archivos (delegación)
   Usa los modales ya presentes en tu plantilla: #image-modal, #video-modal
   =========================== */
/* =========================
   OPEN FILES IN MODAL
   ========================= */

// Helpers para obtener los elementos del DOM del modal
function _getImageModalEls() {
  return {
    modal: document.getElementById('image-modal'),
    img: document.getElementById('modal-image'),
    download: document.getElementById('download-link'),
    closeBtn: document.querySelector('#image-modal .close-modal')
  };
}
function _getVideoModalEls() {
  return {
    modal: document.getElementById('video-modal'),
    video: document.getElementById('modal-video'),
    download: document.getElementById('video-download-link'),
    closeBtn: document.querySelector('#video-modal .close-modal')
  };
}

// Abre modal de imagen con URL (url puede ser data:, http(s) o ruta relativa)
function openImageModal(url, filename = null) {
  try {
    const { modal, img, download, closeBtn } = _getImageModalEls();
    if (!modal || !img) { console.warn('[openImageModal] modal o img no encontrados'); return; }

    console.log('[openImageModal] abrir ->', url);

    // set src y alt
    img.src = url;
    img.alt = filename || url.split('/').pop() || 'imagen';

    // preparar enlace descarga
    if (download) {
      download.href = url;
      if (filename) download.setAttribute('download', filename);
      else download.removeAttribute('download');
      download.style.display = 'inline-block';
    }

    // mostrar modal
    modal.style.display = 'block';
    modal.setAttribute('aria-hidden', 'false');

    // focus y log
    img.focus?.();
  } catch (err) {
    console.error('[openImageModal] error', err);
  }
}

// Cerrar modal imagen y limpiar src (para liberar memoria)
function closeImageModal() {
  const { modal, img, download } = _getImageModalEls();
  if (!modal) return;
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
  if (img) {
    // quitar src para detener cargas y liberar memoria
    try { img.src = ''; } catch(e) {}
  }
  if (download) download.style.display = 'none';
  console.log('[closeImageModal] cerrado');
}

// Abrir modal vídeo (url puede ser stream url o MP4)
function openVideoModal(url, filename = null) {
  try {
    const { modal, video, download } = _getVideoModalEls();
    if (!modal || !video) { console.warn('[openVideoModal] modal o video no encontrados'); return; }

    console.log('[openVideoModal] abrir ->', url);

    // limpiar sources previos
    while (video.firstChild) video.removeChild(video.firstChild);

    const src = document.createElement('source');
    src.src = url;
    // intentar inferir tipo por extensión:
    const ext = (url.split('.').pop() || '').toLowerCase();
    if (ext) src.type = (ext === 'mp4' || ext === 'm4v') ? 'video/mp4' : `video/${ext}`;

    video.appendChild(src);
    video.load();
    video.play().catch(e => { /* autoplay puede fallar si no hay interacción */ });

    // download
    if (download) {
      download.href = url;
      if (filename) download.setAttribute('download', filename);
      else download.removeAttribute('download');
      download.style.display = 'inline-block';
    }

    modal.style.display = 'block';
    modal.setAttribute('aria-hidden', 'false');
  } catch (err) {
    console.error('[openVideoModal] error', err);
  }
}

function closeVideoModal() {
  const { modal, video, download } = _getVideoModalEls();
  if (!modal) return;
  modal.style.display = 'none';
  modal.setAttribute('aria-hidden', 'true');
  if (video) {
    try {
      video.pause();
      // quitar sources
      while (video.firstChild) video.removeChild(video.firstChild);
      video.removeAttribute('src');
      video.load?.();
    } catch (e) {}
  }
  if (download) download.style.display = 'none';
  console.log('[closeVideoModal] cerrado');
}

/* Delegación de eventos: click en miniaturas / file-thumbnail / play-icon / chat-thumbnail */
document.addEventListener('click', (e) => {
  const clickEl = e.target;

  // 1) Imagenes con clase .chat-thumbnail o data-file-url en <img>
  const imgEl = clickEl.closest('img.chat-thumbnail, img[data-file-url]');
  if (imgEl) {
    const url = imgEl.dataset?.fileUrl || imgEl.getAttribute('data-file-url') || imgEl.src;
    const filename = imgEl.dataset?.filename || (url ? url.split('/').pop() : null);
    if (url) {
      // si es imagen -> abrir imagen
      openImageModal(url, filename);
      e.preventDefault();
      return;
    }
  }

  // 2) Click en contenedores con data-file-url (p.ej. .file-thumbnail, .video-thumbnail)
  const fileThumb = clickEl.closest('[data-file-url], .file-thumbnail, .video-thumbnail');
  if (fileThumb) {
    const url = fileThumb.dataset?.fileUrl || fileThumb.getAttribute('data-file-url') || null;
    const fn = fileThumb.dataset?.filename || (url ? url.split('/').pop() : null);
    if (!url) {
      console.warn('[file click] no data-file-url encontrado en el elemento', fileThumb);
      return;
    }
    // decidir: si la extensión es imagen -> image modal; si es video -> video modal; else abrir en nueva pestaña
    const ext = (fn || url.split('/').pop() || '').split('.').pop().toLowerCase();
    if (['jpg','jpeg','png','gif','webp'].includes(ext)) {
      openImageModal(url, fn);
    } else if (['mp4','webm','mov','avi','mpg','m4v'].includes(ext)) {
      openVideoModal(url, fn);
    } else {
      // archivos no multimedia: abrir en nueva pestaña (y permitir descarga)
      console.log('[file click] abrir archivo en pestaña:', url);
      window.open(url, '_blank', 'noopener');
    }
    e.preventDefault();
    return;
  }

  // 3) Icono de play dentro de miniatura (p.ej. <i class="fa fa-play play-icon">)
  const playIcon = clickEl.closest('.play-icon, .video-play');
  if (playIcon) {
    const container = playIcon.closest('[data-file-url], .video-thumbnail');
    if (container) {
      const url = container.dataset?.fileUrl || container.getAttribute('data-file-url');
      const fn = container.dataset?.filename || (url ? url.split('/').pop() : null);
      if (url) {
        openVideoModal(url, fn);
        e.preventDefault();
        return;
      }
    }
  }

  // 4) Si se hace click en el enlace de descarga dentro del modal, no hacemos nada especial (se maneja por el anchor)
});

// Asegura cierre al clicar fuera y que los botones funcionen
(function() {
  // Cerrar image modal y limpiar
  function closeImageModal() {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image');
    const download = document.getElementById('download-link');
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    if (img) try { img.src = ''; } catch(e){}
    if (download) download.style.display = 'none';
  }

  // Cerrar video modal y limpiar
  function closeVideoModal() {
    const modal = document.getElementById('video-modal');
    const video = document.getElementById('modal-video');
    const download = document.getElementById('video-download-link');
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    if (video) {
      try {
        video.pause();
        while (video.firstChild) video.removeChild(video.firstChild);
        video.removeAttribute('src');
        video.load && video.load();
      } catch (e) {}
    }
    if (download) download.style.display = 'none';
  }

/* ==========================================================
   FILE PREVIEW – versión adaptada a tu CSS (simple & perfecta)
   ========================================================== */

(function () {
    const fileInput = document.getElementById("file-input");
    const textarea = document.getElementById("message");
    const chatInput = document.getElementById("chat-input");

    if (!fileInput) {
        console.warn("[filePreview] No se encontró #file-input");
        return;
    }

    // Crear el contenedor si no existe
    let previewContainer =
        document.getElementById("file-preview-container");

    if (!previewContainer) {
        previewContainer = document.createElement("div");
        previewContainer.id = "file-preview-container";
        previewContainer.style.display = "none";

        // Insertarlo justo encima del textarea
        if (chatInput) chatInput.prepend(previewContainer);
        else textarea.parentElement.prepend(previewContainer);
    }

    // Estado interno
    window._mazo_selected_files = [];

    function syncInputFiles() {
        const dt = new DataTransfer();
        window._mazo_selected_files.forEach(f => dt.items.add(f));
        fileInput.files = dt.files;
    }

    function humanSize(size) {
        if (!size) return "0 B";
        const i = Math.floor(Math.log(size) / Math.log(1024));
        const units = ["B", "KB", "MB", "GB"];
        return (size / Math.pow(1024, i)).toFixed(1) + " " + units[i];
    }

    function renderPreviews() {
        previewContainer.innerHTML = "";

        if (!window._mazo_selected_files.length) {
            previewContainer.style.display = "none";
            return;
        }

        previewContainer.style.display = "flex";

        window._mazo_selected_files.forEach((file, i) => {
            const box = document.createElement("div");
            box.className = "file-preview";
            box.dataset.index = i;

            // Miniatura si es imagen
            if (file.type.startsWith("image/")) {
                const img = document.createElement("img");
                img.className = "file-preview-thumb";

                const reader = new FileReader();
                reader.onload = ev => (img.src = ev.target.result);
                reader.readAsDataURL(file);

                box.appendChild(img);
            }

            // Nombre y tamaño
            const name = document.createElement("span");
            name.textContent = `${file.name} (${humanSize(file.size)})`;
            box.appendChild(name);

            // Botón X
            const remove = document.createElement("span");
            remove.textContent = "✕";
            remove.className = "remove-file";

            remove.addEventListener("click", e => {
                e.stopPropagation();
                window._mazo_selected_files.splice(i, 1);
                syncInputFiles();
                renderPreviews();
            });

            box.appendChild(remove);
            previewContainer.appendChild(box);
        });
    }

    // Cuando seleccionas archivo(s)
    fileInput.addEventListener("change", () => {
        Array.from(fileInput.files).forEach(f => {
            const exists = window._mazo_selected_files.some(
                ex => ex.name === f.name && ex.size === f.size
            );
            if (!exists) window._mazo_selected_files.push(f);
        });
        syncInputFiles();
        renderPreviews();
    });

    // Función pública para limpiar tras enviar
    window._mazo_clearSelectedFiles = function () {
        window._mazo_selected_files = [];
        syncInputFiles();
        renderPreviews();
    };
})();


  // Close buttons
  document.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('#image-modal .close-modal, #video-modal .close-modal');
    if (closeBtn) {
      const parent = closeBtn.closest('.modal');
      if (!parent) return;
      if (parent.id === 'image-modal') closeImageModal();
      else if (parent.id === 'video-modal') closeVideoModal();
    }
  });

  // Click fondo (si se hace click en .modal y no en .modal-inner) -> cerrar
  document.addEventListener('click', (e) => {
    const imgModal = document.getElementById('image-modal');
    if (imgModal && imgModal.style.display === 'flex' || imgModal && imgModal.style.display === 'block') {
      if (e.target === imgModal) closeImageModal();
    }
    const vidModal = document.getElementById('video-modal');
    if (vidModal && vidModal.style.display === 'flex' || vidModal && vidModal.style.display === 'block') {
      if (e.target === vidModal) closeVideoModal();
    }
  }, true);

  // Esc para cerrar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeImageModal();
      closeVideoModal();
    }
  });

  // Exponer funciones para que el resto de tu JS (openImageModal/openVideoModal) las use:
  window._mazo_closeImageModal = closeImageModal;
  window._mazo_closeVideoModal = closeVideoModal;

  // Si tus openImageModal / openVideoModal usan download links, asegurarse de que los botones se muestren:
  // (si ya has implementado openImageModal/openVideoModal, estas líneas no rompen nada)
  window._mazo_showImageModal = function(url, filename) {
    const modal = document.getElementById('image-modal');
    const img = document.getElementById('modal-image');
    const download = document.getElementById('download-link');
    if (!modal || !img) return;
    img.src = url;
    img.alt = filename || url.split('/').pop() || '';
    if (download) {
      download.href = url;
      if (filename) download.setAttribute('download', filename);
      else download.removeAttribute('download');
      download.style.display = 'inline-block';
    }
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
  };

  window._mazo_showVideoModal = function(url, filename) {
    const modal = document.getElementById('video-modal');
    const video = document.getElementById('modal-video');
    const download = document.getElementById('video-download-link');
    if (!modal || !video) return;
    // limpiar previos
    while (video.firstChild) video.removeChild(video.firstChild);
    const src = document.createElement('source');
    src.src = url;
    const ext = (url.split('.').pop() || '').toLowerCase();
    src.type = (ext === 'mp4' || ext === 'm4v') ? 'video/mp4' : `video/${ext}`;
    video.appendChild(src);
    video.load();
    try { video.play().catch(()=>{}); } catch(e){}
    if (download) {
      download.href = url;
      if (filename) download.setAttribute('download', filename);
      else download.removeAttribute('download');
      download.style.display = 'inline-block';
    }
    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
  };

})();

// Asegurar que los botones "close-modal" existan (si no, creamos handlers de seguridad)
(function attachCloseButtons() {
  const imgClose = document.querySelector('#image-modal .close-modal');
  if (imgClose) imgClose.addEventListener('click', closeImageModal);
  const vidClose = document.querySelector('#video-modal .close-modal');
  if (vidClose) vidClose.addEventListener('click', closeVideoModal);
})();

/* ==========================
   BIND UI EVENTS (listeners)
   ========================== */
function attachChatFormListeners() {
  const form = document.querySelector('#chat-form');
  const input = document.querySelector('#chat-input');
  const fileInput = document.querySelector('#chat-file-input');
  const sendBtn = document.querySelector('#chat-send-btn');
  const roomId = document.querySelector('#chat-room-id')?.value;

  if (!form || !input || !sendBtn) return;

  sendBtn.addEventListener('click', (e) => {
    e.preventDefault();
    sendTextMessage(roomId, input.value).then(() => {
      input.value = '';
    });
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    sendTextMessage(roomId, input.value).then(() => input.value = '');
  });

  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      const files = Array.from(e.target.files);
      for (const f of files) {
        await sendFileMessage(roomId, f);
      }
      fileInput.value = '';
    });
  }

  // atajos teclado: Ctrl+Enter enviar
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendTextMessage(roomId, input.value).then(() => input.value = '');
    }
  });
}

/* ==========================
   STARTUP
   ========================== */
function startChat(options = {}) {
  if (!socket) initSocket(options.namespace || '');
  attachChatFormListeners();
  // otras inicializaciones (ej: cargar mensajes históricos vía fetch)
}

/* ==========================
   EXPORT / GLOBAL
   ========================== */
// si usas bundler exporta; si no, déjalo global
// Export seguro: añade sólo las funciones que estén definidas
window.MAZOChat = window.MAZOChat || {};
// preferimos no sobreescribir si ya hay algo
Object.assign(window.MAZOChat, {
  start: typeof startChat === 'function' ? startChat : (window.MAZOChat.start || null),
  createRoom: typeof createRoom === 'function' ? createRoom : (window.MAZOChat.createRoom || null),
  joinRoom: typeof joinRoom === 'function' ? joinRoom : (window.MAZOChat.joinRoom || null),
  // funciones de envío
  sendTextMessage,
  sendFileMessage,
  // compat alias HTTP
  sendTextMessageHttp,
  sendFileMessageHttp,
  // edición/borrado (si existen)
  editMessage: typeof editMessage === 'function' ? editMessage : (window.MAZOChat.editMessage || null),
  deleteMessage: typeof deleteMessage === 'function' ? deleteMessage : (window.MAZOChat.deleteMessage || null)
});
