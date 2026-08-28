// Section repliable transverse (Utilisateurs/IA/Santé/Paramètres) : persiste
// l'état ouvert/fermé par section via localStorage, l'ouverture/fermeture
// elle-même reste gérée nativement par <details>.
const STORAGE_PREFIX = "admin-collapse:";

export function createCollapseSection({ id, title, hint = "", open = false, bodyHtml = "" }) {
  const stored = readStoredState(id);
  const isOpen = stored === null ? open : stored;
  return `
    <details class="admin-collapse" data-collapse-id="${id}"${isOpen ? " open" : ""}>
      <summary class="admin-collapse-summary">
        <span>${title}</span>
        ${hint ? `<span class="admin-collapse-hint">${hint}</span>` : ""}
      </summary>
      <div class="admin-collapse-body">${bodyHtml}</div>
    </details>
  `;
}

export function wireCollapsePersistence(root) {
  root.querySelectorAll(".admin-collapse[data-collapse-id]").forEach((el) => {
    el.addEventListener("toggle", () => {
      writeStoredState(el.dataset.collapseId, el.open);
    });
  });
}

function readStoredState(id) {
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + id);
    if (raw === null) return null;
    return raw === "1";
  } catch {
    return null;
  }
}

function writeStoredState(id, open) {
  try {
    window.localStorage.setItem(STORAGE_PREFIX + id, open ? "1" : "0");
  } catch {
    /* localStorage indisponible (mode privé) : l'état repart simplement fermé */
  }
}
