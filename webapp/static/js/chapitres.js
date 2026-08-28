import { api } from "./api.js";
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { getState, masteryByChapter, masteryByNotion, coverageByChapter, coverageByNotion, getInProgressSeries, getChapterStatus, scopedStats } from "./store.js";
import { renderResumeCard } from "./resume.js";
import { icon } from "./icons.js";
import { bindLiveTranslations } from "./i18n.js";
import { getStoredClassLevel } from "./curriculumSelector.js";
import { resolveChapterTitle } from "./chapterTitleByNotions.js";
import { getFavoriteChapters, toggleFavoriteChapter, favoriteIconSvg } from "./favorites.js";
import { normalizeText, debounce } from "./searchUtils.js";
import { DIFF_EMOJI, DIFF_LABEL_SHORT, DIFF_BADGE } from "./difficultyLevels.js";

const settingsReady = initSettingsManager();
settingsReady.then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));
renderResumeCard(document.getElementById("resume-card"));

const DIFF_LABEL = Object.fromEntries(
  Object.entries(DIFF_LABEL_SHORT).map(([lvl, label]) => [lvl, `${DIFF_EMOJI[lvl]} ${label}`])
);

const grid = document.getElementById("chapters-grid");
const emptyFilterMsg = document.getElementById("chapters-empty-filter");

let currentChaptersMeta = [];
let activeFilter = "all";

// ── Sélection multiple (chapitres entiers + notions isolées, tous chapitres
// confondus) — fusionnée en une seule série au clic sur la barre flottante.
// Map<chapterId, Set<notionLabel>> : structure unique, indépendante du DOM,
// pour que la sélection survive à un re-render (changement de filtre) et
// couvre plusieurs chapitres simultanément (contrairement à l'ancien système
// pré-évaluation qui ne sélectionnait qu'un chapitre entier à la fois, jamais
// mélangé avec des notions isolées d'autres chapitres). ───────────────────
const selectedNotions = new Map();

function selectedSetFor(chapterId) {
  let set = selectedNotions.get(chapterId);
  if (!set) { set = new Set(); selectedNotions.set(chapterId, set); }
  return set;
}

/** "empty" (rien coché) / "full" (toutes les notions sélectionnables du
 * chapitre) / "partial". `selectableCount` exclut les notions "reprenables"
 * (déjà en série sur exercice.html — voir isResumable dans renderChapters) :
 * elles ne rejoignent jamais selectedNotions, donc ne comptent ni au
 * numérateur ni au dénominateur. */
function chapterSelectionState(chapterId, selectableCount) {
  const set = selectedNotions.get(chapterId);
  const n = set ? set.size : 0;
  if (n === 0) return "empty";
  return n >= selectableCount ? "full" : "partial";
}

function formatDate(ts) {
  if (!ts) return "jamais";
  const diffDays = Math.floor((Date.now() - ts) / 86400000);
  if (diffDays <= 0) return "aujourd'hui";
  if (diffDays === 1) return "hier";
  return `il y a ${diffDays} j`;
}

function chapterIcon() {
  return icon("checklist");
}

function masteryLabel(coveragePct, accuracyPct, count) {
  if (count === 0) return { text: "À faire", cls: "badge--neutral" };
  if (coveragePct >= 70 && accuracyPct >= 70) return { text: "Maîtrisé", cls: "badge--success" };
  if (coveragePct >= 30 || accuracyPct >= 50) return { text: "En progrès", cls: "badge--warning" };
  return { text: "À renforcer", cls: "badge--danger" };
}

// ── Favoris ("Enregistrés") — voir favorites.js pour la persistance (partagée
// avec la page Cours, même chapitre = même favori partout). ─────────────────
function getFavorites() {
  return getFavoriteChapters(getStoredClassLevel());
}

function toggleFavorite(chapterId) {
  return toggleFavoriteChapter(chapterId, getStoredClassLevel());
}

// ── Filtres ──────────────────────────────────────────────────────────────────
const FILTER_EMPTY_MESSAGES = {
  ongoing: "Aucune série en cours.",
  mastered: "Aucun chapitre maîtrisé pour l'instant.",
  unmastered: "Bravo, tous les chapitres travaillés sont maîtrisés !",
  saved: "Aucun chapitre enregistré pour l'instant — clique sur l'étoile d'une carte pour l'ajouter.",
};

