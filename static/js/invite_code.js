let currentInviteGroupId = null;
let selectedChats = new Map(); // conversationId => username

/* 🔐 Obtener CSRF token desde cookies (Flask-WTF) */
function getCSRFToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : '';
}

function openInviteGroupModal(groupId) {
  currentInviteGroupId = groupId;
  selectedChats.clear();

  document
    .getElementById('invite-group-modal')
    .classList.remove('hidden');

  updateInviteButton();
  loadInviteChats();
}

function closeInviteModal() {
  document
    .getElementById('invite-group-modal')
    .classList.add('hidden');
}

/**
 * Cargar chats del usuario
 */
function loadInviteChats() {
  fetch('/api/chats')
    .then(res => res.json())
    .then(chats => {
      const container = document.getElementById('invite-chats-list');
      container.innerHTML = '';

      if (!chats.length) {
        container.innerHTML = '<p>No tienes chats</p>';
        return;
      }

      chats.forEach(chat => {
        const div = document.createElement('div');
        div.className = 'invite-chat-item';

        div.innerHTML = `
          <img src="${chat.avatar}">
          <span>${chat.name}</span>
        `;

        div.addEventListener('click', () => {
          toggleChatSelection(chat, div);
        });

        container.appendChild(div);
      });
    });
}

/**
 * Seleccionar / deseleccionar chat
 */
function toggleChatSelection(chat, element) {
  if (selectedChats.has(chat.id)) {
    selectedChats.delete(chat.id);
    element.classList.remove('selected');
  } else {
    selectedChats.set(chat.id, chat.name);
    element.classList.add('selected');
  }

  updateInviteButton();
}

/**
 * Actualizar botón Compartir
 */
function updateInviteButton() {
  const btn = document.getElementById('invite-confirm-btn');
  if (!btn) return;

  if (selectedChats.size === 0) {
    btn.disabled = true;
    btn.textContent = 'Compartir';
    return;
  }

  btn.disabled = false;

  const names = Array.from(selectedChats.values()).slice(0, 2).join(', ');
  const extra =
    selectedChats.size > 2
      ? ` +${selectedChats.size - 2}`
      : '';

  btn.textContent = `Compartir con: ${names}${extra}`;
}

/**
 * Confirmar envío de invitaciones
 */
function confirmGroupInvite() {
  if (!currentInviteGroupId || selectedChats.size === 0) return;

  const csrfToken = getCSRFToken();
  const requests = [];

  selectedChats.forEach((_, conversationId) => {
    requests.push(
      fetch(`/groups/send-invite/${currentInviteGroupId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          conversation_id: conversationId
        })
      })
    );
  });

  Promise.all(requests).then(() => {
    closeInviteModal();
  });
}
