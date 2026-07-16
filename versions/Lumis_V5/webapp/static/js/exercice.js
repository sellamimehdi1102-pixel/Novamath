import { api } from "./api.js";
import { bindThemeToggle } from "./theme.js";
import { setMathContent } from "./mathrender.js";
import { fireConfetti, shakeElement, fadeInTransition } from "./animations.js";
import {
  recordAnswer, getState, createSeriesDraft, addSeriesQuestion, finalizeSeries,
  saveInProgressSeries, getInProgressSeries, clearInProgressSeries,
} from "./store.js";
import { ActivityTimer } from "./timetrack.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const $ = (id) => document.getElementById(id);
const DIFF_XP = { 1: 10, 2: 15, 3: 20 };
const SERIES_TOTAL = 10;
const CHRONO_SECONDS = 45;

let mode = "revisions";
let seriesConfig = {};
let seriesQueue = [];
let seriesIndex = 0;
let draft = null;
let current = null;
let chronoTimer = null;
let chronoRemaining = CHRONO_SECONDS;
const timer = new ActivityTimer();

function pool() {
  try {
    return JSON.parse(localStorage.getItem("lumis:practice_choices")) || [];
  } catch {
    return [];
  }
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function updateLevelLine() {
  try {
    const lvl = JSON.parse(localStorage.getItem("lumis:last_level"));
    if (lvl) {
      $("level-line").textContent = `${lvl.icon} Niveau ${lvl.label}`;
      return;
    }
  } catch { /* pas de niveau connu */ }
  $("level-line").textContent = "Fais d'abord une évaluation pour débloquer l'entraînement adapté.";
}

/** Construit exactement SERIES_TOTAL ids pour une série, avec répétition si le
 * pool disponible (ex: une seule notion) contient moins d'exercices que nécessaire. */
function buildSeriesPool(currentMode) {
  const state = getState();
  let ids;
  if (currentMode === "notion" || seriesConfig.exerciseIds) {
    ids = (seriesConfig.exerciseIds || []).slice();
  } else if (currentMode === "erreurs") {
    ids = [...new Set(state.history.filter((h) => !h.correct && h.id != null).map((h) => h.id))];
  } else {
    ids = pool().map((c) => c.id);
  }
  if (!ids.length) return [];

  const seriesIds = [];
  let shuffled = shuffle(ids);
  while (seriesIds.length < SERIES_TOTAL) {
    if (!shuffled.length) shuffled = shuffle(ids);
    seriesIds.push(shuffled.pop());
  }
  return seriesIds;
}

function emptyMessageFor(m) {
  if (m === "erreurs") return "Aucune erreur enregistrée pour l'instant — bravo ! Reviens ici après une série.";
  if (m === "notion") return "Aucun exercice disponible pour cette notion.";
  return "Fais d'abord une évaluation initiale (page Chapitres) pour débloquer l'entraînement.";
}

function showEmpty(message) {
  $("empty-state").hidden = false;
  $("screen-ex").hidden = true;
  $("screen-recap").hidden = true;
  $("series-topbar").hidden = true;
  $("empty-state").querySelector("p").textContent = message;
}

async function startSeries(newMode, config = {}) {
  mode = newMode;
  seriesConfig = config;
  const ids = buildSeriesPool(mode);
  if (!ids.length) {
    showEmpty(emptyMessageFor(mode));
    return;
  }
  seriesQueue = ids;
  seriesIndex = 0;
  draft = createSeriesDraft({
    mode,
    chapterId: config.chapterId || null,
    notion: config.notion || null,
    total: SERIES_TOTAL,
  });
  $("series-topbar").hidden = false;
  $("screen-recap").hidden = true;
  persistProgress();
  await loadCurrent();
}

async function resumeSeries(snapshot) {
  mode = snapshot.mode;
  seriesConfig = snapshot.seriesConfig || {};
  seriesQueue = snapshot.seriesQueue;
  seriesIndex = snapshot.seriesIndex;
  draft = {
    id: snapshot.draftId,
    startedAt: snapshot.draftStartedAt,
    mode,
    chapterId: seriesConfig.chapterId || null,
    notion: seriesConfig.notion || null,
    total: SERIES_TOTAL,
    questions: snapshot.draftQuestions || [],
  };
  document.querySelectorAll(".mode-pill").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  $("series-topbar").hidden = false;
  $("screen-recap").hidden = true;
  await loadCurrent();
}

function persistProgress() {
  saveInProgressSeries({
    mode,
    seriesConfig,
    seriesQueue,
    seriesIndex,
    draftId: draft.id,
    draftStartedAt: draft.startedAt,
    draftQuestions: draft.questions,
  });
}

async function loadCurrent() {
  const id = seriesQueue[seriesIndex];
  const data = await api.practiceLoad(id);
  current = data.exercise;

  $("series-count").textContent = `Question ${seriesIndex + 1}/${SERIES_TOTAL}`;
  $("series-progress-fill").style.width = `${(seriesIndex / SERIES_TOTAL) * 100}%`;

  $("ex-chapter-badge").textContent = current.chapter_id;
  $("ex-notion-badge").textContent = current.notion || "";
  $("ex-xp-badge").textContent = `+${DIFF_XP[current.difficulty] || 10} XP`;
  setMathContent($("ex-enonce"), current.enonce);
  $("ex-hint").hidden = true;
  $("ex-method").hidden = true;
  $("ex-sol").hidden = true;

  const examMode = mode === "examen";
  $("btn-hint").hidden = examMode;
  $("btn-sol").hidden = examMode;
  $("btn-method").hidden = false;

  $("empty-state").hidden = true;
  $("screen-ex").hidden = false;
  fadeInTransition($("screen-ex"));
  startChronoIfNeeded();
  timer.start();
}

function clearChrono() {
  clearInterval(chronoTimer);
  chronoTimer = null;
}

function startChronoIfNeeded() {
  clearChrono();
  const badge = $("ex-chrono-badge");
  if (mode !== "chrono") {
    badge.hidden = true;
    return;
  }
  chronoRemaining = CHRONO_SECONDS;
  badge.hidden = false;
  badge.textContent = `⏱ ${chronoRemaining}s`;
  chronoTimer = setInterval(() => {
    chronoRemaining -= 1;
    badge.textContent = `⏱ ${chronoRemaining}s`;
    if (chronoRemaining <= 0) {
      clearChrono();
      handleVerdict(false);
    }
  }, 1000);
}

function renderHistory() {
  const state = getState();
  const strip = $("history-strip");
  strip.innerHTML = "";
  state.history
    .slice(-15)
    .reverse()
    .forEach((h) => {
      const dot = document.createElement("div");
      dot.className = `history-dot ${h.correct ? "correct" : "wrong"}`;
      dot.title = `${h.chapter} : ${h.notion}`;
      dot.textContent = h.correct ? "✓" : "✕";
      strip.appendChild(dot);
    });
  if (!state.history.length) {
    strip.innerHTML = `<span style="color:var(--text-muted); font-size:0.85rem;">Aucun exercice fait pour l'instant.</span>`;
  }
}

async function handleVerdict(isCorrect) {
  clearChrono();
  const duration_s = timer.stop();
  const usedHint = !$("ex-hint").hidden;

  recordAnswer({
    id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    usedHint,
    mode,
    duration_s,
  });
  addSeriesQuestion(draft, {
    exercise_id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    duration_s,
  });

  await api.practiceResult(current.id, isCorrect);

  if (isCorrect) fireConfetti();
  else shakeElement($("screen-ex"));

  renderHistory();
  updateLevelLine();

  seriesIndex += 1;
  if (seriesIndex >= SERIES_TOTAL) {
    finishSeries();
  } else {
    persistProgress();
    await loadCurrent();
  }
}

function finishSeries() {
  let levelAtTime = null;
  try {
    const lvl = JSON.parse(localStorage.getItem("lumis:last_level"));
    levelAtTime = lvl?.label || null;
  } catch { /* ignore */ }

  const record = finalizeSeries(draft, { levelAtTime });
  clearInProgressSeries();
  showRecap(record);
}

function showRecap(record) {
  $("series-topbar").hidden = true;
  $("screen-ex").hidden = true;
  $("recap-title").textContent = record.score >= record.total * 0.7 ? "Belle série ! 🎉" : "Série terminée";
  $("recap-sub").textContent = `Mode : ${record.mode}${record.chapterId ? " · " + record.chapterId : ""}${record.notion ? " · " + record.notion : ""}`;
  $("recap-score").textContent = `${record.score}/${record.total}`;
  $("recap-accuracy").textContent = `${record.accuracy}%`;
  const minutes = Math.round(record.durationTotal_s / 60);
  $("recap-time").textContent = minutes >= 1 ? `${minutes} min` : `${record.durationTotal_s} s`;

  const notions = [...new Set(record.questions.map((q) => `${q.chapter} : ${q.notion}`))];
  $("recap-notions").innerHTML = notions.length
    ? `<strong>Notions travaillées :</strong><br>${notions.map((n) => `<span class="badge badge--neutral" style="margin:4px 4px 0 0; display:inline-block;">${n}</span>`).join("")}`
    : "";

  if (record.accuracy >= 70) fireConfetti();
  $("screen-recap").hidden = false;
  fadeInTransition($("screen-recap"));
  renderHistory();
}

$("ex-btn-yes").addEventListener("click", () => handleVerdict(true));
$("ex-btn-no").addEventListener("click", () => handleVerdict(false));
$("btn-next-ex").addEventListener("click", () => startSeries(mode, seriesConfig));
$("btn-recap-restart").addEventListener("click", () => startSeries(mode, seriesConfig));

$("btn-quit-series").addEventListener("click", () => {
  $("quit-modal-overlay").hidden = false;
});

$("btn-quit-cancel").addEventListener("click", () => {
  $("quit-modal-overlay").hidden = true;
});

$("btn-quit-confirm").addEventListener("click", () => {
  clearChrono();
  timer.stop();
  // Sauvegarde explicite (en plus de la sauvegarde déjà faite après chaque
  // réponse) : chapitre, notion, question actuelle, réponses, score, temps,
  // progression, date de début et id de série sont tous dans `draft`/`seriesConfig`.
  persistProgress();
  window.location.href = "dashboard.html";
});

$("btn-hint").addEventListener("click", () => {
  setMathContent($("ex-hint"), `💡 ${current.hint}`);
  $("ex-hint").hidden = false;
});
$("btn-sol").addEventListener("click", () => {
  setMathContent($("ex-sol"), `✅ ${current.answer}`);
  $("ex-sol").hidden = false;
});
$("btn-method").addEventListener("click", () => {
  const steps = current.solution_steps || [];
  const el = $("ex-method");
  if (steps.length) {
    el.innerHTML = `<strong>Méthode :</strong><ol>${steps.map((s) => `<li>${s}</li>`).join("")}</ol>`;
  } else {
    el.innerHTML = "Aucune méthode détaillée disponible pour cet exercice.";
  }
  if (window.renderMathInElement) {
    window.renderMathInElement(el, { delimiters: [{ left: "$", right: "$", display: false }], throwOnError: false });
  }
  el.hidden = false;
});

document.querySelectorAll(".mode-pill").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-pill").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    startSeries(btn.dataset.mode, {});
  });
});

function consumePendingSeries() {
  try {
    const raw = localStorage.getItem("lumis:pending_series");
    if (!raw) return null;
    localStorage.removeItem("lumis:pending_series");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function init() {
  updateLevelLine();
  renderHistory();

  const pending = consumePendingSeries();
  if (pending && pending.mode) {
    // Un lancement explicite (notion, ou "Recommencer" depuis le profil) remplace
    // une éventuelle série en cours restée en pause.
    clearInProgressSeries();
    document.querySelectorAll(".mode-pill").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === pending.mode);
    });
    await startSeries(pending.mode, pending);
    return;
  }

  const inProgress = getInProgressSeries();
  if (inProgress) {
    await resumeSeries(inProgress);
    return;
  }

  showEmpty(emptyMessageFor("revisions"));
}

init();