function applyFilter(chaptersMeta, filter, ctx) {
  const { favorites, inProgress } = ctx;
  switch (filter) {
    case "ongoing":
      return chaptersMeta.filter((ch) => inProgress && inProgress.seriesConfig?.chapterId === ch.id);
    case "mastered":
      return chaptersMeta.filter((ch) => ctx.masteryOf(ch) === "mastered");
    case "unmastered":
      return chaptersMeta.filter((ch) => ctx.masteryOf(ch) !== "mastered");
    case "saved":
      return chaptersMeta.filter((ch) => favorites.has(ch.id));
    default:
      return chaptersMeta;
  }
}

document.getElementById("chapter-filter-bar").addEventListener("click", (e) => {
  const btn = e.target.closest(".chapter-filter-pill");
  if (!btn) return;
  activeFilter = btn.dataset.filter;
  document.querySelectorAll(".chapter-filter-pill").forEach((b) => {
    b.classList.toggle("active", b === btn);
    b.setAttribute("aria-selected", String(b === btn));
  });
  renderChapters(currentChaptersMeta);
});

function renderChapters(chaptersMeta) {
  currentChaptersMeta = chaptersMeta;
  const state = scopedStats(getState(), getStoredClassLevel());
  const chapterCoverage = coverageByChapter(state.history);
  const chapterMastery = masteryByChapter(state.history);
  const notionCoverage = coverageByNotion(state.history);
  const notionMastery = masteryByNotion(state.history);
  const inProgress = getInProgressSeries();
  const favorites = getFavorites();

  const metaFor = (ch) => {
    const coveredIds = chapterCoverage[ch.id] || new Set();
    const progressPct = ch.n_exercises ? Math.round((coveredIds.size / ch.n_exercises) * 100) : 0;
    const accuracyPct = Math.round((chapterMastery[ch.id]?.rate || 0) * 100);
    return { coveredIds, progressPct, accuracyPct };
  };

  const visible = applyFilter(chaptersMeta, activeFilter, {
    favorites,
    inProgress,
    // Règle métier unique (Phase N) : un chapitre est "Maîtrisé" seulement si
    // accuracy >= 70% ET au moins MASTERY_MIN_ATTEMPTS tentatives — voir
    // store.js::getChapterStatus, seule source de vérité (plus de formule
    // propre à cette page basée sur la couverture).
    masteryOf: (ch) => getChapterStatus(ch.id, state.history),
  });

  emptyFilterMsg.hidden = visible.length !== 0;
  grid.hidden = visible.length === 0;
  if (!visible.length) {
    emptyFilterMsg.textContent = FILTER_EMPTY_MESSAGES[activeFilter] || "Aucun chapitre à afficher.";
  }

  grid.innerHTML = "";
  visible.forEach((ch) => {
    const { coveredIds, progressPct, accuracyPct } = metaFor(ch);
    const remaining = Math.max(0, ch.n_exercises - coveredIds.size);
    const estMinutes = remaining * 3;
    const isFavorite = favorites.has(ch.id);

    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;

    // Notions "reprenables" (déjà en série en cours ailleurs) : jamais
    // sélectionnables pour une nouvelle série — exclues du numérateur ET du
    // dénominateur de chapterSelectionState (voir sa doc ci-dessus).
    const seriesConfig = inProgress?.seriesConfig;
    const resumableLabels = new Set(
      ch.notions_detail
        .filter((n) => !!seriesConfig
          && seriesConfig.chapterId === ch.id
          && (seriesConfig.notions ? seriesConfig.notions.includes(n.notion) : seriesConfig.notion === n.notion))
        .map((n) => n.notion)
    );
    const selectableCount = ch.notions_detail.length - resumableLabels.size;

    const notionsHtml = ch.notions_detail
      .map((n) => {
        const key = `${ch.id}|${n.notion}`;
        const covered = (notionCoverage[key] || new Set()).size;
        const nCoveragePct = n.n_exercises ? Math.round((covered / n.n_exercises) * 100) : 0;
        const nm = notionMastery[key] || { count: 0, rate: 0, last: null };
        const nAccuracyPct = Math.round(nm.rate * 100);
        const mastery = masteryLabel(nCoveragePct, nAccuracyPct, nm.count);
        const isResumable = resumableLabels.has(n.notion);
        const isSelected = !isResumable && selectedSetFor(ch.id).has(n.notion);
        return `
        <div class="notion-row${isResumable ? " notion-row--resumable" : " notion-row--selectable"}${isSelected ? " selected" : ""}" data-chapter="${ch.id}" data-notion="${n.notion.replace(/"/g, "&quot;")}" data-ids="${n.exercise_ids.join(",")}" data-resumable="${isResumable}">
          <div class="notion-row-top">
            <span class="notion-row-label">${isResumable ? "" : `<span class="notion-checkbox" aria-hidden="true"></span>`}<span>${n.notion}</span></span>
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
            ${isResumable ? `<button class="btn btn-ghost btn-sm notion-action-btn" type="button">${icon("play")} Reprendre</button>` : ""}
          </div>
        </div>`;
      })
      .join("");

    const selectState = chapterSelectionState(ch.id, selectableCount);
    const hasAnySelected = selectState !== "empty";

    card.innerHTML = `
      <div class="chapter-card-top">
        <div class="chapter-icon">${chapterIcon()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${isFavorite ? " is-favorite" : ""}" aria-label="${isFavorite ? "Retirer des favoris" : "Ajouter aux favoris"}" aria-pressed="${isFavorite}">${favoriteIconSvg()}</button>
          <button type="button" class="chapter-select-btn" data-state="${selectState}" aria-label="Sélectionner tout le chapitre" aria-pressed="${selectState === "full"}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m5 13 4 4L19 7"/></svg>
          </button>
        </div>
      </div>
      <h3>${resolveChapterTitle(ch.title, ch.notions_cours) || ch.id.replace(/_/g, " ")}</h3>
      <div class="chapter-id">${ch.id.replace("_", " ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Progression</span><span>${progressPct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${progressPct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${icon("clock")} ~${estMinutes} min restantes</span>
        <span>${icon("penSquare")} ${ch.n_exercises} exercices</span>
        <span>${icon("layers")} ${ch.n_notions} notions</span>
      </div>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <span class="badge ${DIFF_BADGE[ch.difficulty_dominant]}">${DIFF_LABEL[ch.difficulty_dominant]} dominant</span>
        <span class="badge badge--neutral">Réussite ${accuracyPct}%</span>
      </div>
      <button class="chapter-expand-btn" type="button">
        Voir les notions
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <div class="notions-panel">
        ${notionsHtml}
        <button class="btn btn-primary btn-sm notions-start-btn" type="button" ${hasAnySelected ? "" : "disabled"}>Commencer la série</button>
      </div>
    `;

    card.querySelector(".chapter-favorite-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      const nowFavorite = toggleFavorite(ch.id);
      const btn = e.currentTarget;
      btn.classList.toggle("is-favorite", nowFavorite);
      btn.setAttribute("aria-pressed", String(nowFavorite));
      btn.setAttribute("aria-label", nowFavorite ? "Retirer des favoris" : "Ajouter aux favoris");
      // Si le filtre "Enregistrés" est actif, retirer un favori doit faire
      // disparaître la carte immédiatement (détection automatique, §9-10).
      if (activeFilter === "saved" && !nowFavorite) renderChapters(currentChaptersMeta);
    });
    card.querySelector(".chapter-expand-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      const wasOpen = card.classList.contains("expanded");
      // Effet accordéon : un seul chapitre ouvert à la fois sur toute la page.
      grid.querySelectorAll(".chapter-card.expanded").forEach((c) => c.classList.remove("expanded"));
      if (!wasOpen) card.classList.add("expanded");
    });

    const startBtn = card.querySelector(".notions-start-btn");
    const selectBtn = card.querySelector(".chapter-select-btn");

    /** Reflète l'état courant de selectedNotions (pour CE chapitre) sur le
     * DOM de sa carte : bouton chapitre (vide/partiel/complet), bouton
     * "Commencer la série" local, puis la barre flottante globale — jamais
     * l'inverse (selectedNotions reste l'unique source de vérité). */
    function syncCardUI() {
      const state = chapterSelectionState(ch.id, selectableCount);
      selectBtn.dataset.state = state;
      selectBtn.setAttribute("aria-pressed", String(state === "full"));
      startBtn.disabled = state === "empty";
      updateSelectionBar();
    }

    card.querySelectorAll(".notion-row").forEach((row) => {
      row.addEventListener("click", (e) => {
        e.stopPropagation();
        if (row.dataset.resumable === "true") {
          // Une série est déjà en cours sur cette notion précise : on reprend
          // exactement où on s'est arrêté, sans relancer une nouvelle série.
          window.location.href = "exercice.html";
          return;
        }
        // Multi-sélection : un clic sélectionne/désélectionne la notion au
        // lieu de démarrer immédiatement une série (§11-12) — synchronisé
        // dans selectedNotions pour que le bouton chapitre et la barre
        // flottante restent cohérents (CAS 2/3 de la synchronisation).
        const nowSelected = row.classList.toggle("selected");
        const set = selectedSetFor(ch.id);
        if (nowSelected) set.add(row.dataset.notion);
        else set.delete(row.dataset.notion);
        syncCardUI();
      });
    });

    selectBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const state = chapterSelectionState(ch.id, selectableCount);
      const set = selectedSetFor(ch.id);
      if (state === "full") {
        // Bascule complète -> vide (CAS de désélection totale du chapitre).
        set.clear();
      } else {
        // Vide ou partiel -> sélection complète (CAS 1) : coche toutes les
        // notions sélectionnables du chapitre (jamais les "reprenables").
        ch.notions_detail.forEach((n) => { if (!resumableLabels.has(n.notion)) set.add(n.notion); });
      }
      card.querySelectorAll(".notion-row--selectable").forEach((row) => {
        row.classList.toggle("selected", set.has(row.dataset.notion));
      });
      syncCardUI();
    });

    startBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const rows = [...card.querySelectorAll(".notion-row.selected")];
      if (!rows.length) return;
      const notions = rows.map((r) => r.dataset.notion);
      const exerciseIds = [...new Set(rows.flatMap((r) => r.dataset.ids.split(",").map(Number)))];
      launchNotionSeries(ch.id, notions, exerciseIds);
    });

    grid.appendChild(card);
  });

  updateSelectionBar();

  // Un changement de filtre re-génère toute la grille : réappliquer
  // l'assombrissement de la recherche en cours (si l'utilisateur cherchait
  // déjà) pour ne pas perdre son état.
  const searchInputEl = document.getElementById("chapters-search-input");
  if (searchInputEl?.value) applySearchDim(searchInputEl.value);
}

