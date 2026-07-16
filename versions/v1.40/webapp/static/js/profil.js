import { initSettingsManager, onSettingsChange } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { getAccentColor, getAccentColorSecondary, accentRgba } from "./theme.js";
import {
  getState, hydrateFromServer, computeStreak,
  masteryByChapter, levelFromXp, badgeDefs,
} from "./store.js";
import { getChapterTitles, buildSeriesRow } from "./seriesview.js";
import { api } from "./api.js";
import { bindLiveTranslations } from "./i18n.js";
import { badgeIconSvg } from "./badgeIcons.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 10;

let historyPage = 0;
let chapterTitles = {};
let chaptersMeta = [];
let currentUser = null;

function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

function formatDuration(seconds) {
  if (!seconds) return "0 min";
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.round(seconds / 60);
  return `${minutes} min`;
}

function formatDateFR(isoString) {
  const d = new Date(isoString);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

function renderAvatar(container, user) {
  container.innerHTML = "";
  if (user.avatar) {
    const img = document.createElement("img");
    img.src = user.avatar;
    img.alt = "";
    container.appendChild(img);
  } else {
    container.textContent = initials(user.pseudo);
  }
}

function renderAccount(user) {
  currentUser = user;
  $("profile-name").textContent = user.pseudo || "Élève";
  renderAvatar($("profile-avatar"), user);
  $("profile-pseudo-chip").hidden = true;
  $("profile-username-badge").textContent = `@${user.username}`;
  $("profile-email-badge").textContent = user.email;
  $("profile-joined-badge").lastChild.textContent = ` Inscrit le ${formatDateFR(user.created_at)}`;

  // Mode invité : ni personnalisation, ni suppression d'un "compte" qui
  // n'existe que temporairement — remplacé par une invitation à créer un
  // vrai compte. La photo générique/le nom "Invité" s'affichent déjà
  // naturellement (valeurs par défaut du compte invité côté serveur).
  $("profile-subtitle").textContent = user.is_guest ? "Mode invité" : "Élève NovaMath";
  $("btn-delete-account").hidden = user.is_guest;
  let hint = $("profile-guest-hint");
  if (user.is_guest) {
    if (!hint) {
      hint = document.createElement("p");
      hint.id = "profile-guest-hint";
      hint.className = "auth-next-hint";
      hint.textContent = "Crée un compte pour sauvegarder ta progression et débloquer toutes les fonctionnalités.";
      document.querySelector(".profile-header-actions").insertAdjacentElement("afterend", hint);
    }
  } else if (hint) {
    hint.remove();
  }
}

function render(state) {
  const { level, progress } = levelFromXp(state.xp);
  $("profile-level-label").textContent = `Niveau ${level}`;
  $("profile-level-badge").textContent = `Niveau ${level}`;
  $("profile-xp-label").textContent = `${state.xp} XP`;
  $("profile-level-fill").style.width = `${Math.round(progress * 100)}%`;

  const total = state.history.length;
  const correct = state.history.filter((h) => h.correct).length;
  const totalSeconds = state.history.reduce((sum, h) => sum + (h.duration_s || 0), 0);
  $("stat-time").textContent = formatDuration(totalSeconds);
  $("stat-count").textContent = total;
  $("stat-rate").textContent = total ? `${Math.round((correct / total) * 100)}%` : "0%";
  $("stat-streak").textContent = computeStreak(state.history);
  $("stat-series").textContent = (state.series || []).length;
  $("stat-progress").textContent = `${globalProgressPct(state.history)}%`;

  renderAccuracyChart(state.series || []);
  renderDonut(total, correct);
  renderRadar(state.history);
  renderBadges(state.badges);
  renderHeatmap(state.history);
  renderSeriesPage(state.series || []);
}

function globalProgressPct(history) {
  if (!chaptersMeta.length) return 0;
  const attempted = {};
  history.forEach((h) => {
    if (h.id == null) return;
    attempted[h.chapter] = attempted[h.chapter] || new Set();
    attempted[h.chapter].add(h.id);
  });
  const ratios = chaptersMeta.map((c) => (c.n_exercises ? Math.min(1, (attempted[c.id]?.size || 0) / c.n_exercises) : 0));
  if (!ratios.length) return 0;
  return Math.round((ratios.reduce((a, b) => a + b, 0) / ratios.length) * 100);
}

// ── Graphique accuracy (par série terminée) ─────────────────────────────────
function renderAccuracyChart(series) {
  const svg = $("accuracy-chart");
  if (!series.length) {
    svg.innerHTML = "";
    svg.parentElement.querySelector(".accuracy-empty")?.remove();
    const p = document.createElement("p");
    p.className = "accuracy-empty";
    p.textContent = "Termine une série pour voir ton évolution.";
    svg.after(p);
    return;
  }
  svg.parentElement.querySelector(".accuracy-empty")?.remove();

  const W = 300, H = 140, PAD = 12;
  const pts = series.slice(-20);
  const stepX = pts.length > 1 ? (W - PAD * 2) / (pts.length - 1) : 0;
  const coords = pts.map((s, i) => {
    const x = PAD + i * stepX;
    const y = H - PAD - (s.accuracy / 100) * (H - PAD * 2);
    return [x, y];
  });

  const line = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(1)},${H - PAD} L${coords[0][0].toFixed(1)},${H - PAD} Z`;

  const accent = getAccentColorSecondary();
  const dots = coords
    .map(([x, y], i) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3" fill="${accent}"><title>${pts[i].accuracy}%</title></circle>`)
    .join("");

  svg.innerHTML = `
    <defs>
      <linearGradient id="accuracy-fill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${accent}" stop-opacity="0.35"/>
        <stop offset="1" stop-color="${accent}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path d="${area}" fill="url(#accuracy-fill)"/>
    <path d="${line}" fill="none" stroke="url(#accuracy-fill)" style="stroke:${accent}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    ${dots}
  `;
}

