import { api } from "./api.js";
import { ICONS } from "./icons.js";

const $ = (id) => document.getElementById(id);

const PAGE_SIZE = 6;
const MY_REVIEWS_KEY = "novamath:my_reviews";
const ADMIN_KEY_STORAGE = "novamath:admin_key";
const MAX_AVATAR_BYTES = 200_000;

let reviews = [];
let stats = { total: 0, average: 0, distribution: {} };
let page = 1;
let searchQuery = "";
let sortMode = "recent";
let selectedRating = 0;
let avatarDataUrl = null;
let editingId = null;
let pendingDeleteId = null;
// Compte connecté (facultatif — la page d'accueil reste accessible sans compte).
// Quand présent, le serveur ignore de toute façon le nom/pseudo/photo envoyés
// par le formulaire et les remplace par ceux du compte (voir server.py::
// _validate_review_payload) : on reflète ça côté client pour ne pas laisser
// remplir des champs qui n'auront aucun effet.
let currentAccount = null;

// ── Persistance locale : quels avis m'appartiennent (id -> owner_token) ────
function getMyReviews() {
  try {
    return JSON.parse(localStorage.getItem(MY_REVIEWS_KEY)) || {};
  } catch {
    return {};
  }
}
function setMyReview(id, token) {
  const map = getMyReviews();
  map[id] = token;
  localStorage.setItem(MY_REVIEWS_KEY, JSON.stringify(map));
}
function removeMyReview(id) {
  const map = getMyReviews();
  delete map[id];
  localStorage.setItem(MY_REVIEWS_KEY, JSON.stringify(map));
}

function getAdminKey() {
  return localStorage.getItem(ADMIN_KEY_STORAGE) || null;
}
function isAdmin() {
  return !!getAdminKey();
}
function clearAdmin() {
  localStorage.removeItem(ADMIN_KEY_STORAGE);
  $("btn-admin-mode").classList.remove("is-active");
}

function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

function starsHtml(rating) {
  return Array.from({ length: 5 }, (_, i) => {
    const filled = i < rating;
    return `<span class="star-icon ${filled ? "filled" : "empty"}">${filled ? ICONS.starFilled : ICONS.star}</span>`;
  }).join("");
}

function dateValue(r) {
  const [d, m, y] = r.date.split("/").map(Number);
  return new Date(y, m - 1, d).getTime();
}

// ── Chargement / actualisation ─────────────────────────────────────────────
async function loadReviews() {
  const data = await api.getReviews(getAdminKey());
  reviews = data.reviews.map((r, i) => ({ ...r, __idx: i }));
  stats = data.stats;
  render();
}

// ── Filtrage / tri ──────────────────────────────────────────────────────────
function applyFiltersSort() {
  let list = reviews.slice();

  const q = searchQuery.trim().toLowerCase();
  if (q) {
    list = list.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.pseudo || "").toLowerCase().includes(q) ||
        r.classe.toLowerCase().includes(q) ||
        r.comment.toLowerCase().includes(q)
    );
  }

  if (["1", "2", "3", "4", "5"].includes(sortMode)) {
    const n = Number(sortMode);
    list = list.filter((r) => r.rating === n);
    list.sort((a, b) => dateValue(b) - dateValue(a) || b.__idx - a.__idx);
  } else if (sortMode === "top") {
    list.sort((a, b) => b.rating - a.rating || dateValue(b) - dateValue(a) || b.__idx - a.__idx);
  } else if (sortMode === "oldest") {
    list.sort((a, b) => dateValue(a) - dateValue(b) || a.__idx - b.__idx);
  } else {
    list.sort((a, b) => dateValue(b) - dateValue(a) || b.__idx - a.__idx);
  }

  const pinned = list.filter((r) => r.pinned);
  const rest = list.filter((r) => !r.pinned);
  return [...pinned, ...rest];
}

// ── Rendu ────────────────────────────────────────────────────────────────
function actionBtn(label, iconSvg, cls, onClick) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `btn ${cls}`;
  btn.innerHTML = `<span class="btn-icon">${iconSvg}</span>`;
  btn.append(label);
  btn.addEventListener("click", onClick);
  return btn;
}