function avgDuration(history, chapter, notion) {
  const matches = history.filter((h) => h.chapter === chapter && h.notion === notion && h.duration_s);
  if (!matches.length) return "—";
  const avg = matches.reduce((s, h) => s + h.duration_s, 0) / matches.length;
  return `${Math.round(avg)} s`;
}

/** Lance une série couvrant une ou plusieurs notions sélectionnées d'un même
 * chapitre. `notion` reste une étiquette lisible (compatibilité d'affichage
 * avec exercice.js/profil.js, qui n'attendent qu'une chaîne) ; `notions`
 * (tableau) est ce qui permet à la reprise de série de savoir précisément
 * quelles notions sont couvertes (voir isResumable ci-dessus). */
function launchNotionSeries(chapterId, notions, exerciseIds) {
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: "notion", chapterId, notion: notions.join(" + "), notions, exerciseIds })
  );
  window.location.href = "exercice.html";
}

// ── Barre flottante de sélection multiple ────────────────────────────────
// Créée une seule fois (position:fixed, injectée hors de #chapters-grid pour
// ne jamais être détruite par un re-render de la grille au changement de
// filtre) puis seulement mise à jour ensuite. Agrège selectedNotions sur
// TOUS les chapitres de currentChaptersMeta — y compris ceux masqués par le
// filtre actif — pour que rien ne soit perdu si on change de filtre en
// cours de sélection.
let selectionBarEl = null;