// ── Donut répartition bonnes / mauvaises réponses ──────────────────────────
function renderDonut(total, correct) {
  const svg = $("donut-chart");
  const legend = $("donut-legend");
  const wrong = total - correct;
  const pctCorrect = total ? Math.round((correct / total) * 100) : 0;

  if (!total) {
    svg.innerHTML = `<circle cx="60" cy="60" r="48" fill="none" stroke="var(--border)" stroke-width="14"/>`;
    legend.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">Aucune donnée pour l'instant.</p>`;
    return;
  }

  const r = 48, c = 2 * Math.PI * r;
  const correctLen = (pctCorrect / 100) * c;
  svg.innerHTML = `
    <circle cx="60" cy="60" r="${r}" fill="none" stroke="var(--surface-hover)" stroke-width="14"/>
    <circle cx="60" cy="60" r="${r}" fill="none" stroke="#22c55e" stroke-width="14"
      stroke-dasharray="${correctLen.toFixed(1)} ${c.toFixed(1)}" stroke-linecap="round"
      transform="rotate(-90 60 60)"/>
    <text x="60" y="65" text-anchor="middle" font-size="20" font-weight="700" fill="var(--text)">${pctCorrect}%</text>
  `;
  legend.innerHTML = `
    <div class="donut-legend-item"><span class="donut-legend-dot" style="background:#22c55e;"></span>Bonnes réponses <span class="donut-legend-value">${correct}</span></div>
    <div class="donut-legend-item"><span class="donut-legend-dot" style="background:var(--surface-hover); border:1px solid var(--border-strong);"></span>Mauvaises réponses <span class="donut-legend-value">${wrong}</span></div>
  `;
}

function renderRadar(history) {
  const svg = $("radar-chart");
  const mastery = masteryByChapter(history);
  const chapters = Object.keys(mastery).sort();
  if (!chapters.length) {
    svg.innerHTML = `<text x="150" y="130" text-anchor="middle" fill="var(--text-faint)" font-size="13">Fais des exercices pour voir ton radar</text>`;
    return;
  }
  const cx = 150, cy = 130, maxR = 100;
  const n = chapters.length;
  const angleFor = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;

  let rings = "";
  [0.25, 0.5, 0.75, 1].forEach((f) => {
    const pts = chapters.map((_, i) => {
      const a = angleFor(i);
      return `${(cx + Math.cos(a) * maxR * f).toFixed(1)},${(cy + Math.sin(a) * maxR * f).toFixed(1)}`;
    });
    rings += `<polygon points="${pts.join(" ")}" fill="none" stroke="var(--border)" stroke-width="1"/>`;
  });

  const dataPts = chapters.map((ch, i) => {
    const a = angleFor(i);
    const r = mastery[ch].rate * maxR;
    return `${(cx + Math.cos(a) * r).toFixed(1)},${(cy + Math.sin(a) * r).toFixed(1)}`;
  });

  const labels = chapters.map((ch, i) => {
    const a = angleFor(i);
    const lx = cx + Math.cos(a) * (maxR + 18);
    const ly = cy + Math.sin(a) * (maxR + 18);
    return `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="9" fill="var(--text-muted)">${ch.replace("Chapitre_", "C")}</text>`;
  });

  svg.innerHTML = `
    ${rings}
    <polygon points="${dataPts.join(" ")}" fill="${accentRgba(0.28)}" stroke="${getAccentColorSecondary()}" stroke-width="2"/>
    ${labels.join("")}
  `;
}

function renderBadges(unlocked) {
  const grid = $("badges-grid");
  const unlockedSet = new Set(unlocked);
  grid.innerHTML = badgeDefs().map((b) => `
    <div class="badge-tile${unlockedSet.has(b.id) ? " unlocked" : ""}">
      <div class="icon">${badgeIconSvg(b.id)}</div>
      <div class="name">${b.label}</div>
    </div>
  `).join("");
}