function buildCard(review) {
  const card = document.createElement("div");
  card.className = "review-card card card--interactive" + (review.pinned ? " is-pinned" : "") + (review.hidden ? " is-hidden" : "");

  if (review.pinned) {
    const pin = document.createElement("span");
    pin.className = "review-pin-flag";
    pin.title = "Avis épinglé";
    pin.innerHTML = ICONS.pin;
    card.appendChild(pin);
  }

  const header = document.createElement("div");
  header.className = "review-header";

  let avatarEl;
  if (review.avatar && review.avatar.startsWith("data:image/")) {
    avatarEl = document.createElement("img");
    avatarEl.className = "review-avatar-img";
    avatarEl.src = review.avatar;
    avatarEl.alt = "";
  } else {
    avatarEl = document.createElement("div");
    avatarEl.className = "review-avatar";
    avatarEl.textContent = initials(review.name);
  }
  header.appendChild(avatarEl);

  const identity = document.createElement("div");
  identity.className = "review-identity";
  const nameEl = document.createElement("div");
  nameEl.className = "name";
  nameEl.append(review.name);
  if (review.pseudo) {
    const pseudoEl = document.createElement("span");
    pseudoEl.className = "pseudo";
    pseudoEl.textContent = `@${review.pseudo}`;
    nameEl.appendChild(pseudoEl);
  }
  identity.appendChild(nameEl);
  const metaEl = document.createElement("div");
  metaEl.className = "meta";
  metaEl.textContent = `${review.classe} · ${review.date}${review.hidden ? " · masqué" : ""}`;
  identity.appendChild(metaEl);
  header.appendChild(identity);
  card.appendChild(header);

  const starsEl = document.createElement("div");
  starsEl.className = "review-stars";
  starsEl.innerHTML = starsHtml(review.rating);
  card.appendChild(starsEl);

  const comment = document.createElement("p");
  comment.className = "review-comment";
  comment.textContent = review.comment;
  card.appendChild(comment);

  const myToken = getMyReviews()[review.id];
  const admin = isAdmin();
  if (myToken || admin) {
    const actions = document.createElement("div");
    actions.className = "review-actions";
    actions.appendChild(actionBtn("Modifier", ICONS.penSquare, "btn-secondary", () => openEditModal(review)));
    actions.appendChild(actionBtn("Supprimer", ICONS.trash, "btn-danger-outline", () => askDelete(review.id)));
    if (admin) {
      actions.appendChild(actionBtn(review.pinned ? "Désépingler" : "Épingler", ICONS.pin, "btn-ghost", () => togglePin(review.id)));
      actions.appendChild(actionBtn(review.hidden ? "Afficher" : "Masquer", ICONS.eyeOff, "btn-ghost", () => toggleHide(review.id)));
    }
    card.appendChild(actions);
  }

  return card;
}

function renderSummary() {
  const el = $("reviews-summary");
  el.innerHTML = "";
  if (!stats.total) {
    const p = document.createElement("p");
    p.style.color = "var(--text-muted)";
    p.textContent = "Aucun avis pour l'instant — sois le premier à donner ton avis !";
    el.appendChild(p);
    return;
  }

  const scoreBlock = document.createElement("div");
  scoreBlock.className = "reviews-summary-score";
  scoreBlock.innerHTML = `
    <div class="value tabular">${stats.average.toFixed(1)}</div>
    <div class="stars">${starsHtml(Math.round(stats.average))}</div>
    <div class="count">${stats.total} avis</div>
  `;
  el.appendChild(scoreBlock);

  const bars = document.createElement("div");
  bars.className = "reviews-summary-bars";
  for (let n = 5; n >= 1; n--) {
    const pct = stats.distribution[String(n)] || 0;
    const row = document.createElement("div");
    row.className = "reviews-summary-bar";
    row.innerHTML = `<span class="label">${n} <span class="reviews-star-icon">${ICONS.starFilled}</span></span><div class="track"><div class="fill" style="width:${pct}%"></div></div><span class="pct">${pct}%</span>`;
    bars.appendChild(row);
  }
  el.appendChild(bars);
}

function renderPagination(total, shown) {
  const el = $("reviews-pagination");
  el.innerHTML = "";
  if (shown < total) {
    const btn = document.createElement("button");
    btn.className = "btn btn-secondary";
    btn.textContent = `Charger plus d'avis (${total - shown} restants)`;
    btn.addEventListener("click", () => {
      page += 1;
      render();
    });
    el.appendChild(btn);
  }
}

