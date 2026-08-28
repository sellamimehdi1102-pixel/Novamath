import { api } from "./api.js";
import { initSettingsManager, onSettingsChange } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { icon, ICONS } from "./icons.js";
import { bindLiveTranslations } from "./i18n.js";
import { setMathContent } from "./mathrender.js";
import { renderFigure } from "./geomSvg.js";
import { getStoredClassLevel, fetchCurricula } from "./curriculumSelector.js";
import { fadeInTransition } from "./animations.js";
import { resolveChapterTitle } from "./chapterTitleByNotions.js";
import { getFavoriteChapters, toggleFavoriteChapter, getFavoriteNotions, toggleFavoriteNotion, favoriteIconSvg } from "./favorites.js";
import { normalizeText, debounce } from "./searchUtils.js";
import { openReportTicketPopup } from "./supportTicket.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const listView = document.getElementById("cours-list-view");
const readerView = document.getElementById("cours-reader-view");
const grid = document.getElementById("cours-grid");

// ── Mode invité : mêmes règles que Exercices (2 chapitres max), et aucune
// progression de lecture n'est conservée pour un invité (purgée au même
// moment que ses stats/paramètres, voir auth.py::_purge_account). ────────────
const GUEST_MAX_CHAPTERS = 2;
let isGuest = false;
api.me().then(({ user }) => { isGuest = !!user.is_guest; }).catch(() => {});
const openedChapters = new Set();

let chaptersMeta = [];
let courseProgress = {};
const contentCache = new Map();
let activeFilter = "all";

function chapterIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>`;
}

function ensureGuestCoursModal() {
  if (document.getElementById("guest-cours-modal-overlay")) return;
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "guest-cours-modal-overlay";
  overlay.hidden = true;
  overlay.innerHTML = `
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.hidden = true; });
  overlay.querySelector("#btn-guest-cours-dismiss").addEventListener("click", () => { overlay.hidden = true; });
  overlay.querySelectorAll(".js-open-signup, .js-open-login").forEach((btn) => {
    btn.addEventListener("click", () => { overlay.hidden = true; });
  });
}

function showGuestCoursLimitModal() {
  ensureGuestCoursModal();
  document.getElementById("guest-cours-modal-overlay").hidden = false;
}

// ── Grille des chapitres ─────────────────────────────────────────────────
function computeChapterStats(ch) {
  const cp = courseProgress[ch.id] || {};
  const entries = Object.values(cp);
  const doneCount = entries.filter((n) => n.status === "done").length;
  const total = ch.n_notions || 0;
  const pct = total ? Math.round((doneCount / total) * 100) : 0;
  const anyInProgress = entries.some((n) => n.status === "in_progress");
  return { doneCount, total, pct, anyInProgress };
}

// ── Filtres (Tous / En cours / Terminés / Favoris) ──────────────────────────
const FILTER_EMPTY_MESSAGES = {
  ongoing: "Aucun cours en cours de lecture.",
  done: "Aucun cours terminé pour l'instant.",
  favorites: "Aucun favori pour l'instant — clique sur l'étoile d'un chapitre ou d'une notion pour l'ajouter.",
};

/** Un chapitre a une notion favorite si l'une de ses clés "chapterId|notionId"
 * (voir favorites.js) commence par ce chapterId — pas besoin d'avoir chargé
 * le contenu du chapitre pour le savoir depuis la grille. */
function chapterHasFavoriteNotion(chapterId, favNotions) {
  const prefix = `${chapterId}|`;
  for (const key of favNotions) if (key.startsWith(prefix)) return true;
  return false;
}

function chapterMatchesFilter(ch, filter, favChapters, favNotions) {
  const stats = computeChapterStats(ch);
  switch (filter) {
    case "ongoing":
      return !(stats.total > 0 && stats.doneCount === stats.total) && (stats.anyInProgress || stats.doneCount > 0);
    case "done":
      return stats.total > 0 && stats.doneCount === stats.total;
    case "favorites":
      return favChapters.has(ch.id) || chapterHasFavoriteNotion(ch.id, favNotions);
    default:
      return true;
  }
}

document.getElementById("cours-filter-bar")?.addEventListener("click", (e) => {
  const btn = e.target.closest(".chapter-filter-pill");
  if (!btn) return;
  activeFilter = btn.dataset.filter;
  document.querySelectorAll("#cours-filter-bar .chapter-filter-pill").forEach((b) => {
    b.classList.toggle("active", b === btn);
    b.setAttribute("aria-selected", String(b === btn));
  });
  renderGrid();
});

function renderGrid() {
  const favChapters = getFavoriteChapters(getStoredClassLevel());
  const favNotions = getFavoriteNotions(getStoredClassLevel());
  const visible = chaptersMeta.filter((ch) => chapterMatchesFilter(ch, activeFilter, favChapters, favNotions));

  const emptyEl = document.getElementById("cours-empty-filter");
  if (emptyEl) {
    emptyEl.hidden = visible.length !== 0;
    emptyEl.textContent = FILTER_EMPTY_MESSAGES[activeFilter] || "Aucun cours à afficher.";
  }
  grid.hidden = visible.length === 0;

  grid.innerHTML = "";
  visible.forEach((ch) => {
    const stats = computeChapterStats(ch);
    const isFavorite = favChapters.has(ch.id);
    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;
    card.innerHTML = `
      <div class="chapter-card-top">
        <div class="chapter-icon">${chapterIcon()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${isFavorite ? " is-favorite" : ""}" aria-label="${isFavorite ? "Retirer des favoris" : "Ajouter aux favoris"}" aria-pressed="${isFavorite}">${favoriteIconSvg()}</button>
        </div>
      </div>
      <h3>${resolveChapterTitle(ch.title, ch.notions_cours) || ch.id.replace(/_/g, " ")}</h3>
      <div class="chapter-id">${ch.id.replace("_", " ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${stats.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${stats.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${icon("bookOpen")} ${ch.n_notions} notion${ch.n_notions > 1 ? "s" : ""}</span>
        <span>${icon("check")} ${stats.doneCount}/${stats.total} terminée${stats.doneCount > 1 ? "s" : ""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${icon("bookOpen")} ${stats.anyInProgress ? "Continuer" : "Ouvrir"}
      </button>
    `;
    card.querySelector(".cours-open-btn").addEventListener("click", () => openChapter(ch.id));
    card.querySelector(".chapter-favorite-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      const nowFavorite = toggleFavoriteChapter(ch.id, getStoredClassLevel());
      const btn = e.currentTarget;
      btn.classList.toggle("is-favorite", nowFavorite);
      btn.setAttribute("aria-pressed", String(nowFavorite));
      btn.setAttribute("aria-label", nowFavorite ? "Retirer des favoris" : "Ajouter aux favoris");
      if (activeFilter === "favorites" && !nowFavorite) renderGrid();
    });
    grid.appendChild(card);
  });

  const searchInputEl = document.getElementById("cours-search-input");
  if (searchInputEl?.value) applySearchDim(searchInputEl.value);
}