function ensureSelectionBar() {
  if (selectionBarEl) return selectionBarEl;
  const bar = document.createElement("div");
  bar.className = "series-selection-bar";
  bar.id = "series-selection-bar";
  bar.innerHTML = `
    <div class="series-selection-stats">
      <div class="series-selection-stat">
        <strong id="series-selection-chapters">0</strong>
        <span>chapitre<span class="plural-s"></span></span>
      </div>
      <div class="series-selection-stat">
        <strong id="series-selection-notions">0</strong>
        <span>notion<span class="plural-s"></span></span>
      </div>
      <div class="series-selection-stat">
        <strong id="series-selection-exercises">0</strong>
        <span>exercice<span class="plural-s"></span></span>
      </div>
    </div>
    <button type="button" class="btn btn-primary series-selection-launch" id="series-selection-launch">
      Lancer la série
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
    </button>
  `;
  document.body.appendChild(bar);
  bar.querySelector("#series-selection-launch").addEventListener("click", launchMergedSeries);
  selectionBarEl = bar;

  // La bannière cookies (cookieConsent.js) est aussi position:fixed, ancrée
  // en bas d'écran (voir guest.css/base.css::.cookie-banner) : sans ce
  // repositionnement, les deux se superposent et "Lancer la série" devient
  // physiquement inatteignable tant que la bannière n'est pas fermée. Un
  // MutationObserver (et non un simple appel ponctuel) car la bannière peut
  // apparaître/disparaître (accepter/refuser) à tout moment, indépendamment
  // d'un changement de sélection.
  const repositionAboveCookieBanner = () => {
    const cookieBanner = document.getElementById("cookie-consent-banner");
    if (cookieBanner) {
      const rect = cookieBanner.getBoundingClientRect();
      bar.style.bottom = `${Math.max(22, window.innerHeight - rect.top + 14)}px`;
    } else {
      bar.style.bottom = "";
    }
  };
  repositionAboveCookieBanner();
  new MutationObserver(repositionAboveCookieBanner).observe(document.body, { childList: true });
  window.addEventListener("resize", repositionAboveCookieBanner);

  return bar;
}

