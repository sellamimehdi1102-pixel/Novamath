import { api } from "./api.js";
import { initSettingsManager, getSettings, onSettingsChange } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { setMathContent } from "./mathrender.js";
import { fireConfetti, shakeElement, fadeInTransition } from "./animations.js";
import {
  recordAnswer, getState, createSeriesDraft, addSeriesQuestion, finalizeSeries,
  saveInProgressSeries, getInProgressSeries, clearInProgressSeries, scopedStats,
} from "./store.js";
import { ActivityTimer } from "./timetrack.js";
import { bindLiveTranslations } from "./i18n.js";
import { ICONS } from "./icons.js";
import { getStoredClassLevel } from "./curriculumSelector.js";

const settingsManagerReady = initSettingsManager();
settingsManagerReady.then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const DIFF_XP = { 1: 10, 2: 13, 3: 16, 4: 19, 5: 22 };
let SERIES_TOTAL = 10;
const CHRONO_SECONDS = 45;

// ── Préférences d'entraînement (Paramètres → Entraînement), chargées avant
// tout démarrage de série — voir loadTrainingSettings() dans init(). Valeurs
// par défaut alignées sur auth.py::DEFAULT_SETTINGS["training"], au cas où le
// chargement échoue (offline, session expirée entre-temps, etc.).
let trainingSettings = {
  questionsPerSeries: 10,
  chrono: true,
  confirmBeforeLeave: true,
  autoResume: true,
  autoShowCorrection: false,
  soundEffects: true,
};

function playTone(freq, duration = 0.15) {
  if (!trainingSettings.soundEffects) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
    osc.onended = () => ctx.close();
  } catch {
    /* API audio indisponible — pas bloquant */
  }
}

let mode = "revisions";
let seriesConfig = {};
let seriesQueue = [];
let seriesIndex = 0;
let draft = null;
let current = null;
let chronoTimer = null;
let chronoRemaining = CHRONO_SECONDS;
const timer = new ActivityTimer();

