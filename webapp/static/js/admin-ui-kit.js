// Composants transverses réutilisables par tout le panneau admin — modale de
// confirmation élégante (remplace window.confirm()) et notification de
// succès/erreur. Un seul jeu de composants partagé, jamais une modale/un
// toast redéfini par page (voir admin.html pour le balisage statique
// correspondant, même principe que admin-collapse.js).

export function confirmDialog({ title, text, confirmLabel = "Confirmer", danger = true }) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("admin-confirm-modal");
    const confirmBtn = document.getElementById("admin-confirm-modal-confirm");
    const cancelBtn = document.getElementById("admin-confirm-modal-cancel");
    const closeBtn = document.getElementById("admin-confirm-modal-close");
    document.getElementById("admin-confirm-modal-title").textContent = title;
    document.getElementById("admin-confirm-modal-text").textContent = text || "";
    confirmBtn.textContent = confirmLabel;
    confirmBtn.className = `admin-btn ${danger ? "admin-btn--danger" : "admin-btn--primary"}`;

    const close = (result) => {
      overlay.hidden = true;
      confirmBtn.removeEventListener("click", onConfirm);
      cancelBtn.removeEventListener("click", onCancel);
      closeBtn.removeEventListener("click", onCancel);
      overlay.removeEventListener("click", onOverlayClick);
      document.removeEventListener("keydown", onKeydown);
      resolve(result);
    };
    const onConfirm = () => close(true);
    const onCancel = () => close(false);
    const onOverlayClick = (e) => { if (e.target === overlay) close(false); };
    const onKeydown = (e) => { if (e.key === "Escape") close(false); };

    confirmBtn.addEventListener("click", onConfirm);
    cancelBtn.addEventListener("click", onCancel);
    closeBtn.addEventListener("click", onCancel);
    overlay.addEventListener("click", onOverlayClick);
    document.addEventListener("keydown", onKeydown);
    overlay.hidden = false;
    confirmBtn.focus();
  });
}

let toastTimer = null;

export function showToast(message, isError = false) {
  const el = document.getElementById("admin-toast");
  clearTimeout(toastTimer);
  el.classList.remove("is-leaving");
  el.className = `admin-toast${isError ? " admin-toast--error" : ""}`;
  el.textContent = message;
  el.hidden = false;
  toastTimer = setTimeout(() => {
    el.classList.add("is-leaving");
    el.addEventListener("animationend", () => { el.hidden = true; }, { once: true });
  }, 2600);
}