// ── Chargement paresseux du contenu (un seul chapitre à la fois) ───────────
// Passe désormais par GET /api/course-content/<classe>/<chapitre> (Chantier
// "Répartition du contenu des cours par plan") plutôt qu'un fetch statique
// direct vers data/cours*/chapitre_N.json — le contenu Premium/Ultra n'est
// plus jamais envoyé à un plan qui n'y a pas droit (filtré côté serveur,
// voir server.py::api_course_content/course_content_service.py). Le cache
// mémoire n'a pas besoin d'être scopé par classe : changer de classe
// recharge toujours la page (curriculumSelector.js), qui repart d'un cache
// vide.
async function loadChapterContent(chapterId) {
  if (contentCache.has(chapterId)) return contentCache.get(chapterId);
  const data = await api.getCourseContent(getStoredClassLevel(), chapterId);
  contentCache.set(chapterId, data);
  return data;
}

function showListView() {
  listView.hidden = false;
  readerView.hidden = true;
  readerView.innerHTML = "";
}

function showReaderView() {
  listView.hidden = true;
  readerView.hidden = false;
}

// ── Vue "détail chapitre" : liste des notions à lire ────────────────────────
async function openChapter(chapterId) {
  if (isGuest && !openedChapters.has(chapterId) && openedChapters.size >= GUEST_MAX_CHAPTERS) {
    showGuestCoursLimitModal();
    return;
  }
  openedChapters.add(chapterId);

  readerView.innerHTML = `
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `;
  showReaderView();

  // Le squelette ci-dessus ne doit JAMAIS rester affiché indéfiniment :
  // avant, une erreur de fetch (contenu manquant/serveur indisponible)
  // devenait une Promise rejetée non gérée (openChapter() est appelée sans
  // .catch() depuis le listener de clic) — invisible pour l'utilisateur, qui
  // voyait juste le chargement rester bloqué pour toujours. Voir l'incident
  // "troisieme" (curriculum_registry.py) qui a révélé ce trou.
  try {
    const content = await loadChapterContent(chapterId);
    renderChapterDetail(chapterId, content);
  } catch (err) {
    console.error("Échec du chargement du chapitre", chapterId, err);
    renderChapterLoadError(chapterId);
  }
}

function renderChapterLoadError(chapterId) {
  readerView.innerHTML = `
    <div class="guest-lock-card card cours-load-error" role="alert">
      <div class="icon-wrap icon-wrap--danger">${ICONS.alertTriangle}</div>
      <h3>Contenu indisponible</h3>
      <p>Le contenu de ce chapitre est momentanément indisponible.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary" id="cours-error-retry">Réessayer</button>
        <button type="button" class="btn btn-secondary" id="cours-error-back">Retour</button>
      </div>
    </div>
  `;
  readerView.querySelector("#cours-error-retry").addEventListener("click", () => openChapter(chapterId));
  readerView.querySelector("#cours-error-back").addEventListener("click", () => showListView());
}

function notionStatusBadge(status) {
  if (status === "done") return `<span class="badge badge--success">Terminée</span>`;
  if (status === "in_progress") return `<span class="badge badge--warning">En cours</span>`;
  return `<span class="badge badge--neutral">À lire</span>`;
}

// ── Icône adaptée au sujet de la notion — heuristique par mots-clés sur
// l'id/titre, repli sur l'icône générique du chapitre si rien ne matche. ───
const NOTION_ICON_RULES = [
  [/racine|carr[ée]e?\b/, "compass"],
  [/puissance|exposant/, "zap"],
  [/premier|diviseur|multiple|pgcd|ppcm/, "layers"],
  [/ensemble.*nombre|nombre.*ensemble/, "database"],
  [/fonction|courbe|antécédent|image/, "barChart"],
  [/vecteur|translat|chasles/, "ruler"],
  [/probabilit|arbre|tirage|hasard|évènement|événement/, "sparkles"],
  [/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/, "compass"],
  [/[ée]quation|in[ée]quation|syst[èe]me/, "scale"],
  [/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/, "barChart"],
  [/suite/, "sliders"],
  [/d[ée]riv/, "zap"],
];
function notionIcon(n) {
  const s = `${n.id} ${n.title}`.toLowerCase();
  for (const [re, name] of NOTION_ICON_RULES) if (re.test(s)) return name;
  return "bookOpen";
}

// ── Temps de lecture estimé — comptage de mots sur le contenu textuel réel
// de la notion (≈180 mots/min, arrondi, plancher à 3 min pour rester
// réaliste même sur une notion courte). ─────────────────────────────────
function estimateReadingMinutes(n) {
  const chunks = [
    n.intro, n.definition, n.explicationSimple, n.intuition, n.astuce,
    ...(n.exemples || []).flatMap((e) => [e.enonce, e.explication, e.conclusion, ...(e.calcul || []).map((c) => c.texte)]),
    ...(n.reglesImportantes || []), ...(n.remarques || []),
    ...(n.erreursFrequentes || []), ...(n.aRetenir || []),
  ].filter(Boolean);
  const words = chunks.join(" ").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(3, Math.round(words / 180));
}

// ── Niveau affiché — `n.difficulte` si renseigné, sinon la difficulté la
// plus fréquente parmi les exemples de la notion. ──────────────────────
function notionLevel(n) {
  if (n.difficulte) return n.difficulte;
  const counts = {};
  (n.exemples || []).forEach((e) => { if (e.difficulte) counts[e.difficulte] = (counts[e.difficulte] || 0) + 1; });
  const top = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
  return top || "moyen";
}
function levelBadge(level) {
  const l = (level || "").toLowerCase();
  if (l === "facile") return `<span class="badge badge--success">Facile</span>`;
  if (l === "difficile") return `<span class="badge badge--danger">Difficile</span>`;
  return `<span class="badge badge--warning">Moyen</span>`;
}