function render() {
  renderSummary();
  const filtered = applyFiltersSort();
  const grid = $("reviews-grid");
  grid.innerHTML = "";
  const slice = filtered.slice(0, page * PAGE_SIZE);
  slice.forEach((r) => grid.appendChild(buildCard(r)));
  $("reviews-empty").hidden = filtered.length > 0;
  grid.hidden = filtered.length === 0;
  renderPagination(filtered.length, slice.length);
}

// ── Modale d'ajout / modification ──────────────────────────────────────────
function resetForm() {
  editingId = null;
  selectedRating = 0;
  avatarDataUrl = null;
  $("review-form").reset();
  $("review-form").hidden = false;
  $("review-success").hidden = true;
  $("review-modal-title").textContent = "Donner mon avis";
  $("btn-review-submit").textContent = "Publier mon avis";
  $("avatar-preview").innerHTML = "";
  $("btn-avatar-remove").hidden = true;
  $("comment-count").textContent = "0";
  updateStarButtons();
  clearFormErrors();
  applyAccountLock();
}

/** Si un compte est connecté, préremplit et verrouille nom/pseudo/photo avec
 * l'identité du compte (le serveur les impose de toute façon) et masque les
 * champs devenus inutiles. */
function applyAccountLock() {
  const hint = $("review-account-hint");
  if (!currentAccount) {
    $("review-identity-row").hidden = false;
    $("review-avatar-field").hidden = false;
    hint.hidden = true;
    return;
  }
  $("review-name").value = currentAccount.pseudo || "";
  $("review-pseudo").value = currentAccount.username || "";
  avatarDataUrl = currentAccount.avatar || null;
  $("review-identity-row").hidden = true;
  $("review-avatar-field").hidden = true;
  hint.hidden = false;
  hint.textContent = `Publié en tant que ${currentAccount.pseudo} (@${currentAccount.username}).`;
  updateAvatarPreview(currentAccount.pseudo);
}

function updateStarButtons({ preview = 0 } = {}) {
  document.querySelectorAll(".star-btn").forEach((btn) => {
    const v = Number(btn.dataset.value);
    const active = v <= (preview || selectedRating);
    btn.classList.toggle("is-active", v <= selectedRating);
    btn.classList.toggle("is-preview", preview > 0 && v <= preview);
    btn.innerHTML = active ? ICONS.starFilled : ICONS.star;
    btn.setAttribute("aria-checked", String(v === selectedRating));
  });
}

function updateAvatarPreview(name) {
  const preview = $("avatar-preview");
  preview.innerHTML = "";
  if (avatarDataUrl) {
    const img = document.createElement("img");
    img.src = avatarDataUrl;
    img.alt = "";
    preview.appendChild(img);
    $("btn-avatar-remove").hidden = false;
  } else {
    preview.textContent = initials(name || $("review-name").value);
    $("btn-avatar-remove").hidden = true;
  }
}

function clearFormErrors() {
  ["error-name", "error-rating", "error-comment", "error-global"].forEach((id) => {
    $(id).hidden = true;
  });
  document.querySelectorAll(".form-field").forEach((f) => f.classList.remove("has-error"));
}

// ── Mode invité : publier un avis nécessite un compte (voir server.py::
// api_reviews, qui refuse aussi côté serveur) — on évite d'ouvrir un
// formulaire que la sauvegarde rejettera de toute façon. ───────────────────
function ensureGuestReviewModal() {
  if (document.getElementById("guest-review-modal-overlay")) return;
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "guest-review-modal-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <div class="modal-card card">
      <h3>Créez votre compte pour continuer</h3>
      <p>Vous utilisez actuellement Mathadap en mode invité.</p>
      <p>Publier un avis nécessite un compte — créez-en un gratuitement pour partager votre expérience.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-review-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.hidden = true; });
  overlay.querySelector("#btn-guest-review-dismiss").addEventListener("click", () => { overlay.hidden = true; });
  overlay.querySelectorAll(".js-open-signup, .js-open-login").forEach((btn) => {
    btn.addEventListener("click", () => { overlay.hidden = true; });
  });
}

