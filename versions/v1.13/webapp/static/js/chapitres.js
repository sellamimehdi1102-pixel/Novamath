import { api } from "./api.js";
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { getState, masteryByChapter, masteryByNotion, coverageByChapter, coverageByNotion, getInProgressSeries } from "./store.js";
import { renderResumeCard } from "./resume.js";
import { icon } from "./icons.js";
import { bindLiveTranslations } from "./i18n.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));
renderResumeCard(document.getElementById("resume-card"));

const DIFF_LABEL = { 1: "Facile", 2: "Moyen", 3: "Confirmé", 4: "Difficile", 5: "Expert" };
const DIFF_BADGE = { 1: "badge--success", 2: "badge--success", 3: "badge--warning", 4: "badge--danger", 5: "badge--danger" };

const selected = new Set();
const grid = document.getElementById("chapters-grid");
const selectionBar = document.getElementById("selection-bar");
const selectionCount = document.getElementById("selection-count");

// ── Mode invité : limité à 2 chapitres sélectionnés ─────────────────────────
const GUEST_MAX_CHAPTERS = 2;
let isGuest = false;
api.me().then(({ user }) => { isGuest = !!user.is_guest; }).catch(() => {});

function ensureGuestChaptersModal() {
  if (document.getElementById("guest-chapters-modal-overlay")) return;
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "guest-chapters-modal-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <div class="modal-card card">
      <h3>Débloquez tous les chapitres</h3>
      <p>Créez gratuitement votre compte NovaMath afin d'accéder à tous les chapitres, sauvegarder votre progression et retrouver vos statistiques sur tous vos appareils.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-chapters-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.hidden = true; });
  overlay.querySelector("#btn-guest-chapters-dismiss").addEventListener("click", () => { overlay.hidden = true; });
  overlay.querySelectorAll(".js-open-signup, .js-open-login").forEach((btn) => {
    btn.addEventListener("click", () => { overlay.hidden = true; });
  });
}

function showGuestChaptersLimitModal() {
  ensureGuestChaptersModal();
  document.getElementById("guest-chapters-modal-overlay").hidden = false;
}

function formatDate(ts) {
  if (!ts) return "jamais";
  const diffDays = Math.floor((Date.now() - ts) / 86400000);
  if (diffDays <= 0) return "aujourd'hui";
  if (diffDays === 1) return "hier";
  return `il y a ${diffDays} j`;
}

function chapterIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>`;
}

function masteryLabel(coveragePct, accuracyPct, count) {
  if (count === 0) return { text: "À faire", cls: "badge--neutral" };
  if (coveragePct >= 70 && accuracyPct >= 70) return { text: "Maîtrisé", cls: "badge--success" };
  if (coveragePct >= 30 || accuracyPct >= 50) return { text: "En progrès", cls: "badge--warning" };
  return { text: "À renforcer", cls: "badge--danger" };
}

function renderChapters(chaptersMeta) {
  const state = getState();
  const chapterCoverage = coverageByChapter(state.history);
  const chapterMastery = masteryByChapter(state.history);
  const notionCoverage = coverageByNotion(state.history);
  const notionMastery = masteryByNotion(state.history);
  const inProgress = getInProgressSeries();

  grid.innerHTML = "";
  chaptersMeta.forEach((ch) => {
    const coveredIds = chapterCoverage[ch.id] || new Set();
    const progressPct = ch.n_exercises ? Math.round((coveredIds.size / ch.n_exercises) * 100) : 0;
    const accuracyPct = Math.round((chapterMastery[ch.id]?.rate || 0) * 100);
    const remaining = Math.max(0, ch.n_exercises - coveredIds.size);
    const estMinutes = remaining * 3;

    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;

    const notionsHtml = ch.notions_detail
      .map((n) => {
        const key = `${ch.id}|${n.notion}`;
        const covered = (notionCoverage[key] || new Set()).size;
        const nCoveragePct = n.n_exercises ? Math.round((covered / n.n_exercises) * 100) : 0;
        const nm = notionMastery[key] || { count: 0, rate: 0, last: null };
        const nAccuracyPct = Math.round(nm.rate * 100);
        const mastery = masteryLabel(nCoveragePct, nAccuracyPct, nm.count);
        const isResumable = inProgress
          && inProgress.seriesConfig?.chapterId === ch.id
          && inProgress.seriesConfig?.notion === n.notion;
        return `
        <div class="notion-row${isResumable ? " notion-row--resumable" : ""}" data-chapter="${ch.id}" data-notion="${n.notion.replace(/"/g, "&quot;")}" data-ids="${n.exercise_ids.join(",")}" data-resumable="${isResumable}">
          <div class="notion-row-top">
            <span>${n.notion}</span>
            <span class="badge ${DIFF_BADGE[n.difficulty_dominant]}">${DIFF_LABEL[n.difficulty_dominant]}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${nCoveragePct}%"></div></div>
          <div class="notion-meta">
            <span>${nm.count}/${n.n_exercises} exercices faits · Accuracy ${nAccuracyPct}% · Temps moyen ${avgDuration(state.history, ch.id, n.notion)}</span>
            <span>Dernier entraînement : ${formatDate(nm.last)}</span>
          </div>
          <div class="notion-meta">
            <span>Difficultés : ${(n.difficulties_available || []).join(", ")}${n.n_natural_variants ? ` · ${n.n_natural_variants} variantes` : ""}</span>
          </div>
          <div class="notion-meta" style="margin-top:6px;">
            <span class="badge ${mastery.cls}">${mastery.text}</span>
            <button class="btn btn-ghost btn-sm notion-action-btn" type="button">
              ${isResumable ? `${icon("play")} Reprendre` : "Commencer"}
            </button>
          </div>
        </div>`;
      })
      .join("");

    card.innerHTML = `
      <div class="chapter-card-top">
        <div class="chapter-icon">${chapterIcon()}</div>
        <div class="chapter-select-dot"></div>
      </div>
      <h3>${ch.title}</h3>
      <div class="chapter-id">${ch.id.replace("_", " ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Progression</span><span>${progressPct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${progressPct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>⏱ ~${estMinutes} min restantes</span>
        <span>📝 ${ch.n_exercises} exercices</span>
        <span>📚 ${ch.n_notions} notions</span>
      </div>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <span class="badge ${DIFF_BADGE[ch.difficulty_dominant]}">${DIFF_LABEL[ch.difficulty_dominant]} dominant</span>
        <span class="badge badge--neutral">Réussite ${accuracyPct}%</span>
      </div>
      <button class="chapter-expand-btn" type="button">
        Voir les notions
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <div class="notions-panel">${notionsHtml}</div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.closest(".chapter-expand-btn") || e.target.closest(".notion-row")) return;
      toggleSelection(ch.id, card);
    });
    card.querySelector(".chapter-expand-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      const wasOpen = card.classList.contains("expanded");
      // Effet accordéon : un seul chapitre ouvert à la fois sur toute la page.
      grid.querySelectorAll(".chapter-card.expanded").forEach((c) => c.classList.remove("expanded"));
      if (!wasOpen) card.classList.add("expanded");
    });
    card.querySelectorAll(".notion-row").forEach((row) => {
      row.addEventListener("click", (e) => {
        e.stopPropagation();
        if (row.dataset.resumable === "true") {
          // Une série est déjà en cours sur cette notion précise : on reprend
          // exactement où on s'est arrêté, sans relancer une nouvelle série.
          window.location.href = "exercice.html";
          return;
        }
        launchNotionSeries(row.dataset.chapter, row.dataset.notion, row.dataset.ids.split(",").map(Number));
      });
    });

    grid.appendChild(card);
  });
}

function avgDuration(history, chapter, notion) {
  const matches = history.filter((h) => h.chapter === chapter && h.notion === notion && h.duration_s);
  if (!matches.length) return "—";
  const avg = matches.reduce((s, h) => s + h.duration_s, 0) / matches.length;
  return `${Math.round(avg)} s`;
}

function launchNotionSeries(chapterId, notion, exerciseIds) {
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: "notion", chapterId, notion, exerciseIds })
  );
  window.location.href = "exercice.html";
}

function toggleSelection(id, card) {
  if (selected.has(id)) {
    selected.delete(id);
    card.classList.remove("selected");
  } else {
    if (isGuest && selected.size >= GUEST_MAX_CHAPTERS) {
      showGuestChaptersLimitModal();
      return;
    }
    selected.add(id);
    card.classList.add("selected");
  }
  updateSelectionBar();
}

function updateSelectionBar() {
  const n = selected.size;
  selectionCount.textContent = n === 0 ? "Tous les chapitres (aucune sélection)" : `${n} chapitre${n > 1 ? "s" : ""} sélectionné${n > 1 ? "s" : ""}`;
  selectionBar.classList.add("visible");
}

document.getElementById("btn-start-evaluation").addEventListener("click", (e) => {
  e.preventDefault();
  localStorage.setItem("lumis:selected_chapters", JSON.stringify([...selected]));
  window.location.href = "evaluation.html";
});

/** Ouvre automatiquement un chapitre (et scrolle jusqu'à lui) si on arrive
 * depuis le bouton "Aller au chapitre" du dashboard (MOD4). */
function openRequestedChapter() {
  let request;
  try {
    request = JSON.parse(localStorage.getItem("lumis:open_chapter"));
  } catch {
    request = null;
  }
  if (!request) return;
  localStorage.removeItem("lumis:open_chapter");

  const card = grid.querySelector(`.chapter-card[data-id="${request.chapterId}"]`);
  if (!card) return;
  grid.querySelectorAll(".chapter-card.expanded").forEach((c) => c.classList.remove("expanded"));
  card.classList.add("expanded");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
}

api.chapters().then((data) => {
  renderChapters(data.chapters_meta || []);
  selectionBar.classList.add("visible");
  openRequestedChapter();
});
