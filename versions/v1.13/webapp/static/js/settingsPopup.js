// ── Ouverture des Paramètres en popup (remplace l'ancienne page settings.html) ─
import { openPopup } from "./popup.js";
import { mountSettingsPanel } from "./settings.js";
import { t } from "./i18n.js";

const PANEL_TEMPLATE = `
  <nav class="settings-menu" id="settings-menu" aria-label="Catégories de paramètres"></nav>
  <div class="settings-panel" id="settings-panel"></div>

  <div class="modal-overlay" id="confirm-modal-overlay" hidden>
    <div class="modal-card card">
      <h3 id="confirm-modal-title">Confirmer l'action</h3>
      <p id="confirm-modal-text"></p>
      <div id="confirm-modal-extra"></div>
      <span class="form-error form-error--global" id="confirm-modal-error" hidden></span>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-danger-outline" id="confirm-modal-confirm">Confirmer</button>
        <button type="button" class="btn btn-ghost" id="confirm-modal-cancel">Annuler</button>
      </div>
    </div>
  </div>

  <div class="toast" id="settings-toast" hidden></div>
`;

let activeHandle = null;

export function openSettingsPopup() {
  if (activeHandle) return activeHandle;

  const body = document.createElement("div");
  body.className = "settings-shell";
  body.innerHTML = PANEL_TEMPLATE;

  const handle = openPopup({
    id: "settings-popup-overlay",
    title: t("settings.title"),
    bodyEl: body,
    size: "xl",
    onClose: () => { activeHandle = null; },
  });
  activeHandle = handle;
  mountSettingsPanel(body);
  return handle;
}

export function bindSettingsButton(buttonEl) {
  if (!buttonEl) return;
  buttonEl.addEventListener("click", () => openSettingsPopup());
}