function renderChapterDetail(chapterId, content) {
  const cp = courseProgress[chapterId] || {};
  // Repère de progression du chapitre — présentation pure, réutilise le même
  // calcul que la grille (computeChapterStats), aucune nouvelle donnée.
  const meta = chaptersMeta.find((c) => c.id === chapterId);
  const stats = meta ? computeChapterStats(meta) : null;
  const favNotions = getFavoriteNotions(getStoredClassLevel());

  readerView.innerHTML = `
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${icon("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${chapterId.replace("_", " ")}</div>
      <h1>${resolveChapterTitle(content.title, content.notions.map((n) => n.title)) || chapterId.replace(/_/g, " ")}</h1>
      ${stats ? `
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${stats.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${stats.doneCount}/${stats.total} notions terminées</span>
      </div>` : ""}
    </div>
    <div class="cours-notions-list">
      ${content.notions.map((n) => {
        const cpn = cp[n.id];
        const status = cpn?.status || "todo";
        const nEx = (n.exemples || []).length;
        const nGraph = n.figure ? 1 : 0;
        const desc = n.objectif || (n.intro || "").split("\n")[0] || "";
        const progressPct = cpn?.quizTotal ? Math.round((cpn.quizScore / cpn.quizTotal) * 100) : 50;
        const isNotionFav = favNotions.has(`${chapterId}|${n.id}`);
        return `
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${icon(notionIcon(n))}</div>
            <div class="cours-notion-card-badges">${levelBadge(notionLevel(n))}${notionStatusBadge(status)}</div>
          </div>
          <div class="cours-notion-title-row">
            <h3>${n.title}</h3>
            <button type="button" class="chapter-favorite-btn${isNotionFav ? " is-favorite" : ""}" aria-label="${isNotionFav ? "Retirer des favoris" : "Ajouter aux favoris"}" aria-pressed="${isNotionFav}">${favoriteIconSvg()}</button>
          </div>
          <p class="cours-notion-card-desc" data-text="${encodeURIComponent(desc)}"></p>
          <div class="cours-notion-meta">
            <span>${icon("clock")} ${estimateReadingMinutes(n)} min</span>
            <span>${icon("penSquare")} ${nEx} exemple${nEx > 1 ? "s" : ""}</span>
            ${nGraph ? `<span>${icon("barChart")} ${nGraph} graphique</span>` : ""}
          </div>
          ${status === "in_progress" ? `
          <div class="cours-notion-card-progress">
            <div class="progress-track"><div class="progress-fill" style="width:${progressPct}%"></div></div>
          </div>` : ""}
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${icon("play")} ${status === "todo" ? "Commencer" : status === "done" ? "Relire" : "Continuer"}
          </button>
        </div>`;
      }).join("")}
    </div>
  `;
  renderMathAttrs(readerView);
  fadeInTransition(readerView);
  readerView.querySelector("#cours-back-to-grid").addEventListener("click", () => {
    renderGrid();
    showListView();
  });
  readerView.querySelectorAll(".cours-read-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const notionId = e.target.closest(".cours-notion-card").dataset.notion;
      const notion = content.notions.find((n) => n.id === notionId);
      openNotionReader(chapterId, content, notion);
    });
  });
  readerView.querySelectorAll(".cours-notion-card .chapter-favorite-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const notionId = btn.closest(".cours-notion-card").dataset.notion;
      const nowFavorite = toggleFavoriteNotion(chapterId, notionId, getStoredClassLevel());
      btn.classList.toggle("is-favorite", nowFavorite);
      btn.setAttribute("aria-pressed", String(nowFavorite));
      btn.setAttribute("aria-label", nowFavorite ? "Retirer des favoris" : "Ajouter aux favoris");
    });
  });
}

// ── Étapes de méthode : couleur + icône par étape ───────────────────────────
const STEP_COLORS = ["blue", "purple", "green", "orange", "pink"];

function buildStepsHtml(etapes) {
  return `<div class="cours-steps">${(etapes || []).map((e, i) => `
    <div class="cours-step cours-step--${e.couleur || STEP_COLORS[i % STEP_COLORS.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${icon(e.icone || "check")}</span>
        <span class="cours-step-index">${i + 1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(e.texte)}"></div>
    </div>
  `).join("")}</div>`;
}

