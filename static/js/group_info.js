function makeAdmin(groupId, userId) {
  fetch(`/groups/${groupId}/make-admin/${userId}`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCSRFToken() }
  }).then(() => location.reload());
}

function removeAdmin(groupId, userId) {
  fetch(`/groups/${groupId}/remove-admin/${userId}`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCSRFToken() }
  }).then(() => location.reload());
}

function removeMember(groupId, userId) {
  if (!confirm("¿Eliminar este usuario del grupo?")) return;

  fetch(`/groups/${groupId}/remove-member/${userId}`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCSRFToken() }
  }).then(() => location.reload());
}