function openAddModal() {
  if (currentAccount?.is_guest) {
    ensureGuestReviewModal();
    document.getElementById("guest-review-modal-overlay").hidden = false;
    return;
  }
  resetForm();
  updateAvatarPreview("");
  $("review-modal-overlay").hidden = false;
  $("review-name").focus();
}

function openEditModal(review) {
  resetForm();
  editingId = review.id;
  $("review-modal-title").textContent = "Modifier mon avis";
  $("btn-review-submit").textContent = "Enregistrer les modifications";
  $("review-name").value = review.name;
  $("review-pseudo").value = review.pseudo || "";
  $("review-classe").value = review.classe;
  $("review-comment").value = review.comment;
  $("comment-count").textContent = String(review.comment.length);
  selectedRating = review.rating;
  avatarDataUrl = review.avatar || null;
  updateStarButtons();
  updateAvatarPreview(review.name);
  $("review-modal-overlay").hidden = false;
  $("review-name").focus();
}

function closeModal() {
  $("review-modal-overlay").hidden = true;
}

function validateClientSide() {
  clearFormErrors();
  let ok = true;
  const name = $("review-name").value.trim();
  const comment = $("review-comment").value.trim();

  if (!name) {
    $("error-name").hidden = false;
    $("review-name").closest(".form-field").classList.add("has-error");
    ok = false;
  }
  if (!selectedRating) {
    $("error-rating").hidden = false;
    ok = false;
  }
  if (!comment) {
    $("error-comment").hidden = false;
    $("review-comment").closest(".form-field").classList.add("has-error");
    ok = false;
  }
  return ok;
}

async function handleSubmit(e) {
  e.preventDefault();
  if (!validateClientSide()) return;

  const payload = {
    name: $("review-name").value.trim(),
    pseudo: $("review-pseudo").value.trim(),
    classe: $("review-classe").value,
    rating: selectedRating,
    comment: $("review-comment").value.trim(),
    avatar: avatarDataUrl,
  };

  const submitBtn = $("btn-review-submit");
  submitBtn.disabled = true;
  try {
    if (editingId) {
      const myToken = getMyReviews()[editingId];
      const adminKey = isAdmin() ? getAdminKey() : null;
      await api.updateReview(editingId, { ...payload, owner_token: myToken }, adminKey);
    } else {
      const res = await api.createReview(payload);
      setMyReview(res.review.id, res.review.owner_token);
    }
    await loadReviews();
    $("review-form").hidden = true;
    $("review-success").hidden = false;
    setTimeout(() => {
      closeModal();
    }, 1400);
  } catch (err) {
    $("error-global").textContent = err.message || "Une erreur est survenue.";
    $("error-global").hidden = false;
  } finally {
    submitBtn.disabled = false;
  }
}

// ── Suppression ──────────────────────────────────────────────────────────
function askDelete(id) {
  pendingDeleteId = id;
  $("review-delete-modal-overlay").hidden = false;
}

async function confirmDelete() {
  if (!pendingDeleteId) return;
  const id = pendingDeleteId;
  const myToken = getMyReviews()[id];
  const adminKey = isAdmin() ? getAdminKey() : null;
  try {
    await api.deleteReview(id, myToken, adminKey);
    removeMyReview(id);
    await loadReviews();
  } catch (err) {
    alert(err.message || "Suppression impossible.");
  }
  pendingDeleteId = null;
  $("review-delete-modal-overlay").hidden = true;
}

// ── Administration ──────────────────────────────────────────────────────
async function togglePin(id) {
  try {
    await api.pinReview(id, getAdminKey());
    await loadReviews();
  } catch (err) {
    handleAdminError(err);
  }
}
async function toggleHide(id) {
  try {
    await api.hideReview(id, getAdminKey());
    await loadReviews();
  } catch (err) {
    handleAdminError(err);
  }
}
function handleAdminError(err) {
  if (err.status === 403) {
    clearAdmin();
    alert("Clé administrateur invalide — mode administrateur désactivé.");
    loadReviews();
  } else {
    alert(err.message || "Action impossible.");
  }
}

async function activateAdmin() {
  const key = $("admin-key-input").value.trim();
  $("error-admin").hidden = true;
  if (!key) {
    $("error-admin").hidden = false;
    return;
  }
  localStorage.setItem(ADMIN_KEY_STORAGE, key);
  try {
    await loadReviews();
    $("btn-admin-mode").classList.add("is-active");
    $("admin-modal-overlay").hidden = true;
    $("admin-key-input").value = "";
  } catch {
    clearAdmin();
    $("error-admin").hidden = false;
  }
}

