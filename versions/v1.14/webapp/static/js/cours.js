import { api } from "./api.js";
import { initSettingsManager, onSettingsChange } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { icon } from "./icons.js";
import { bindLiveTranslations } from "./i18n.js";
import { setMathContent } from "./mathrender.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const listView = document.getElementById("cours-list-view");
const readerView = document.getElementById("cours-reader-view");
const grid = document.getElementById("cours-grid");

// ── Mode invité : mêmes règles que Chapitres (2 chapitres max), et aucune
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
      <h3>${ch.title}</h3>
      <div class="chapter-id">${ch.id.replace("_", " ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${stats.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${stats.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>📚 ${ch.n_notions} notion${ch.n_notions > 1 ? "s" : ""}</span>
        <span>✅ ${stats.doneCount}/${stats.total} terminée${stats.doneCount > 1 ? "s" : ""}</span>
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
async function loadChapterContent(chapterId) {
  if (contentCache.has(chapterId)) return contentCache.get(chapterId);
  const num = chapterId.replace("Chapitre_", "");
  const res = await fetch(`data/cours/chapitre_${num}.json`);
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

  readerView.innerHTML = `<div class="skeleton" style="height:220px;"></div>`;
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
  readerView.innerHTML = `
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${icon("arrowLeft")} Tous les cours</button>
    </div>
    <div class="page-header">
      <div>
        <h1>${content.title}</h1>
        <div class="chapter-id">${chapterId.replace("_", " ")}</div>
      </div>
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
            <span>${n.sections.length} sections</span>
            ${cp[n.id]?.quizTotal ? `<span>Quiz : ${cp[n.id].quizScore}/${cp[n.id].quizTotal}</span>` : ""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${icon("play")} ${status === "todo" ? "Commencer" : status === "done" ? "Relire" : "Continuer"}
          </button>
        </div>`;
      }).join("")}
    </div>
  `;
  readerView.querySelector("#cours-back-to-grid").addEventListener("click", () => {
    renderGrid();
    showListView();
  });
  readerView.querySelectorAll(".cours-read-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const notionId = e.target.closest(".cours-notion-card").dataset.notion;
      const notion = content.notions.find((n) => n.id === notionId);
      const startSection = cp[notionId]?.lastSection || 0;
      openNotionReader(chapterId, content, notion, Math.min(startSection, notion.sections.length - 1));
    });
  });
}

// ── Rendu d'une section selon son type ──────────────────────────────────────
const SECTION_LABELS = {
  definition: "Définition", propriete: "Propriété", methode: "Méthode",
  exemple: "Exemple résolu", attention: "Attention", astuce: "Astuce", tableau: "Tableau",
};
const SECTION_ICONS = {
  definition: "bookOpen", propriete: "check", methode: "compass",
  exemple: "lightbulb", attention: "helpCircle", astuce: "star", tableau: "layers",
};

function renderSection(section) {
  const label = SECTION_LABELS[section.type] || "";
  const box = document.createElement("div");
  box.className = `cours-box cours-box--${section.type}`;
  const header = section.title || label;
  let bodyHtml = `<div class="cours-box-header">${icon(SECTION_ICONS[section.type] || "info")} <span>${header}</span></div>`;
  box.innerHTML = bodyHtml;

  if (section.type === "exemple") {
    const enonceEl = document.createElement("div");
    enonceEl.className = "cours-exemple-enonce";
    box.appendChild(enonceEl);
    setMathContent(enonceEl, section.enonce);

    (section.etapes || []).forEach((step, i) => {
      const stepEl = document.createElement("div");
      stepEl.className = "cours-exemple-etape";
      box.appendChild(stepEl);
      setMathContent(stepEl, `Étape ${i + 1} : ${step}`);
    });

    const reponseEl = document.createElement("div");
    reponseEl.className = "cours-exemple-reponse";
    box.appendChild(reponseEl);
    setMathContent(reponseEl, `Réponse : ${section.reponse}`);
  } else if (section.type === "methode") {
    const list = document.createElement("ol");
    list.className = "cours-methode-steps";
    (section.steps || []).forEach((step) => {
      const li = document.createElement("li");
      list.appendChild(li);
      setMathContent(li, step);
    });
    box.appendChild(list);
  } else if (section.type === "tableau") {
    const table = document.createElement("table");
    table.className = "cours-table";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    (section.headers || []).forEach((h) => {
      const th = document.createElement("th");
      headRow.appendChild(th);
      setMathContent(th, h);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    (section.rows || []).forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((cell) => {
        const td = document.createElement("td");
        tr.appendChild(td);
        setMathContent(td, cell);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    box.appendChild(table);
  } else {
    const bodyEl = document.createElement("div");
    bodyEl.className = "cours-box-body";
    box.appendChild(bodyEl);
    setMathContent(bodyEl, section.body || "");
  }

  return box;
}

// ── Lecteur de notion : navigation section par section + quiz final ────────
function openNotionReader(chapterId, content, notion, startIndex = 0) {
  let sectionIndex = Math.max(0, Math.min(startIndex, notion.sections.length - 1));
  let onQuiz = false;

  function saveProgress(patch) {
    api.saveCourseProgress(chapterId, notion.id, patch).catch(() => {});
  }

  function renderStep() {
    if (!onQuiz) {
      const section = notion.sections[sectionIndex];
      const progressPct = Math.round(((sectionIndex + 1) / notion.sections.length) * 100);
      readerView.innerHTML = `
        <div class="cours-back-row">
          <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${icon("arrowLeft")} ${content.title}</button>
        </div>
        <div class="cours-notion-header">
          <h1>${notion.title}</h1>
          <div class="progress-track" style="max-width:320px;"><div class="progress-fill" style="width:${progressPct}%"></div></div>
          <div class="cours-notion-progress-label">Section ${sectionIndex + 1} / ${notion.sections.length}</div>
        </div>
        ${sectionIndex === 0 && (notion.objectifs?.length || notion.prerequis?.length) ? `
        <div class="cours-intro-row">
          ${notion.objectifs?.length ? `<div class="card cours-intro-card"><h4>${icon("target")} Objectifs</h4><ul>${notion.objectifs.map((o) => `<li>${o}</li>`).join("")}</ul></div>` : ""}
          ${notion.prerequis?.length ? `<div class="card cours-intro-card"><h4>${icon("compass")} Prérequis</h4><ul>${notion.prerequis.map((p) => `<li>${p}</li>`).join("")}</ul></div>` : ""}
        </div>` : ""}
        <div id="cours-section-slot"></div>
        <div class="cours-nav-row">
          <button class="btn btn-secondary" id="cours-prev-btn" type="button" ${sectionIndex === 0 ? "disabled" : ""}>${icon("arrowLeft")} Précédent</button>
          <button class="btn btn-primary" id="cours-next-btn" type="button">${sectionIndex === notion.sections.length - 1 ? "Résumé et quiz" : "Suivant"} ${icon("arrowRight")}</button>
        </div>
      `;
      readerView.querySelector("#cours-section-slot").appendChild(renderSection(section));
      readerView.querySelector("#cours-back-to-chapter").addEventListener("click", () => renderChapterDetail(chapterId, content));
      readerView.querySelector("#cours-prev-btn").addEventListener("click", () => {
        sectionIndex = Math.max(0, sectionIndex - 1);
        saveProgress({ status: "in_progress", lastSection: sectionIndex });
        renderStep();
      });
      readerView.querySelector("#cours-next-btn").addEventListener("click", () => {
        if (sectionIndex === notion.sections.length - 1) {
          onQuiz = true;
          saveProgress({ status: "in_progress", lastSection: sectionIndex });
          renderStep();
        } else {
          sectionIndex += 1;
          saveProgress({ status: "in_progress", lastSection: sectionIndex });
          renderStep();
        }
      });
      saveProgress({ status: "in_progress", lastSection: sectionIndex });
    } else {
      renderSummaryAndQuiz();
    }
  }

  function renderSummaryAndQuiz() {
    readerView.innerHTML = `
      <div class="cours-back-row">
        <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${icon("arrowLeft")} ${content.title}</button>
      </div>
      <h1>${notion.title} — Résumé</h1>
      <div class="card cours-resume-card"><p id="cours-resume-text"></p></div>
      ${notion.ficheMemo?.length ? `<div class="card cours-fichememo-card"><h4>${icon("star")} Fiche mémo</h4><ul id="cours-fichememo-list"></ul></div>` : ""}
      <div id="cours-quiz-zone"></div>
      <div class="cours-nav-row">
        <button class="btn btn-secondary" id="cours-back-to-sections" type="button">${icon("arrowLeft")} Revoir le cours</button>
      </div>
    `;
    readerView.querySelector("#cours-back-to-chapter").addEventListener("click", () => renderChapterDetail(chapterId, content));
    readerView.querySelector("#cours-back-to-sections").addEventListener("click", () => { onQuiz = false; renderStep(); });
    setMathContent(readerView.querySelector("#cours-resume-text"), notion.resume || "");
    if (notion.ficheMemo?.length) {
      const list = readerView.querySelector("#cours-fichememo-list");
      notion.ficheMemo.forEach((item) => {
        const li = document.createElement("li");
        list.appendChild(li);
        setMathContent(li, item);
      });
    }
    if (notion.quizExerciseIds?.length) {
      renderQuiz(readerView.querySelector("#cours-quiz-zone"));
    } else {
      saveProgress({ status: "done" });
    }
  }

  async function renderQuiz(zone) {
    zone.innerHTML = `<div class="skeleton" style="height:140px;"></div>`;
    let exercises;
    try {
      exercises = await Promise.all(notion.quizExerciseIds.map((id) => api.exercise(id).then((r) => r.exercise)));
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
        saveProgress({ status: "done", quizScore: score, quizTotal: exercises.length });
        return;
      }
      const ex = exercises[qIndex];
      zone.innerHTML = `
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">${icon("lightbulb")} Mini-quiz — question ${qIndex + 1}/${exercises.length}</div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-secondary" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-primary" id="cours-quiz-success" type="button">${icon("check")} J'ai réussi</button>
          </div>
        </div>
      `;
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

  renderStep();
}

// ── Init ─────────────────────────────────────────────────────────────────
async function openRequestedNotion(chapterId, notionId) {
  await openChapter(chapterId);
  const content = await loadChapterContent(chapterId);
  const notion = content.notions.find((n) => n.id === notionId);
  if (!notion) return;
  const cp = courseProgress[chapterId] || {};
  const startSection = cp[notionId]?.lastSection || 0;
  openNotionReader(chapterId, content, notion, Math.min(startSection, notion.sections.length - 1));
}

Promise.all([api.chapters(), api.getCourseProgress().catch(() => ({}))]).then(([chaptersData, progress]) => {
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
});

onSettingsChange((e) => {
  if (!["appearance", "*"].includes(e.detail.category)) return;
  if (!listView.hidden) renderGrid();
});