/** Recalcule les compteurs globaux depuis selectedNotions + currentChaptersMeta
 * (jamais depuis le DOM, pour rester exact même pour un chapitre masqué par
 * le filtre actif) et anime la barre à l'apparition / au changement de valeur. */
function updateSelectionBar() {
  const bar = ensureSelectionBar();
  let chaptersFull = 0;
  let notionsCount = 0;
  let exerciseIdSet = new Set();

  for (const [chapterId, notionSet] of selectedNotions) {
    if (notionSet.size === 0) continue;
    const ch = currentChaptersMeta.find((c) => c.id === chapterId);
    if (!ch) continue;
    notionsCount += notionSet.size;
    if (notionSet.size >= ch.notions_detail.length) chaptersFull += 1;
    for (const notionLabel of notionSet) {
      const detail = ch.notions_detail.find((n) => n.notion === notionLabel);
      detail?.exercise_ids.forEach((id) => exerciseIdSet.add(id));
    }
  }

  const hasSelection = notionsCount > 0;
  bar.classList.toggle("visible", hasSelection);
  if (!hasSelection) return;

  const setCounter = (id, value) => {
    const el = document.getElementById(id);
    if (el.textContent !== String(value)) {
      el.textContent = String(value);
      el.closest(".series-selection-stat").classList.remove("bump");
      // Force un reflow pour rejouer l'animation même si la valeur change
      // deux fois de suite au même compteur (ex: +1 puis -1 rapidement).
      void el.offsetWidth;
      el.closest(".series-selection-stat").classList.add("bump");
    }
    el.closest(".series-selection-stat").querySelector(".plural-s").textContent = value > 1 ? "s" : "";
  };
  setCounter("series-selection-chapters", chaptersFull);
  setCounter("series-selection-notions", notionsCount);
  setCounter("series-selection-exercises", exerciseIdSet.size);
}

/** Fusionne TOUTE la sélection courante (chapitres entiers + notions isolées,
 * tous chapitres confondus) en une seule série, en construisant exactement
 * l'objet que consumePendingSeries()/buildSeriesPool()/startSeries()
 * (exercice.js, non modifiés) savent déjà consommer — voir launchNotionSeries
 * ci-dessus pour le même contrat, cas à un seul chapitre. */