// ── Initialisation ──────────────────────────────────────────────────────
export function initReviews() {
  if (!$("reviews-grid")) return;
  if (isAdmin()) $("btn-admin-mode").classList.add("is-active");

  loadReviews().catch(() => {
    $("reviews-summary").innerHTML = `<p style="color:var(--text-muted);">Impossible de charger les avis pour le moment.</p>`;
  });

  // La page d'accueil reste publique : un visiteur non connecté peut toujours
  // publier un avis (échec silencieux de /api/auth/me, currentAccount reste null).
  api.me().then(({ user }) => { currentAccount = user; }).catch(() => {});

  $("btn-add-review").addEventListener("click", openAddModal);
  $("btn-review-cancel").addEventListener("click", closeModal);
  $("review-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "review-modal-overlay") closeModal();
  });
  $("review-form").addEventListener("submit", handleSubmit);

  $("review-comment").addEventListener("input", () => {
    $("comment-count").textContent = String($("review-comment").value.length);
  });

  document.querySelectorAll(".star-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedRating = Number(btn.dataset.value);
      updateStarButtons();
      $("error-rating").hidden = true;
    });
    btn.addEventListener("mouseenter", () => updateStarButtons({ preview: Number(btn.dataset.value) }));
    btn.addEventListener("focus", () => updateStarButtons({ preview: Number(btn.dataset.value) }));
  });
  $("star-input").addEventListener("mouseleave", () => updateStarButtons());
  $("star-input").addEventListener("focusout", () => updateStarButtons());
  $("star-input").addEventListener("keydown", (e) => {
    if (!["ArrowRight", "ArrowLeft"].includes(e.key)) return;
    e.preventDefault();
    selectedRating = Math.min(5, Math.max(1, selectedRating + (e.key === "ArrowRight" ? 1 : -1)));
    updateStarButtons();
    document.querySelector(`.star-btn[data-value="${selectedRating}"]`)?.focus();
    $("error-rating").hidden = true;
  });

  $("review-avatar-input").addEventListener("change", () => {
    const file = $("review-avatar-input").files[0];
    if (!file) return;
    if (file.size > MAX_AVATAR_BYTES) {
      $("error-global").textContent = "Cette image est trop volumineuse (200 Ko maximum).";
      $("error-global").hidden = false;
      $("review-avatar-input").value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      avatarDataUrl = reader.result;
      updateAvatarPreview($("review-name").value);
    };
    reader.readAsDataURL(file);
  });
  $("btn-avatar-remove").addEventListener("click", () => {
    avatarDataUrl = null;
    $("review-avatar-input").value = "";
    updateAvatarPreview($("review-name").value);
  });
  $("review-name").addEventListener("input", () => {
    if (!avatarDataUrl) updateAvatarPreview($("review-name").value);
  });

  $("review-delete-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "review-delete-modal-overlay") {
      $("review-delete-modal-overlay").hidden = true;
      pendingDeleteId = null;
    }
  });
  $("btn-review-delete-cancel").addEventListener("click", () => {
    $("review-delete-modal-overlay").hidden = true;
    pendingDeleteId = null;
  });
  $("btn-review-delete-confirm").addEventListener("click", confirmDelete);

  $("reviews-search-input").addEventListener("input", (e) => {
    searchQuery = e.target.value;
    page = 1;
    render();
  });
  $("reviews-sort").addEventListener("change", (e) => {
    sortMode = e.target.value;
    page = 1;
    render();
  });

  $("btn-admin-mode").addEventListener("click", () => {
    if (isAdmin()) {
      clearAdmin();
      loadReviews();
    } else {
      $("admin-modal-overlay").hidden = false;
      $("admin-key-input").focus();
    }
  });
  $("btn-admin-cancel").addEventListener("click", () => {
    $("admin-modal-overlay").hidden = true;
  });
  $("admin-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "admin-modal-overlay") $("admin-modal-overlay").hidden = true;
  });
  $("btn-admin-confirm").addEventListener("click", activateAdmin);
  $("admin-key-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") activateAdmin();
  });
}

initReviews();
