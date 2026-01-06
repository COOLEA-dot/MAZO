document.addEventListener("DOMContentLoaded", () => {
  const deleteBtn = document.getElementById("deleteAccountBtn");
  if (!deleteBtn) return;

  deleteBtn.addEventListener("click", () => {
    const confirmed = confirm(
      "¿Estás seguro? Esta acción eliminará tu cuenta y todos tus datos."
    );
    if (!confirmed) return;

    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      .getAttribute("content");

    fetch("/delete-account", {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest"
      }
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          window.location.href = "/";
        } else {
          alert("Error al eliminar la cuenta");
        }
      })
      .catch(() => {
        alert("Error de conexión");
      });
  });
});
