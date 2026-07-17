// ── Éditeur d'avatar : import direct, recadrage carré interactif, compression ─
// Flux : clic sur l'avatar/le bouton → sélecteur de fichiers natif OUVERT
// IMMÉDIATEMENT (input.click() programmatique, aucune étape intermédiaire) →
// une fois un fichier choisi, la modale de recadrage s'ouvre directement.
// Auto-suffisant (aucune librairie externe). Le recadrage/zoom/déplacement se
// fait en coordonnées pixel exactes, puis le rendu final est produit par une
// simple copie de rectangle sur <canvas> — la prévisualisation affichée dans
// le viewport correspond donc exactement à l'image finale enregistrée.
const $ = (id) => document.getElementById(id);

const VIEWPORT = 260; // taille (px) du cadre de recadrage circulaire affiché
const OUTPUT = 400; // taille (px) de l'avatar final (carré, cercle affiché via CSS)
const MAX_FILE_BYTES = 5 * 1024 * 1024; // 5 Mo, conforme au cahier des charges
const JPEG_QUALITY = 0.85;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

let img = null;
let naturalW = 0, naturalH = 0;
let baseScale = 1;
let zoom = 1;
let left = 0, top = 0;
let dragging = false;
let dragStart = null;
let onSaveCallback = null;
let objectUrl = null;

function clampPosition() {
  const dw = naturalW * baseScale * zoom;
  const dh = naturalH * baseScale * zoom;
  left = Math.min(0, Math.max(VIEWPORT - dw, left));
  top = Math.min(0, Math.max(VIEWPORT - dh, top));
}

function applyTransform() {
  const dw = naturalW * baseScale * zoom;
  const dh = naturalH * baseScale * zoom;
  img.style.width = `${dw}px`;
  img.style.height = `${dh}px`;
  img.style.left = `${left}px`;
  img.style.top = `${top}px`;
}

function loadImageFile(file) {
  return new Promise((resolve, reject) => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Image illisible."));
    image.src = objectUrl;
  });
}

function resetEditorState(image) {
  naturalW = image.naturalWidth;
  naturalH = image.naturalHeight;
  baseScale = Math.max(VIEWPORT / naturalW, VIEWPORT / naturalH);
  zoom = 1;
  const dw = naturalW * baseScale;
  const dh = naturalH * baseScale;
  left = (VIEWPORT - dw) / 2;
  top = (VIEWPORT - dh) / 2;
}

function renderToDataUrl() {
  const canvas = document.createElement("canvas");
  canvas.width = OUTPUT;
  canvas.height = OUTPUT;
  const ctx = canvas.getContext("2d");
  const k = OUTPUT / VIEWPORT;
  const dw = naturalW * baseScale * zoom * k;
  const dh = naturalH * baseScale * zoom * k;
  ctx.fillStyle = "#12141c";
  ctx.fillRect(0, 0, OUTPUT, OUTPUT);
  ctx.drawImage(img, left * k, top * k, dw, dh);
  return canvas.toDataURL("image/jpeg", JPEG_QUALITY);
}

function onPointerDown(e) {
  dragging = true;
  dragStart = { x: e.clientX, y: e.clientY, left, top };
  $("crop-viewport").classList.add("is-dragging");
  $("crop-viewport").setPointerCapture?.(e.pointerId);
  e.preventDefault();
}
function onPointerMove(e) {
  if (!dragging) return;
  left = dragStart.left + (e.clientX - dragStart.x);
  top = dragStart.top + (e.clientY - dragStart.y);
  clampPosition();
  applyTransform();
}
function onPointerUp() {
  dragging = false;
  $("crop-viewport").classList.remove("is-dragging");
}

// L'erreur s'affiche sur la page (pas dans la modale de recadrage : les
// validations de format/taille se produisent AVANT que la modale n'existe,
// puisque le sélecteur de fichiers s'ouvre directement au clic).
function setError(msg) {
  const el = $("avatar-page-error");
  if (!el) return;
  el.textContent = msg;
  el.hidden = !msg;
}

async function handleFile(file) {
  setError("");
  if (!ACCEPTED_TYPES.includes(file.type)) {
    setError("Formats acceptés : JPG, PNG ou WEBP.");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    setError(`Cette image dépasse 5 Mo (${(file.size / 1024 / 1024).toFixed(1)} Mo) — choisis une image plus légère.`);
    return;
  }
  try {
    img = $("crop-image");
    const image = await loadImageFile(file);
    img.src = image.src;
    resetEditorState(image);
    $("crop-zoom").value = "1";
    applyTransform();
    $("avatar-modal-overlay").hidden = false;
    $("btn-avatar-modal-save").disabled = false;
  } catch {
    setError("Impossible de lire cette image. Réessaie avec un autre fichier.");
  }
}

let wired = false;
function wireOnce() {
  if (wired) return;
  wired = true;

  $("avatar-file-input").addEventListener("change", () => {
    const file = $("avatar-file-input").files[0];
    if (file) handleFile(file);
  });

  $("crop-viewport").addEventListener("pointerdown", onPointerDown);
  window.addEventListener("pointermove", onPointerMove);
  window.addEventListener("pointerup", onPointerUp);

  $("crop-zoom").addEventListener("input", () => {
    const newZoom = Number($("crop-zoom").value);
    const dwOld = naturalW * baseScale * zoom;
    const dhOld = naturalH * baseScale * zoom;
    const fx = (VIEWPORT / 2 - left) / dwOld;
    const fy = (VIEWPORT / 2 - top) / dhOld;
    zoom = newZoom;
    const dwNew = naturalW * baseScale * zoom;
    const dhNew = naturalH * baseScale * zoom;
    left = VIEWPORT / 2 - fx * dwNew;
    top = VIEWPORT / 2 - fy * dhNew;
    clampPosition();
    applyTransform();
  });

  $("btn-avatar-modal-cancel").addEventListener("click", closeAvatarEditor);
  $("avatar-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "avatar-modal-overlay") closeAvatarEditor();
  });
  $("btn-avatar-modal-save").addEventListener("click", () => {
    if (!img || !naturalW) return;
    const dataUrl = renderToDataUrl();
    if (onSaveCallback) onSaveCallback(dataUrl);
    closeAvatarEditor();
  });
}

/** Déclenche directement le sélecteur de fichiers natif du navigateur — aucune
 * étape intermédiaire. La modale de recadrage ne s'ouvre qu'une fois un
 * fichier valide sélectionné (voir handleFile). */
export function triggerAvatarUpload({ onSave }) {
  wireOnce();
  onSaveCallback = onSave;
  setError("");
  $("avatar-file-input").value = "";
  $("avatar-file-input").click();
}

export function closeAvatarEditor() {
  $("avatar-modal-overlay").hidden = true;
}
