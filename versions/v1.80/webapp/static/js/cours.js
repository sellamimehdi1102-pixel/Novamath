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

function renderGrid() {
  grid.innerHTML = "";
  chaptersMeta.forEach((ch) => {
    const stats = computeChapterStats(ch);
    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;
    card.innerHTML = `
      <div class="chapter-card-top">
        <div class="chapter-icon">${chapterIcon()}</div>
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
    grid.appendChild(card);
  });
}

// ── Chargement paresseux du contenu (un seul chapitre à la fois) ───────────
// Dossier par classe (curriculum_registry.py::courses_dir) — "seconde" reste
// "data/cours/" (chemin historique, jamais renommé), toute autre classe lit
// "data/cours_<classe>/" (voir generate_cours_from_bank.py). Le cache
// mémoire n'a pas besoin d'être scopé par classe : changer de classe
// recharge toujours la page (curriculumSelector.js), qui repart d'un cache
// vide.
function coursDirFor(classLevel) {
  return classLevel === "seconde" ? "cours" : `cours_${classLevel}`;
}

async function loadChapterContent(chapterId) {
  if (contentCache.has(chapterId)) return contentCache.get(chapterId);
  const num = chapterId.replace("Chapitre_", "");
  const dir = coursDirFor(getStoredClassLevel());
  const res = await fetch(`data/${dir}/chapitre_${num}.json`);
  if (!res.ok) throw new Error("Contenu introuvable pour " + chapterId);
  const data = await res.json();
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

  const content = await loadChapterContent(chapterId);
  renderChapterDetail(chapterId, content);
}

function notionStatusBadge(status) {
  if (status === "done") return `<span class="badge badge--success">Terminée</span>`;
  if (status === "in_progress") return `<span class="badge badge--warning">En cours</span>`;
  return `<span class="badge badge--neutral">À lire</span>`;
}

function renderChapterDetail(chapterId, content) {
  const cp = courseProgress[chapterId] || {};
  // Repère de progression du chapitre — présentation pure, réutilise le même
  // calcul que la grille (computeChapterStats), aucune nouvelle donnée.
  const meta = chaptersMeta.find((c) => c.id === chapterId);
  const stats = meta ? computeChapterStats(meta) : null;

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
        const status = cp[n.id]?.status || "todo";
        return `
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <h3>${n.title}</h3>
            ${notionStatusBadge(status)}
          </div>
          <div class="cours-notion-meta">
            <span>${(n.exemples || []).length} exemple${(n.exemples || []).length > 1 ? "s" : ""}</span>
            ${cp[n.id]?.quizTotal ? `<span>Quiz : ${cp[n.id].quizScore}/${cp[n.id].quizTotal}</span>` : ""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${icon("play")} ${status === "todo" ? "Commencer" : status === "done" ? "Relire" : "Continuer"}
          </button>
        </div>`;
      }).join("")}
    </div>
  `;
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
function buildExempleHtml(ex) {
  const calcHtml = (ex.calcul || []).map((c, i, arr) => `
    <div class="cours-calc-row">
      <div class="cours-calc-expr" data-text="${encodeURIComponent(`$${c.expr}$`)}"></div>
      <div class="cours-calc-texte" data-text="${encodeURIComponent(c.texte)}"></div>
    </div>
    ${i < arr.length - 1 ? `<div class="cours-calc-arrow">${ICONS.arrowRight}</div>` : ""}
  `).join("");
  return `
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${icon("penSquare")} ${ex.titre || "Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(ex.enonce)}"></div>
      <div class="cours-calc-block">${calcHtml}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : " + ex.reponse)}"></div>
    </div>
  `;
}

function renderMathAttrs(root) {
  root.querySelectorAll("[data-text]").forEach((el) => {
    setMathContent(el, decodeURIComponent(el.dataset.text));
    el.removeAttribute("data-text");
  });
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

  readerView.innerHTML = `
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${icon("arrowLeft")} ${resolveChapterTitle(content.title, content.notions.map((n) => n.title)) || chapterId.replace(/_/g, " ")}</button>
    </div>

    <h1 class="cours-notion-title">${notion.title}</h1>
    <p class="cours-intro-text">${notion.intro || ""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${icon("target")}</div>
      <p>${notion.objectif || ""}</p>
    </div>

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${icon("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.definition || "")}"></div>
    </div>

    ${notion.figure ? `<div class="cours-figure-wrap">${renderFigure(notion.figure)}${notion.figure.alt ? `<div class="cours-figure-caption">${notion.figure.alt}</div>` : ""}</div>` : ""}

    ${notion.reglesImportantes?.length ? `
    <div class="cours-section-label">${icon("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${notion.reglesImportantes.map((r) => `<div class="card cours-regle-card" data-text="${encodeURIComponent(r)}"></div>`).join("")}
    </div>` : ""}

    ${notion.methode?.etapes?.length ? `
    <div class="cours-section-label">${icon("compass")} ${notion.methode.titre || "Méthode"}</div>
    ${buildStepsHtml(notion.methode.etapes)}` : ""}

    ${notion.exemples?.length ? `
    <div class="cours-section-label">${icon("penSquare")} Exemples</div>
    ${notion.exemples.map(buildExempleHtml).join("")}` : ""}

    ${notion.erreursFrequentes?.length ? `
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${icon("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${notion.erreursFrequentes.map((e) => `<li data-text="${encodeURIComponent(e)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    ${notion.astuce ? `
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${icon("lightbulb")} <span>Astuce</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(notion.astuce)}"></div>
    </div>` : ""}

    ${notion.aRetenir?.length ? `
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${icon("star")} À retenir</div>
      <ul class="cours-aretenir-list">
        ${notion.aRetenir.slice(0, 5).map((r) => `<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>` : ""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${notion.quizExerciseIds?.length ? "hidden" : ""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${icon("check")} J'ai terminé cette leçon</button>
    </div>

    ${notionNavHtml(content, notion)}
  `;

  renderMathAttrs(readerView);
  fadeInTransition(readerView);

  readerView.querySelector("#cours-back-to-chapter").addEventListener("click", () => renderChapterDetail(chapterId, content));
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