function launchMergedSeries() {
  const notions = [];
  const exerciseIdSet = new Set();
  const chapterIds = [];

  for (const [chapterId, notionSet] of selectedNotions) {
    if (notionSet.size === 0) continue;
    const ch = currentChaptersMeta.find((c) => c.id === chapterId);
    if (!ch) continue;
    chapterIds.push(chapterId);
    for (const notionLabel of notionSet) {
      notions.push(notionLabel);
      const detail = ch.notions_detail.find((n) => n.notion === notionLabel);
      detail?.exercise_ids.forEach((id) => exerciseIdSet.add(id));
    }
  }
  if (!exerciseIdSet.size) return;

  const label = notions.length <= 3 ? notions.join(" + ") : `${notions.length} notions sélectionnées`;
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({
      mode: "notion",
      // Un seul chapitre sélectionné : comportement identique à
      // launchNotionSeries() (isResumable pourra encore cibler ce chapitre).
      // Plusieurs chapitres mélangés : null, jamais une valeur inventée.
      chapterId: chapterIds.length === 1 ? chapterIds[0] : null,
      notion: label,
      notions,
      exerciseIds: [...exerciseIdSet],
    })
  );
  window.location.href = "exercice.html";
}

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

// ── Recherche (chapitre / notion / difficulté) ──────────────────────────────
// Index construit UNE SEULE FOIS (dans le .then final ci-dessous) à partir de
// chaptersMeta déjà chargé en mémoire — jamais de nouvelle requête réseau ni
// de parcours du DOM pour chercher : tout se fait sur les données. Réutilise
// exactement le vocabulaire de difficulté déjà affiché sur les cartes
// (DIFF_LABEL) pour qu'une recherche "difficile" retrouve les notions
// concernées, sans introduire de nouvelle taxonomie.
const DIFF_SEARCH_WORDS = { 1: "facile", 2: "moyen", 3: "confirme", 4: "difficile", 5: "expert" };
let searchIndex = [];

function buildSearchIndex(chaptersMeta) {
  searchIndex = chaptersMeta.flatMap((ch) => {
    const chapterTitle = resolveChapterTitle(ch.title, ch.notions_cours) || ch.id.replace(/_/g, " ");
    const chapterEntry = {
      type: "chapter", chapterId: ch.id, chapterTitle, notionLabel: null,
      norm: normalizeText(chapterTitle),
    };
    const notionEntries = (ch.notions_detail || []).map((n) => {
      const diffWords = (n.difficulties_available || []).map((d) => DIFF_SEARCH_WORDS[d] || "").join(" ");
      return {
        type: "notion", chapterId: ch.id, chapterTitle, notionLabel: n.notion,
        norm: normalizeText(`${chapterTitle} ${n.notion} ${diffWords}`),
        notionNorm: normalizeText(n.notion),
      };
    });
    return [chapterEntry, ...notionEntries];
  });
}

function runSearch(query) {
  const q = normalizeText(query);
  if (!q) return [];
  return searchIndex
    .filter((item) => item.norm.includes(q))
    .sort((a, b) => {
      const aRank = (a.notionNorm || a.norm).startsWith(q) ? 0 : 1;
      const bRank = (b.notionNorm || b.norm).startsWith(q) ? 0 : 1;
      return aRank - bRank;
    })
    .slice(0, 20);
}

const searchInput = document.getElementById("chapters-search-input");
const searchClearBtn = document.getElementById("chapters-search-clear");
const searchResultsEl = document.getElementById("chapters-search-results");

/** Assombrit (sans les retirer du flux — transition CSS douce, jamais de
 * ré-render coûteux) les cartes qui ne correspondent pas à la recherche en
 * cours, en plus du panneau de résultats détaillé (qui, lui, descend au
 * niveau des notions). */
function applySearchDim(query) {
  const q = normalizeText(query);
  grid.querySelectorAll(".chapter-card").forEach((card) => {
    if (!q) { card.classList.remove("is-search-dimmed"); return; }
    const ch = currentChaptersMeta.find((c) => c.id === card.dataset.id);
    const chapterTitle = ch ? (resolveChapterTitle(ch.title, ch.notions_cours) || ch.id) : "";
    const matches = normalizeText(chapterTitle).includes(q)
      || (ch?.notions_detail || []).some((n) => normalizeText(n.notion).includes(q));
    card.classList.toggle("is-search-dimmed", !matches);
  });
}