// ── Exemples détaillés : calcul étape par étape avec flèches ────────────────
// `analyse`/`choixMethode`/`interpretation` (optionnels) : un exemple
// "entièrement guidé" ajoute ces 3 champs pour dérouler enoncé → analyse →
// choix de la méthode → calcul détaillé (déjà `calcul[]`) → résultat →
// interprétation, plutôt qu'un simple enoncé/réponse. Absents sur la
// quasi-totalité des exemples existants : la carte reste alors strictement
// identique à avant (repli sur `conclusion` seul).
// `ex.interactif` (optionnel) : au lieu d'afficher tout le calcul et la
// réponse d'un coup, l'élève révèle chaque étape avec un bouton ("Voir
// l'étape suivante"), puis la correction complète (réponse + interprétation)
// avec un dernier clic — voir le gestionnaire `.cours-exemple-next-btn`.
// Sans ce champ, la carte reste strictement identique à avant (tout visible
// immédiatement).
function buildExempleHtml(ex) {
  const interactif = !!ex.interactif;
  const totalSteps = (ex.calcul || []).length;
  const calcHtml = (ex.calcul || []).map((c, i, arr) => `
    <div class="cours-calc-row${interactif ? " cours-calc-row--hidden" : ""}" data-calc-index="${i}">
      ${c.expr ? `<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${c.expr}$`)}"></div>` : ""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(c.texte)}"></div>
    </div>
    ${i < arr.length - 1 ? `<div class="cours-calc-arrow${interactif ? " cours-calc-row--hidden" : ""}" data-calc-index="${i}">${ICONS.arrowRight}</div>` : ""}
  `).join("");
  const correctionHtml = `
    <div class="cours-exemple-correction${interactif ? " cours-exemple-correction--hidden" : ""}">
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : " + ex.reponse)}"></div>
      ${ex.interpretation ? `
      <div class="cours-exemple-subblock cours-exemple-interpretation">
        <span class="cours-exemple-subblock-label">${icon("lightbulb")} Interprétation</span>
        <div data-text="${encodeURIComponent(ex.interpretation)}"></div>
      </div>` : ex.conclusion ? `<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(ex.conclusion)}"></div>` : ""}
    </div>`;
  return `
    <div class="card cours-exemple-card" data-total-steps="${totalSteps}" data-revealed="0">
      <div class="cours-exemple-title">${icon("penSquare")} <span data-text="${encodeURIComponent(ex.titre || "Exemple")}"></span></div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(ex.enonce)}"></div>
      ${ex.analyse ? `
      <div class="cours-exemple-subblock">
        <span class="cours-exemple-subblock-label">${icon("eye")} Analyse</span>
        <div data-text="${encodeURIComponent(ex.analyse)}"></div>
      </div>` : ""}
      ${ex.choixMethode ? `
      <div class="cours-exemple-subblock">
        <span class="cours-exemple-subblock-label">${icon("compass")} Méthode choisie</span>
        <div data-text="${encodeURIComponent(ex.choixMethode)}"></div>
      </div>` : ""}
      ${ex.explication ? `<div class="cours-exemple-explication" data-text="${encodeURIComponent(ex.explication)}"></div>` : ""}
      <div class="cours-calc-block">${calcHtml}</div>
      ${interactif && totalSteps ? `
      <div class="cours-exemple-controls">
        <button type="button" class="btn btn-ghost btn-sm cours-exemple-next-btn">${icon("eye")} Voir l'étape suivante</button>
      </div>` : ""}
      ${correctionHtml}
    </div>
  `;
}

// `notion.questionsEclair` (optionnel) : très courtes questions de réflexion
// insérées entre les sections du cours (ex. "Que remarques-tu ?"), pour faire
// réfléchir l'élève en continu plutôt que d'attendre le quiz final. `apres`
// choisit l'ancre d'insertion ("pourquoi", "figure", "intuition", "methode",
// ou "exemple:<id>" pour après un exemple précis). Absent sur toutes les
// autres notions : n'affiche rien tant que ce champ n'existe pas.
function questionsEclairHtml(notion, apres) {
  const items = (notion.questionsEclair || []).filter((q) => q.apres === apres);
  if (!items.length) return "";
  return items.map((q) => `
    <div class="cours-question-eclair">
      <div class="cours-question-eclair-label">${icon("helpCircle")} <span data-text="${encodeURIComponent(q.question)}"></span></div>
      ${q.piste ? `
      <button type="button" class="cours-question-eclair-btn" data-piste="${encodeURIComponent(q.piste)}">${icon("eye")} Voir une piste</button>
      <div class="cours-question-eclair-piste" hidden></div>` : ""}
    </div>
  `).join("");
}

function renderMathAttrs(root) {
  root.querySelectorAll("[data-text]").forEach((el) => {
    setMathContent(el, decodeURIComponent(el.dataset.text));
    el.removeAttribute("data-text");
  });
}

// ── Indicateurs de contenu verrouillé (Chantier "Répartition du contenu des
// cours par plan") — `notion.locked_content` vient du backend
// (course_content_service.py), jamais recalculé côté client : le frontend ne
// fait qu'afficher ce que le serveur a réellement retiré. Un seul indicateur
// par palier au maximum par notion (pas un par champ retiré), pour rester
// discret — voir le principe UX du chantier ("pas de publicité permanente"). ─
function lockedContentCard(tier, title, body) {
  return `
    <div class="cours-box cours-box--locked cours-box--locked-${tier}">
      <div class="cours-box-header">${icon("lock")} <span>${title}</span></div>
      <div class="cours-box-body">${body}</div>
    </div>
  `;
}

function buildLockedPremiumHtml(locked) {
  if (!locked?.premium) return "";
  const extra = locked.premium_extra_examples || 0;
  const body = extra > 0
    ? `Approfondis cette notion avec ${extra} exemple${extra > 1 ? "s" : ""} supplémentaire${extra > 1 ? "s" : ""} et des explications détaillées.`
    : "Approfondis cette notion avec des explications et un contenu supplémentaires.";
  return lockedContentCard("premium", "Contenu Premium", body);
}

function buildLockedUltraHtml(locked) {
  if (!locked?.ultra) return "";
  return lockedContentCard("ultra", "Contenu Ultra", "Accède à l'explication complète et aux approfondissements de cette notion.");
}

// ── Navigation notion précédente / suivante — présentation pure à partir de
// content.notions, déjà chargé en mémoire (aucune requête, aucun calcul). ──
function notionNavHtml(content, notion) {
  const idx = content.notions.findIndex((n) => n.id === notion.id);
  const prev = idx > 0 ? content.notions[idx - 1] : null;
  const next = idx < content.notions.length - 1 ? content.notions[idx + 1] : null;
  if (!prev && !next) return "";
  return `
    <div class="cours-notion-nav">
      ${prev ? `
      <button type="button" class="cours-notion-nav-btn" data-notion="${prev.id}">
        ${icon("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${prev.title}</span></span>
      </button>` : "<span></span>"}
      ${next ? `
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${next.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${next.title}</span></span>
        ${icon("arrowRight")}
      </button>` : ""}
    </div>
  `;
}

// ── Lecteur de notion : page unique, scroll, sections toujours découpées ───
function openNotionReader(chapterId, content, notion) {
  function saveProgress(patch) {
    api.saveCourseProgress(chapterId, notion.id, patch, getStoredClassLevel()).catch(() => {});
  }

  // ── Bloc figure : SEULE section du cours en deux colonnes (graphique à
  // gauche, sa fiche d'explication dédiée à droite), insérée dans le fil de
  // lecture pleine largeur exactement là où la figure apparaît naturellement
  // (juste après la Définition) — le reste du cours reste en une seule
  // colonne. La colonne de droite est une suite de petites cartes typées
  // (schéma `figure.explication`, tout optionnel) plutôt qu'un simple
  // paragraphe, pour se lire comme une vraie fiche pédagogique :
  //   resume        : chapeau de 2-3 lignes au-dessus des cartes
  //   comprendre    : explication intuitive (analogie, langage simple)
  //   lecture[]     : comment lire le graphique (axes, points, couleurs...)
  //   observations[]: ce que l'on observe concrètement sur CE graphique
  //   etapes[]      : { titre, texte } — le calcul associé, étape par étape
  //   astuce        : astuce de mémorisation
  //   pieges[]      : erreurs / confusions classiques
  //   aRetenir[]    : résumé ultra-court (3-4 points max)
  // Repli : si `explication` est absent, on retombe sur `figure.alt` seul
  // (légende courte) pour ne jamais laisser la figure sans texte. Pas de
  // position sticky : si les cartes sont plus hautes que le graphique,
  // elles continuent naturellement dessous, sans espace vide (la grille
  // aligne juste le haut des deux colonnes). ──────────────────────────────
  function figureCard(variant, iconName, title, bodyHtml) {
    return `
      <div class="cours-box cours-figure-card cours-box--${variant}">
        <div class="cours-box-header">${icon(iconName)} <span>${title}</span></div>
        ${bodyHtml}
      </div>
    `;
  }
  function figureCardList(items) {
    return `<ul class="cours-box-list">${items.map((t) => `<li data-text="${encodeURIComponent(t)}"></li>`).join("")}</ul>`;
  }
  function buildFigureExplicationHtml(exp) {
    const cards = [];
    if (exp.comprendre) {
      cards.push(figureCard("simple", "lightbulb", "Ce qu'il faut comprendre",
        `<div class="cours-box-body" data-text="${encodeURIComponent(exp.comprendre)}"></div>`));
    }
    if (exp.lecture?.length) {
      cards.push(figureCard("lecture", "eye", "Comment lire le graphique ?", figureCardList(exp.lecture)));
    }
    if (exp.observations?.length) {
      cards.push(figureCard("observations", "penSquare", "Ce que montre ce graphique", figureCardList(exp.observations)));
    }
    if (exp.etapes?.length) {
      cards.push(figureCard("etapes", "compass", "Comment faire le calcul ?", `
        <div class="cours-figure-etapes">
          ${exp.etapes.map((e, i) => `
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${i + 1}</span>
              <div>
                <div class="cours-figure-etape-titre" data-text="${encodeURIComponent(e.titre || `Étape ${i + 1}`)}"></div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(e.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `));
    }
    if (exp.astuce) {
      cards.push(figureCard("astuce", "lightbulb", "Astuce NovaMath",
        `<div class="cours-box-body" data-text="${encodeURIComponent(exp.astuce)}"></div>`));
    }
    if (exp.pieges?.length) {
      cards.push(figureCard("attention", "x", "À ne pas confondre", figureCardList(exp.pieges)));
    }
    if (exp.aRetenir?.length) {
      cards.push(figureCard("aretenir", "star", "À retenir", figureCardList(exp.aRetenir.slice(0, 4))));
    }
    return `
      ${exp.resume ? `<p class="cours-figure-resume" data-text="${encodeURIComponent(exp.resume)}"></p>` : ""}
      <div class="cours-figure-cards">${cards.join("")}</div>
    `;
  }
  // ── Repli automatique — la grande majorité des figures du site n'ont pas
  // (encore) de `figure.explication` rédigée à la main. Plutôt que de
  // laisser la colonne de droite avec une seule phrase (`figure.alt`), on
  // reconstruit une fiche à plusieurs cartes à partir du contenu RÉEL déjà
  // écrit pour la notion (explicationSimple, méthode, astuce, erreurs
  // fréquentes, à retenir — présents sur la quasi-totalité des notions) :
  // aucune invention, juste la même matière que le reste du cours,
  // recomposée pour accompagner directement le graphique. ─────────────────
  function deriveFigureExplicationFromNotion(notion, figure) {
    const exp = {};
    if (notion.explicationSimple || notion.intuition) {
      exp.comprendre = notion.explicationSimple || notion.intuition;
    }
    if (figure.alt) exp.observations = [figure.alt];
    // La méthode reste affichée une seule fois, en colonne unique juste
    // au-dessus des exemples (qui s'y réfèrent directement) — elle n'est
    // donc jamais déplacée dans la carte, contrairement à astuce/erreurs.
    if (notion.astuce) exp.astuce = notion.astuce;
    if (notion.erreursFrequentes?.length) exp.pieges = notion.erreursFrequentes;
    if (notion.aRetenir?.length) exp.aRetenir = notion.aRetenir;
    return exp;
  }
  // `figure.emphasis` (optionnel) : agrandit la colonne graphique (56/44 au
  // lieu de 44/56) — réservé aux figures qui portent une vraie démonstration.
  // `figure.steps` (optionnel, ex. ["Le triangle", "+ Les aires", "+ La
  // relation"]) : ajoute des pastilles cliquables au-dessus du graphique qui
  // révèlent progressivement les éléments marqués `reveal: 2`/`reveal: 3`
  // dans le spec (voir geomSvg.js). Sans l'un ou l'autre champ, une figure
  // garde exactement son rendu actuel.
  function buildFigureBlockHtml(figure, notion) {
    if (!figure) return "";
    // Une figure malformée (kind inconnu retombé sur renderGeom sans
    // viewBox cohérent, coordonnées invalides...) ne doit jamais empêcher
    // l'affichage du reste de la notion (texte, méthode, exemples) — voir
    // audit du système de figures : aucun garde-fou n'existait avant.
    let svg;
    try {
      svg = renderFigure(figure);
    } catch (err) {
      console.warn(`Figure invalide pour la notion "${notion?.id}" :`, err);
      return "";
    }
    const explication = figure.explication || deriveFigureExplicationFromNotion(notion, figure);
    const hasContent = Object.keys(explication).length > 0;
    const rightCol = hasContent ? buildFigureExplicationHtml(explication)
      : figure.alt ? `<p class="cours-figure-caption-text" data-text="${encodeURIComponent(figure.alt)}"></p>` : "";
    const stepsHtml = figure.steps?.length ? `
      <div class="cours-figure-steps" role="tablist" aria-label="Étapes de la figure">
        ${figure.steps.map((s, i) => `<button type="button" class="cours-figure-step-btn${i === 0 ? " is-active" : ""}" data-step="${i + 1}" role="tab" aria-selected="${i === 0}">${i + 1}. ${s}</button>`).join("")}
      </div>
      <div class="cours-figure-nav">
        <button type="button" class="btn btn-ghost btn-sm cours-figure-prev-btn" data-total-steps="${figure.steps.length}" disabled>${icon("arrowLeft")} Précédent</button>
        <button type="button" class="btn btn-ghost btn-sm cours-figure-replay-btn">${icon("rotate")} Rejouer l'animation</button>
        <button type="button" class="btn btn-ghost btn-sm cours-figure-next-btn" data-total-steps="${figure.steps.length}">Suivant ${icon("arrowRight")}</button>
      </div>` : "";
    // `figure.relation` (optionnel) : formule finale (ex. "a²+b²=c²"), révélée
    // en même temps que la dernière étape (`reveal-3`) — rendue en HTML/KaTeX
    // plutôt que dans le SVG pour une meilleure qualité typographique.
    const relationHtml = figure.relation ? `<div class="cours-figure-relation reveal-3" data-text="${encodeURIComponent(figure.relation)}"></div>` : "";
    return `
      <div class="cours-figure-layout${figure.emphasis ? " cours-figure-layout--xl" : ""}">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap${figure.emphasis ? " cours-figure-wrap--xl" : ""}" data-step="1">
            ${stepsHtml}
            ${svg}
            ${relationHtml}
          </div>
        </div>
        ${rightCol ? `<div class="cours-figure-text-col">${rightCol}</div>` : ""}
      </div>
    `;
  }

  // ── Quand la fiche du graphique est reconstruite à partir du contenu de
  // la notion (repli automatique, voir deriveFigureExplicationFromNotion),
  // ce contenu est DÉPLACÉ dans les cartes plutôt que dupliqué : les
  // sections correspondantes (Pour bien comprendre, Méthode, Astuce,
  // Erreurs fréquentes) ne sont alors pas répétées plus bas en colonne
  // unique. Quand une `figure.explication` est rédigée à la main (contenu
  // propre au graphique, différent du reste du cours), rien n'est masqué.
  const usesFallbackFigureCards = !!(notion.figure && !notion.figure.explication);

  readerView.innerHTML = `
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${icon("arrowLeft")} ${resolveChapterTitle(content.title, content.notions.map((n) => n.title)) || chapterId.replace(/_/g, " ")}</button>
    </div>

    <h1 class="cours-notion-title">${notion.title}</h1>
    <p class="cours-intro-text" data-text="${encodeURIComponent(notion.intro || "")}"></p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${icon("target")}</div>
      <p data-text="${encodeURIComponent(notion.objectif || "")}"></p>
    </div>

    ${notion.pourquoi ? `
    <div class="cours-box cours-box--pourquoi">
      <div class="cours-box-header">${icon("sparkles")} <span>Pourquoi apprend-on cela ?</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.pourquoi)}"></div>
    </div>` : ""}
    ${questionsEclairHtml(notion, "pourquoi")}

    ${notion.explicationSimple && !usesFallbackFigureCards ? `
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${icon("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.explicationSimple)}"></div>
    </div>` : ""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${icon("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.definition || "")}"></div>
    </div>

    ${buildFigureBlockHtml(notion.figure, notion)}
    ${questionsEclairHtml(notion, "figure")}

    ${notion.intuition ? `
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${icon("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.intuition)}"></div>
    </div>` : ""}
    ${questionsEclairHtml(notion, "intuition")}

    ${notion.exemplesConcrets?.length ? `
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${icon("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${notion.exemplesConcrets.map((c) => `<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    ${notion.reglesImportantes?.length ? `
    <div class="cours-section-label">${icon("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${notion.reglesImportantes.map((r) => `<div class="card cours-regle-card" data-text="${encodeURIComponent(r)}"></div>`).join("")}
    </div>` : ""}

    ${notion.remarques?.length ? `
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${icon("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${notion.remarques.map((r) => `<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    ${notion.methode?.etapes?.length ? `
    <div class="cours-section-label">${icon("compass")} <span data-text="${encodeURIComponent(notion.methode.titre || "Méthode")}"></span></div>
    ${buildStepsHtml(notion.methode.etapes)}` : ""}
    ${questionsEclairHtml(notion, "methode")}

    ${notion.exemples?.length ? `
    <div class="cours-section-label">${icon("penSquare")} Exemples</div>
    ${notion.exemples.map((ex) => buildExempleHtml(ex) + questionsEclairHtml(notion, `exemple:${ex.id}`)).join("")}` : ""}
    ${buildLockedPremiumHtml(notion.locked_content)}

    ${notion.demonstration?.etapes?.length ? `
    <div class="cours-section-label">${icon("compass")} <span data-text="${encodeURIComponent(notion.demonstration.titre || "Démonstration")}"></span></div>
    ${buildStepsHtml(notion.demonstration.etapes.map((e) => ({
      texte: e.titre ? `${e.titre} — ${e.texte}` : e.texte,
    })))}
    ${notion.demonstration.conclusion ? `
    <div class="cours-box cours-box--simple">
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.demonstration.conclusion)}"></div>
    </div>` : ""}` : ""}
    ${buildLockedUltraHtml(notion.locked_content)}

    ${notion.erreursFrequentes?.length && !usesFallbackFigureCards ? `
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${icon("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${notion.erreursFrequentes.map((e) => `<li data-text="${encodeURIComponent(e)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    ${notion.astuce && !usesFallbackFigureCards ? `
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${icon("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.astuce)}"></div>
    </div>` : ""}

    ${notion.aRetenir?.length ? `
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${icon("star")} ${notion.resume ? "À retenir" : "Résumé — à retenir"}</div>
      <ul class="cours-aretenir-list">
        ${notion.aRetenir.slice(0, 6).map((r) => `<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    ${notion.resume ? `
    <div class="card cours-resume-card">
      <div class="cours-resume-title">${icon("trophy")} Résumé de la leçon</div>
      <p class="cours-resume-text" data-text="${encodeURIComponent(notion.resume)}"></p>
    </div>` : ""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${notion.quizExerciseIds?.length ? "hidden" : ""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${icon("check")} J'ai terminé cette leçon</button>
    </div>

    <div class="support-report-row">
      <button id="cours-report-btn" class="support-report-link" type="button">
        ${icon("flag")} Ce cours contient une erreur ? Signaler
      </button>
    </div>

    ${notionNavHtml(content, notion)}
  `;

  renderMathAttrs(readerView);
  fadeInTransition(readerView);

  readerView.querySelector("#cours-back-to-chapter").addEventListener("click", () => renderChapterDetail(chapterId, content));
  readerView.querySelector("#cours-report-btn").addEventListener("click", () => {
    openReportTicketPopup({
      sourceLabel: "Cours",
      defaultCategory: "bug",
      contextLines: [
        { label: "Chapitre", value: chapterId },
        { label: "Leçon", value: notion.title },
        { label: "Classe", value: getStoredClassLevel() },
        { label: "URL", value: window.location.href },
      ],
    });
  });
  // Étapes de révélation progressive de la figure (voir figure.steps) — ne
  // fait rien si la notion n'a pas de figure à étapes (aucun bouton rendu).
  // `goToFigureStep` centralise le changement d'étape (pastille cliquée,
  // Précédent/Suivant, Rejouer) pour garder l'état des pastilles et des
  // boutons Précédent/Suivant toujours synchronisé avec `data-step`.
  function goToFigureStep(wrap, step) {
    const total = wrap.querySelectorAll(".cours-figure-step-btn").length;
    const clamped = Math.max(1, Math.min(total, step));
    wrap.dataset.step = clamped;
    wrap.querySelectorAll(".cours-figure-step-btn").forEach((b) => {
      const isActive = Number(b.dataset.step) === clamped;
      b.classList.toggle("is-active", isActive);
      b.setAttribute("aria-selected", String(isActive));
    });
    const prevBtn = wrap.querySelector(".cours-figure-prev-btn");
    const nextBtn = wrap.querySelector(".cours-figure-next-btn");
    if (prevBtn) prevBtn.disabled = clamped === 1;
    if (nextBtn) nextBtn.disabled = clamped === total;
  }
  readerView.querySelectorAll(".cours-figure-step-btn").forEach((btn) => {
    btn.addEventListener("click", () => goToFigureStep(btn.closest(".cours-figure-wrap"), Number(btn.dataset.step)));
  });
  readerView.querySelectorAll(".cours-figure-prev-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const wrap = btn.closest(".cours-figure-wrap");
      goToFigureStep(wrap, Number(wrap.dataset.step) - 1);
    });
  });
  readerView.querySelectorAll(".cours-figure-next-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const wrap = btn.closest(".cours-figure-wrap");
      goToFigureStep(wrap, Number(wrap.dataset.step) + 1);
    });
  });
  readerView.querySelectorAll(".cours-figure-replay-btn").forEach((btn) => {
    btn.addEventListener("click", () => goToFigureStep(btn.closest(".cours-figure-wrap"), 1));
  });
  // Exemples interactifs (voir `ex.interactif`) : révèle le calcul étape par
  // étape puis la correction complète, au lieu de tout afficher d'un coup.
  // N'affecte que les exemples qui portent explicitement ce champ.
  readerView.querySelectorAll(".cours-exemple-next-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const card = btn.closest(".cours-exemple-card");
      const total = Number(card.dataset.totalSteps);
      let revealed = Number(card.dataset.revealed);
      if (revealed < total) {
        revealed += 1;
        card.dataset.revealed = revealed;
        card.querySelector(`.cours-calc-row[data-calc-index="${revealed - 1}"]`)?.classList.remove("cours-calc-row--hidden");
        card.querySelector(`.cours-calc-arrow[data-calc-index="${revealed - 1}"]`)?.classList.remove("cours-calc-row--hidden");
        btn.innerHTML = revealed === total
          ? `${icon("check")} Voir la correction complète`
          : `${icon("eye")} Voir l'étape suivante (${revealed}/${total})`;
      } else {
        card.querySelector(".cours-exemple-correction")?.classList.remove("cours-exemple-correction--hidden");
        btn.remove();
      }
    });
  });
  // Questions éclair (voir `notion.questionsEclair`) : bouton "Voir une
  // piste" qui affiche l'indice au clic — aucune notion existante n'a ce
  // champ, donc aucun bouton n'est rendu ailleurs.
  readerView.querySelectorAll(".cours-question-eclair-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const piste = decodeURIComponent(btn.dataset.piste);
      const box = btn.nextElementSibling;
      setMathContent(box, piste);
      box.hidden = false;
      btn.remove();
    }, { once: true });
  });
  // `notion.uxAnimations` (optionnel, réservé pour l'instant à la notion
  // pilote) : légère apparition en fondu + translation des cartes au
  // défilement, jamais tape-à-l'œil. Sans ce champ, aucun observateur n'est
  // créé et aucune notion existante ne change d'apparence.
  if (notion.uxAnimations && "IntersectionObserver" in window) {
    const animatedEls = readerView.querySelectorAll(".cours-box, .card, .cours-regle-card, .cours-question-eclair");
    animatedEls.forEach((el) => el.classList.add("cours-anim"));
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    animatedEls.forEach((el) => observer.observe(el));
  }
  readerView.querySelectorAll(".cours-notion-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = content.notions.find((n) => n.id === btn.dataset.notion);
      if (target) openNotionReader(chapterId, content, target);
    });
  });

  saveProgress({ status: "in_progress" });

  if (notion.quizExerciseIds?.length) {
    renderQuiz(readerView.querySelector("#cours-quiz-zone"));
  } else {
    readerView.querySelector("#cours-mark-done-btn")?.addEventListener("click", () => {
      saveProgress({ status: "done" });
      readerView.querySelector("#cours-done-row").innerHTML = `<span class="cours-done-confirm">${icon("check")} Leçon terminée !</span>`;
    });
  }

  async function renderQuiz(zone) {
    zone.innerHTML = `<div class="skeleton" style="height:140px;"></div>`;
    let exercises;
    try {
      exercises = await Promise.all(
        notion.quizExerciseIds.map((id) => api.exercise(id, getStoredClassLevel()).then((r) => r.exercise)),
      );
    } catch {
      zone.innerHTML = "";
      saveProgress({ status: "done" });
      return;
    }
    let qIndex = 0;
    let score = 0;

    function renderQuestion() {
      if (qIndex >= exercises.length) {
        zone.innerHTML = `<div class="card cours-quiz-done">${icon("check")} Mini-quiz terminé : <strong>${score}/${exercises.length}</strong> bonnes réponses.</div>`;
        fadeInTransition(zone.querySelector(".cours-quiz-done"));
        saveProgress({ status: "done", quizScore: score, quizTotal: exercises.length });
        return;
      }
      const ex = exercises[qIndex];
      const quizPct = Math.round((qIndex / exercises.length) * 100);
      zone.innerHTML = `
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${icon("lightbulb")} Mini-quiz — question ${qIndex + 1}/${exercises.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${quizPct}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${icon("check")} J'ai réussi</button>
          </div>
        </div>
      `;
      fadeInTransition(zone.querySelector(".cours-quiz-card"));
      setMathContent(zone.querySelector("#cours-quiz-enonce"), ex.enonce);
      zone.querySelector("#cours-quiz-reveal").addEventListener("click", () => {
        const answerEl = zone.querySelector("#cours-quiz-answer");
        answerEl.hidden = false;
        setMathContent(answerEl, `Réponse : ${ex.answer}${ex.hint ? `\nIndice : ${ex.hint}` : ""}`);
        zone.querySelector("#cours-quiz-reveal").hidden = true;
        zone.querySelector("#cours-quiz-verdict").hidden = false;
      });
      zone.querySelector("#cours-quiz-fail").addEventListener("click", () => { qIndex += 1; renderQuestion(); });
      zone.querySelector("#cours-quiz-success").addEventListener("click", () => { score += 1; qIndex += 1; renderQuestion(); });
    }
    renderQuestion();
  }
}

// ── Init ─────────────────────────────────────────────────────────────────
async function openRequestedNotion(chapterId, notionId) {
  await openChapter(chapterId);
  const content = await loadChapterContent(chapterId);
  const notion = content.notions.find((n) => n.id === notionId);
  if (!notion) return;
  openNotionReader(chapterId, content, notion);
}

// ── Classe sans cours déclarés (curriculum_registry.py::courses_dir absent) ─
// La classe active peut avoir des exercices sans avoir de cours (ex.
// Première aujourd'hui) : jamais de repli silencieux sur les chapitres
// Seconde dans ce cas, un état vide honnête à la place.
function renderNoCoursesState() {
  grid.innerHTML = `
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${icon("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `;
}

// ── Recherche (chapitre / notion / mot-clé) ─────────────────────────────────
// Index construit UNE SEULE FOIS dans init() ci-dessous, à partir de
// chaptersMeta déjà en mémoire (chapterTitle + notions_cours, déjà chargés
// pour la grille) — jamais de requête réseau ni de contenu de chapitre
// chargé juste pour indexer : la recherche porte sur les données, pas sur le
// DOM ni sur un chargement paresseux supplémentaire.
let searchIndex = [];

function buildSearchIndex() {
  searchIndex = chaptersMeta.flatMap((ch) => {
    const chapterTitle = resolveChapterTitle(ch.title, ch.notions_cours) || ch.id.replace(/_/g, " ");
    const chapterEntry = { type: "chapter", chapterId: ch.id, chapterTitle, notionTitle: null, norm: normalizeText(chapterTitle) };
    const notionEntries = (ch.notions_cours || []).map((notionTitle) => ({
      type: "notion", chapterId: ch.id, chapterTitle, notionTitle,
      norm: normalizeText(`${chapterTitle} ${notionTitle}`),
      notionNorm: normalizeText(notionTitle),
    }));
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

const searchInput = document.getElementById("cours-search-input");
const searchClearBtn = document.getElementById("cours-search-clear");
const searchResultsEl = document.getElementById("cours-search-results");

/** Assombrit (sans les retirer du flux) les cartes qui ne correspondent pas
 * à la recherche en cours — même mécanique que chapitres.js. */
function applySearchDim(query) {
  const q = normalizeText(query);
  grid.querySelectorAll(".chapter-card").forEach((card) => {
    if (!q) { card.classList.remove("is-search-dimmed"); return; }
    const ch = chaptersMeta.find((c) => c.id === card.dataset.id);
    const chapterTitle = ch ? (resolveChapterTitle(ch.title, ch.notions_cours) || ch.id) : "";
    const matches = normalizeText(chapterTitle).includes(q)
      || (ch?.notions_cours || []).some((t) => normalizeText(t).includes(q));
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
    <button type="button" class="page-search-item${i === 0 ? " is-active" : ""}" role="option">
      <span class="title">${icon(r.type === "chapter" ? "bookOpen" : "layers")}${r.type === "chapter" ? r.chapterTitle : r.notionTitle}</span>
      <span class="subtitle">${r.type === "chapter" ? "Chapitre" : `${r.chapterTitle} — Notion`}</span>
    </button>
  `).join("");
  results.forEach((r, i) => {
    searchResultsEl.children[i].addEventListener("click", () => pickSearchResult(r));
  });
}

/** Ouvre directement le bon chapitre puis, pour une notion, scrolle jusqu'à
 * sa carte précise (retrouvée par titre — notions_cours et content.notions
 * partagent la même source, voir generate_cours_from_bank.py) en la mettant
 * brièvement en évidence. */
async function pickSearchResult(result) {
  searchInput.value = result.type === "chapter" ? result.chapterTitle : result.notionTitle;
  searchResultsEl.hidden = true;
  await openChapter(result.chapterId);
  if (result.type !== "notion") return;
  const content = await loadChapterContent(result.chapterId);
  const notion = content.notions.find((n) => normalizeText(n.title) === normalizeText(result.notionTitle));
  if (!notion) return;
  const card = readerView.querySelector(`.cours-notion-card[data-notion="${CSS.escape(notion.id)}"]`);
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.add("notion-row--highlight");
    setTimeout(() => card.classList.remove("notion-row--highlight"), 1600);
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
      active?.click();
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

async function init() {
  const classLevel = getStoredClassLevel();
  let hasCourses = true;
  try {
    const curricula = await fetchCurricula();
    const current = curricula.find((c) => c.classLevel === classLevel);
    hasCourses = current ? current.hasCourses !== false : true;
  } catch {
    hasCourses = true; // info indisponible (réseau) : on ne bloque pas Seconde par prudence
  }

  if (!hasCourses) {
    renderNoCoursesState();
    return;
  }

  const [chaptersData, progress] = await Promise.all([
    api.chapters(classLevel), api.getCourseProgress(classLevel).catch(() => ({})),
  ]);
  chaptersMeta = chaptersData.chapters_meta || [];
  courseProgress = progress || {};
  renderGrid();
  buildSearchIndex();

  const params = new URLSearchParams(window.location.search);
  const chapterId = params.get("chapter");
  const notionId = params.get("notion");
  if (chapterId && notionId) {
    openRequestedNotion(chapterId, notionId);
  } else if (chapterId) {
    openChapter(chapterId);
  }
}

init();

onSettingsChange((e) => {
  if (!["appearance", "*"].includes(e.detail.category)) return;
  if (!listView.hidden) renderGrid();
});