function renderHeatmap(history) {
  const grid = $("heatmap-grid");
  const counts = {};
  history.forEach((h) => { counts[h.date] = (counts[h.date] || 0) + 1; });

  const days = [];
  for (let i = 181; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  grid.innerHTML = days.map((day) => {
    const c = counts[day] || 0;
    const level = c === 0 ? 0 : c === 1 ? 1 : c <= 3 ? 2 : c <= 5 ? 3 : 4;
    return `<div class="heatmap-cell" data-level="${level}" title="${day} : ${c} exercice(s)"></div>`;
  }).join("");
}

function renderSeriesPage(series) {
  const sorted = [...series].reverse();
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  historyPage = Math.min(historyPage, totalPages - 1);
  const slice = sorted.slice(historyPage * PAGE_SIZE, (historyPage + 1) * PAGE_SIZE);

  const body = $("full-history-body");
  body.innerHTML = "";

  if (!slice.length) {
    body.innerHTML = `<tr><td colspan="11" style="color:var(--text-muted);">Aucune série terminée pour l'instant.</td></tr>`;
  } else {
    slice.forEach((s) => body.appendChild(buildSeriesRow(s, chapterTitles, { withRestart: true })));
  }

  $("btn-prev-page").disabled = historyPage === 0;
  $("btn-next-page").disabled = historyPage >= totalPages - 1;
}

$("btn-prev-page").addEventListener("click", () => {
  historyPage = Math.max(0, historyPage - 1);
  renderSeriesPage(getState().series || []);
});
$("btn-next-page").addEventListener("click", () => {
  historyPage += 1;
  renderSeriesPage(getState().series || []);
});

// Le profil est désormais une page de consultation uniquement — toute
// modification (pseudo, avatar, informations personnelles) se fait dans
// Paramètres → Compte, seule source de vérité pour éviter tout doublon.
// `novamath:account-updated` reste écouté ici (identity.js/settings.js
// peuvent le déclencher) pour garder le pseudo/avatar affichés à jour.
window.addEventListener("novamath:account-updated", (e) => renderAccount(e.detail));

// ── Déconnexion ──────────────────────────────────────────────────────────────
$("btn-logout").addEventListener("click", () => { $("logout-modal-overlay").hidden = false; });
$("btn-logout-cancel").addEventListener("click", () => { $("logout-modal-overlay").hidden = true; });
$("logout-modal-overlay").addEventListener("click", (e) => {
  if (e.target.id === "logout-modal-overlay") $("logout-modal-overlay").hidden = true;
});
$("btn-logout-confirm").addEventListener("click", async () => {
  try {
    await api.logout();
  } finally {
    window.location.href = "/";
  }
});

// ── Suppression de compte ────────────────────────────────────────────────────
$("btn-delete-account").addEventListener("click", () => {
  $("delete-account-form").reset();
  $("btn-delete-account-confirm").disabled = true;
  $("error-delete-account-password").hidden = true;
  $("error-delete-account-global").hidden = true;
  // Un compte relié uniquement à un fournisseur OAuth n'a pas de mot de passe
  // NovaMath — dans ce cas, la case à cocher suffit comme confirmation.
  $("delete-account-password-field").hidden = currentUser?.auth_provider !== "local";
  $("delete-account-modal-overlay").hidden = false;
});
$("btn-delete-account-cancel").addEventListener("click", () => { $("delete-account-modal-overlay").hidden = true; });
$("delete-account-modal-overlay").addEventListener("click", (e) => {
  if (e.target.id === "delete-account-modal-overlay") $("delete-account-modal-overlay").hidden = true;
});
$("delete-account-ack").addEventListener("change", () => {
  $("btn-delete-account-confirm").disabled = !$("delete-account-ack").checked;
});
$("btn-toggle-delete-password").addEventListener("click", () => {
  const input = $("delete-account-password");
  input.type = input.type === "password" ? "text" : "password";
});
$("delete-account-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!$("delete-account-ack").checked) return;
  $("error-delete-account-password").hidden = true;
  $("error-delete-account-global").hidden = true;
  $("btn-delete-account-confirm").disabled = true;
  try {
    await api.deleteMe({ password: $("delete-account-password").value, confirm: true });
    window.location.href = "/";
  } catch (err) {
    if (err.field === "password") {
      $("error-delete-account-password").hidden = false;
    } else {
      $("error-delete-account-global").textContent = err.message || "Suppression impossible.";
      $("error-delete-account-global").hidden = false;
    }
    $("btn-delete-account-confirm").disabled = false;
  }
});

async function init() {
  const { user } = await api.me();
  renderAccount(user);

  chapterTitles = await getChapterTitles();
  try {
    const data = await api.chapters();
    chaptersMeta = data.chapters_meta || [];
  } catch {
    chaptersMeta = [];
  }
  render(getState());
  const fresh = await hydrateFromServer();
  render(fresh);

  onSettingsChange((e) => {
    if (e.detail.category !== "appearance" && e.detail.category !== "*") return;
    render(getState());
  });
}

init();