// `lumis:practice_choices` vient de l'évaluation initiale (evaluation.js),
// elle-même construite depuis la banque Seconde uniquement (aucun modèle
// adaptatif déclaré pour les autres classes dans curriculum_registry.py —
// voir server.py::MODEL). Sans ce filtre, une évaluation faite pendant que
// Seconde était active resterait proposée comme pool d'entraînement "par
// défaut" même après être passé en Première. Entrées historiques (sans
// class_level) : seconde par convention, même repli que partout ailleurs.
function pool() {
  try {
    const raw = JSON.parse(localStorage.getItem("lumis:practice_choices"));
    if (!raw) return [];
    const stored = Array.isArray(raw) ? { classLevel: "seconde", choices: raw } : raw;
    return (stored.classLevel || "seconde") === getStoredClassLevel() ? (stored.choices || []) : [];
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
  const state = scopedStats(getState(), getStoredClassLevel());
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
  return "Fais d'abord une évaluation initiale (page Exercices) pour débloquer l'entraînement.";
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
  // Toute série démarrée explicitement (par opposition à une reprise, voir
  // resumeSeries) doit utiliser la préférence "Nombre d'exercices" actuelle —
  // même si une série précédente reprise avait temporairement réaligné
  // SERIES_TOTAL sur un ancien total (voir resumeSeries()).
  SERIES_TOTAL = trainingSettings.questionsPerSeries || 10;
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
  // Une série déjà en cours a été construite avec le nombre de questions en
  // vigueur au moment de son lancement (snapshot.total) : si la préférence
  // "Nombre d'exercices" a changé depuis (ex. 10 → 20) pendant qu'elle était
  // en pause, on NE redimensionne PAS seriesQueue (déjà figée) — on réaligne
  // au contraire SERIES_TOTAL sur la taille réelle de la série reprise, pour
  // que "Question X/Y" et la condition de fin restent cohérents avec son
  // contenu réel. La nouvelle préférence s'appliquera à la prochaine série
  // démarrée depuis zéro (buildSeriesPool() lit SERIES_TOTAL à cet instant-là).
  SERIES_TOTAL = snapshot.total || seriesQueue.length || SERIES_TOTAL;
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
  const score = draft.questions.filter((q) => q.correct).length;
  const wrong = draft.questions.length - score;
  saveInProgressSeries({
    mode,
    seriesConfig,
    seriesQueue,
    seriesIndex,
    draftId: draft.id,
    draftStartedAt: draft.startedAt,
    startDate: new Date(draft.startedAt).toISOString().slice(0, 10),
    draftQuestions: draft.questions,
    total: SERIES_TOTAL,
    score,
    wrong,
    progressPct: Math.round((seriesIndex / SERIES_TOTAL) * 100),
  });
}

// Puces de progression de la série — présentation pure à partir de valeurs
// déjà calculées (seriesIndex/SERIES_TOTAL/draft.questions), aucune nouvelle
// donnée ni aucun nouveau calcul de score.
function renderSeriesDots() {
  const container = $("series-dots");
  if (!container) return;
  const total = Math.min(SERIES_TOTAL, 40); // évite une rangée illisible si le réglage "nombre d'exercices" est très élevé
  const html = [];
  for (let i = 0; i < total; i++) {
    const q = draft?.questions[i];
    let cls = "series-dot";
    if (q) cls += q.correct ? " is-correct" : " is-wrong";
    else if (i === seriesIndex) cls += " is-current";
    html.push(`<span class="${cls}"></span>`);
  }
  container.innerHTML = html.join("");
}

async function loadCurrent() {
  const id = seriesQueue[seriesIndex];
  $("screen-ex").classList.add("is-loading");
  const data = await api.practiceLoad(id, getStoredClassLevel());
  current = data.exercise;
  $("screen-ex").classList.remove("is-loading");

  $("series-count").textContent = `Question ${seriesIndex + 1}/${SERIES_TOTAL}`;
  $("series-progress-fill").style.width = `${(seriesIndex / SERIES_TOTAL) * 100}%`;
  renderSeriesDots();

  $("ex-chapter-badge").textContent = current.chapter_id;
  $("ex-notion-badge").textContent = current.notion || "";
  $("ex-xp-badge").textContent = `+${DIFF_XP[current.difficulty] || 10} XP`;
  setMathContent($("ex-enonce"), current.enonce);
  $("ex-hint").hidden = true;
  $("ex-method").hidden = true;
  $("ex-sol").hidden = true;
  $("btn-hint").classList.remove("is-revealed");
  $("btn-method").classList.remove("is-revealed");
  $("btn-sol").classList.remove("is-revealed");

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
  if (mode !== "chrono" || !trainingSettings.chrono) {
    badge.hidden = true;
    return;
  }
  chronoRemaining = CHRONO_SECONDS;
  badge.hidden = false;
  badge.classList.remove("is-urgent");
  badge.innerHTML = `<span class="exercice-inline-icon">${ICONS.clock}</span>${chronoRemaining}s`;
  const chronoValueEl = badge.lastChild;
  chronoTimer = setInterval(() => {
    chronoRemaining -= 1;
    chronoValueEl.textContent = `${chronoRemaining}s`;
    badge.classList.toggle("is-urgent", chronoRemaining <= 10 && chronoRemaining > 0);
    if (chronoRemaining <= 0) {
      clearChrono();
      handleVerdict(false);
    }
  }, 1000);
}

function renderHistory() {
  const state = scopedStats(getState(), getStoredClassLevel());
  const strip = $("history-strip");
  strip.innerHTML = "";
  state.history
    .slice(-15)
    .reverse()
    .forEach((h) => {
      const dot = document.createElement("div");
      dot.className = `history-dot ${h.correct ? "correct" : "wrong"}`;
      dot.title = `${h.chapter} : ${h.notion}`;
      dot.innerHTML = ICONS[h.correct ? "check" : "x"];
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

  await api.practiceResult(current.id, isCorrect, getStoredClassLevel());

  if (isCorrect) { fireConfetti(); playTone(880); }
  else { shakeElement($("screen-ex")); playTone(220, 0.25); }

  renderHistory();
  updateLevelLine();

  // Préférence "Afficher automatiquement la correction" (Paramètres →
  // Entraînement) : la méthode s'affiche sans clic, avec une courte pause
  // avant d'enchaîner — jamais en mode examen (intégrité de l'épreuve).
  if (trainingSettings.autoShowCorrection && mode !== "examen") {
    showMethod();
    await new Promise((resolve) => setTimeout(resolve, 2500));
  }

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

// Icône + teinte de la carte de fin de série — présentation pure à partir de
// record.accuracy (déjà calculé par finalizeSeries dans store.js). L'Or
// n'apparaît que sur les meilleures séries (≥90%), jamais en dessous.
function renderRecapIcon(record) {
  const el = $("recap-icon");
  if (record.accuracy >= 90) {
    el.className = "recap-icon tier-gold";
    el.innerHTML = ICONS.trophy;
  } else if (record.accuracy >= 70) {
    el.className = "recap-icon tier-good";
    el.innerHTML = ICONS.star;
  } else {
    el.className = "recap-icon tier-encourage";
    el.innerHTML = ICONS.sprout;
  }
}

function showRecap(record) {
  $("series-topbar").hidden = true;
  $("screen-ex").hidden = true;
  renderRecapIcon(record);
  $("recap-title").textContent = record.score >= record.total * 0.7 ? "Belle série !" : "Série terminée";
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

function quitSeries() {
  clearChrono();
  timer.stop();
  // Sauvegarde explicite (en plus de la sauvegarde déjà faite après chaque
  // réponse) : chapitre, notion, question actuelle, réponses, score, temps,
  // progression, date de début et id de série sont tous dans `draft`/`seriesConfig`.
  persistProgress();
  window.location.href = "dashboard.html";
}

$("btn-quit-series").addEventListener("click", () => {
  // Préférence "Confirmation avant de quitter une série" (Paramètres →
  // Entraînement) : désactivée, on quitte directement sans la fenêtre.
  if (!trainingSettings.confirmBeforeLeave) {
    quitSeries();
    return;
  }
  $("quit-modal-overlay").hidden = false;
});

$("btn-quit-cancel").addEventListener("click", () => {
  $("quit-modal-overlay").hidden = true;
});

$("btn-quit-confirm").addEventListener("click", quitSeries);

$("btn-hint").addEventListener("click", () => {
  setMathContent($("ex-hint"), current.hint);
  $("ex-hint").prepend(inlineIconEl("lightbulb"));
  $("ex-hint").hidden = false;
  $("btn-hint").classList.add("is-revealed");
});
$("btn-sol").addEventListener("click", () => {
  setMathContent($("ex-sol"), current.answer);
  $("ex-sol").prepend(inlineIconEl("check"));
  $("ex-sol").hidden = false;
  $("btn-sol").classList.add("is-revealed");
});

function inlineIconEl(name) {
  const span = document.createElement("span");
  span.className = "exercice-inline-icon";
  span.innerHTML = ICONS[name] || "";
  return span;
}
function showMethod() {
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
  $("btn-method").classList.add("is-revealed");
}
$("btn-method").addEventListener("click", showMethod);

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

async function loadTrainingSettings() {
  try {
    await settingsManagerReady;
    const s = getSettings();
    if (s?.training) trainingSettings = { ...trainingSettings, ...s.training };
  } catch {
    /* préférences par défaut déjà en place — pas bloquant (invité hors ligne, etc.) */
  }
  SERIES_TOTAL = trainingSettings.questionsPerSeries || 10;
}

// Corrige le bug historique "le chrono ne se désactive pas" : avant, les
// préférences n'étaient lues qu'une fois au chargement de la page — si le
// popup Paramètres était ouvert par-dessus une page exercice déjà en mémoire
// et que le toggle Chronomètre changeait, la valeur en mémoire ici restait
// périmée jusqu'à un rechargement complet. On s'abonne désormais à l'événement
// du SettingsManager pour appliquer tout changement "training" en direct,
// y compris couper un chrono déjà en cours de décompte.
onSettingsChange((e) => {
  const t = e.detail.category === "training" ? e.detail.patch
    : e.detail.category === "*" ? e.detail.settings?.training
    : null;
  if (!t) return;
  trainingSettings = { ...trainingSettings, ...t };
  SERIES_TOTAL = trainingSettings.questionsPerSeries || 10;
  if (mode === "chrono" && current) {
    if (!trainingSettings.chrono) {
      clearChrono();
      $("ex-chrono-badge").hidden = true;
    } else if (!chronoTimer) {
      startChronoIfNeeded();
    }
  }
});

async function init() {
  await loadTrainingSettings();
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
    // Préférence "Reprendre automatiquement une série interrompue" : si
    // désactivée, on demande confirmation au lieu de reprendre en silence.
    if (!trainingSettings.autoResume && !window.confirm("Une série est en cours. Veux-tu la reprendre ?")) {
      clearInProgressSeries();
      showEmpty(emptyMessageFor("revisions"));
      return;
    }
    await resumeSeries(inProgress);
    return;
  }

  showEmpty(emptyMessageFor("revisions"));
}

init();
