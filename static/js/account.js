document.addEventListener("DOMContentLoaded", () => {
  const deleteBtn = document.getElementById("deleteAccountBtn");
  const modal = document.getElementById("deleteModal");
  const confirmBtn = document.getElementById("confirmDelete");
  const cancelBtn = document.getElementById("cancelDelete");

  if (!deleteBtn) return;

  deleteBtn.addEventListener("click", () => {
    modal.style.display = "flex";
  });

  cancelBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  confirmBtn.addEventListener("click", () => {
    const csrfToken = document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content");

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