function renderSearchResults(query) {
  if (searchClearBtn) searchClearBtn.hidden = !query;
  applySearchDim(query);
  if (!query) {
    searchResultsEl.hidden = true;
    searchResultsEl.innerHTML = "";
    return;
  }
  const results = runSearch(query);
  searchResultsEl.hidden = false;
  if (!results.length) {
    searchResultsEl.innerHTML = `<div class="page-search-empty">Aucun résultat pour « ${query} ».</div>`;
    return;
  }
  searchResultsEl.innerHTML = results.map((r, i) => `
    <button type="button" class="page-search-item${i === 0 ? " is-active" : ""}" data-index="${i}" role="option">
      <span class="title">${icon(r.type === "chapter" ? "checklist" : "layers")}${r.type === "chapter" ? r.chapterTitle : r.notionLabel}</span>
      <span class="subtitle">${r.type === "chapter" ? "Chapitre" : `${r.chapterTitle} — Notion`}</span>
    </button>
  `).join("");
  results.forEach((r, i) => {
    searchResultsEl.children[i].addEventListener("click", () => pickSearchResult(r));
  });
}

/** Ouvre le chapitre (accordéon) du résultat choisi et, pour une notion,
 * scrolle jusqu'à sa ligne précise en la mettant brièvement en évidence —
 * même mécanique que openRequestedChapter() ci-dessous (déjà éprouvée pour
 * le lien "Aller au chapitre" du dashboard). */
function pickSearchResult(result) {
  searchInput.value = result.type === "chapter" ? result.chapterTitle : result.notionLabel;
  searchResultsEl.hidden = true;
  const card = grid.querySelector(`.chapter-card[data-id="${result.chapterId}"]`);
  if (!card) return;
  grid.querySelectorAll(".chapter-card.expanded").forEach((c) => { if (c !== card) c.classList.remove("expanded"); });
  card.classList.add("expanded");
  card.scrollIntoView({ behavior: "smooth", block: "center" });
  if (result.type === "notion") {
    const row = card.querySelector(`.notion-row[data-notion="${CSS.escape(result.notionLabel)}"]`);
    if (row) {
      setTimeout(() => {
        row.scrollIntoView({ behavior: "smooth", block: "center" });
        row.classList.add("notion-row--highlight");
        setTimeout(() => row.classList.remove("notion-row--highlight"), 1600);
      }, 380); // laisse le temps à l'accordéon de s'ouvrir (transition max-height 350ms)
    }
  }
}

if (searchInput) {
  const debouncedSearch = debounce((q) => renderSearchResults(q), 250);
  searchInput.addEventListener("input", () => debouncedSearch(searchInput.value));
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (searchInput.value) { searchInput.value = ""; renderSearchResults(""); }
      else searchInput.blur();
      return;
    }
    if (e.key === "Enter") {
      const active = searchResultsEl.querySelector(".page-search-item.is-active") || searchResultsEl.querySelector(".page-search-item");
      if (active) active.click();
      return;
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const items = [...searchResultsEl.querySelectorAll(".page-search-item")];
      if (!items.length) return;
      const activeIdx = items.findIndex((it) => it.classList.contains("is-active"));
      const nextIdx = Math.max(0, Math.min(items.length - 1, activeIdx + (e.key === "ArrowDown" ? 1 : -1)));
      items.forEach((it) => it.classList.remove("is-active"));
      items[nextIdx].classList.add("is-active");
      items[nextIdx].scrollIntoView({ block: "nearest" });
    }
  });
  searchClearBtn?.addEventListener("click", () => {
    searchInput.value = "";
    renderSearchResults("");
    searchInput.focus();
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".page-search") && !e.target.closest(".page-search-results")) {
      searchResultsEl.hidden = true;
    }
  });
}

Promise.all([settingsReady, api.chapters(getStoredClassLevel())]).then(([, data]) => {
  const chaptersMeta = data.chapters_meta || [];
  renderChapters(chaptersMeta);
  buildSearchIndex(chaptersMeta);
  openRequestedChapter();
});
