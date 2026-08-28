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
import { openReportTicketPopup } from "./supportTicket.js";
import { DIFF_EMOJI, DIFF_LABEL_SHORT, DIFF_BADGE } from "./difficultyLevels.js";

const settingsManagerReady = initSettingsManager();
settingsManagerReady.then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const DIFF_XP = { 1: 10, 2: 13, 3: 16, 4: 19, 5: 22 };
let SERIES_TOTAL = 10;
const CHRONO_SECONDS = 45;

// ── Marqueur "session d'entraînement active dans cet onglet" ────────────────
// lumis:series_in_progress (localStorage) survit volontairement à la
// fermeture du navigateur, pour que la carte "Reprendre la série" (voir
// resume.js) fonctionne même des jours plus tard. Mais un clic générique sur
// "Entraînement" (sidebar, sans paramètre) ne doit PAS silencieusement rouvrir
// une série ancienne restée en pause (bug remonté) : seul un F5/retour dans
// CE même onglet pendant que la série est active (ce marqueur, en
// sessionStorage — vidé à la fermeture de l'onglet) ou un clic explicite sur
// "Reprendre la série" (paramètre ?resume=1, voir resume.js) doivent la
// reprendre automatiquement.
const TAB_ACTIVE_KEY = "lumis:exercice_tab_active";
function markTabActive() {
  try { sessionStorage.setItem(TAB_ACTIVE_KEY, "1"); } catch { /* stockage indisponible (navigation privée...) : tant pis, pas bloquant */ }
}
function clearTabActive() {
  try { sessionStorage.removeItem(TAB_ACTIVE_KEY); } catch { /* ignore */ }
}
function isTabActive() {
  try {
    if (sessionStorage.getItem(TAB_ACTIVE_KEY) !== "1") return false;
  } catch {
    return false;
  }
  // Chantier 9 (bug "Entraînement ouvre parfois un autre chapitre",
  // 2026-08-25) : la seule présence de ce marqueur en sessionStorage ne
  // prouve PAS un F5 de CETTE page — sessionStorage survit à TOUTE
  // navigation dans le même onglet, pas seulement à un F5. Quitter
  // exercice.html en pleine série via un lien de la sidebar (Cours,
  // Chapitres...) SANS passer par "Quitter" (le seul endroit qui nettoie ce
  // marqueur, voir quitSeries) laissait donc ce marqueur "collé à true"
  // indéfiniment dans cet onglet : le prochain clic générique sur
  // "Entraînement" (sidebar), même après avoir consulté plusieurs autres
  // chapitres entre-temps, reprenait alors SILENCIEUSEMENT l'ancienne série
  // — exactement le bug remonté ("j'atterris sur un autre chapitre que celui
  // attendu"). L'API Navigation Timing distingue un vrai rechargement de
  // cette page (type "reload") ou un retour d'historique vers elle (type
  // "back_forward") d'une navigation fraîche depuis une autre page (type
  // "navigate") — seuls les deux premiers cas justifient une reprise
  // automatique. Indisponible dans certains environnements (repli sur
  // sessionStorage seul, comportement historique) plutôt que de casser la
  // reprise F5 si l'API venait à manquer.
  try {
    const [nav] = performance.getEntriesByType("navigation");
    if (nav) return nav.type === "reload" || nav.type === "back_forward";
  } catch {
    /* API indisponible : repli sur sessionStorage seul (comportement historique) */
  }
  return true;
}

// ── Préférences d'entraînement (Paramètres → Entraînement), chargées avant
// tout démarrage de série — voir loadTrainingSettings() dans init().
// questionsPerSeries/chrono/soundEffects sont alignés sur et écrasés par
// auth.py::DEFAULT_SETTINGS["training"] (paramétrables dans l'interface) ;
// confirmBeforeLeave/autoResume/autoShowCorrection ne sont plus des réglages
// exposés (simplification de l'interface) — ces trois valeurs restent
// fixes, jamais écrasées par le merge de loadTrainingSettings().
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
let lastVerdictLabel = null; // rempli par handleVerdict(), lu uniquement par le bouton "Signaler un problème"
let chronoTimer = null;
let chronoRemaining = CHRONO_SECONDS;
const timer = new ActivityTimer();

// ── Verrou anti double-clic (chantier "Correction du risque de double-
// consommation des exercices") ──────────────────────────────────────────────
// startSeries(), handleVerdict() et resumeSeries() mutent le MÊME état
// partagé (seriesQueue/seriesIndex/draft/current) puis appellent loadCurrent()
// (seul point qui consomme QuotaType.EXERCISES_DAILY, voir server.py::
// api_practice_load). Sans verrou, deux invocations quasi simultanées de
// n'importe laquelle de ces fonctions (double-clic, clic pendant l'expiration
// du chrono...) exécutent chacune leur portion synchrone jusqu'à leur premier
// `await` AVANT que la première n'ait fini : la seconde écrase l'état déjà
// posé par la première, et les deux finissent par appeler /api/practice/load
// indépendamment — deux consommations réelles pour une seule intention
// utilisateur. Un seul verrou partagé (pas un par fonction) : ces trois
// fonctions doivent se bloquer mutuellement, pas seulement elles-mêmes.
// loadCurrent() n'a pas besoin de son propre verrou : elle n'est jamais
// appelée ailleurs que par ces trois fonctions, déjà protégées.
let exerciseActionInFlight = false;

// Boutons capables de déclencher une de ces trois fonctions — désactivés le
// temps du flux en cours pour éviter le double-clic à la source (le verrou
// reste la garantie réelle ; ceci n'est qu'une aide UX). btn-quit-series/
// btn-hint/btn-sol/btn-method ne déclenchent aucune des trois fonctions
// protégées : volontairement non touchés (§3 : ne pas bloquer des
// interactions non concernées).
const EXERCISE_ACTION_BUTTON_IDS = ["btn-next-ex", "btn-recap-restart", "ex-btn-yes", "ex-btn-no"];

function setExerciseActionButtonsDisabled(disabled) {
  EXERCISE_ACTION_BUTTON_IDS.forEach((id) => {
    const el = $(id);
    if (el) el.disabled = disabled;
  });
  document.querySelectorAll(".mode-pill").forEach((b) => { b.disabled = disabled; });
}

// `lumis:practice_choices` : entrées historiques laissées par l'ancien test
// de placement (retiré) sur des navigateurs qui l'ont utilisé — conservé en
// lecture seule pour ne pas casser leur pool "Révisions" existant, plus rien
// n'écrit cette clé aujourd'hui. Filtrée par classe (voir getStoredClassLevel)
// pour qu'un pool construit sous Seconde ne resurgisse jamais sous Première.
// Entrées historiques sans class_level : seconde par convention, même repli
// que partout ailleurs.
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
  $("level-line").textContent = "Choisis un chapitre pour commencer à t'entraîner.";
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
    if (!shuffled.length) {
      shuffled = shuffle(ids);
      // Anti-répétition à la jonction entre deux passages du pool : sans
      // ce garde-fou, le dernier id du lot précédent peut retomber en
      // première position du nouveau lot (deux tirages indépendants), ce
      // qui donne à l'élève deux fois de suite le même exercice — voir
      // Phase 1 "diversité contrôlée" du chantier pédagogique.
      const last = seriesIds[seriesIds.length - 1];
      if (ids.length > 1 && shuffled[shuffled.length - 1] === last) {
        const swapAt = shuffled.length - 2;
        [shuffled[swapAt], shuffled[shuffled.length - 1]] = [shuffled[shuffled.length - 1], shuffled[swapAt]];
      }
    }
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
  // Double-clic sur "Démarrer la série"/"Recommencer"/un mode-pill : la
  // deuxième invocation ne fait rien plutôt que d'écraser seriesQueue/
  // seriesIndex/draft déjà posés par la première (voir le commentaire sur
  // exerciseActionInFlight).
  if (exerciseActionInFlight) return;
  exerciseActionInFlight = true;
  setExerciseActionButtonsDisabled(true);
  try {
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
    markTabActive();
    await loadCurrent();
  } finally {
    exerciseActionInFlight = false;
    setExerciseActionButtonsDisabled(false);
  }
}

async function resumeSeries(snapshot) {
  // Même verrou que startSeries()/handleVerdict() (voir exerciseActionInFlight) :
  // resumeSeries() n'est appelée que depuis init(), mais mute le même état
  // partagé et peut théoriquement chevaucher un clic utilisateur (démarrer une
  // nouvelle série, répondre) survenu pendant les `await` précédents de init().
  if (exerciseActionInFlight) return;
  exerciseActionInFlight = true;
  setExerciseActionButtonsDisabled(true);
  try {
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
  markTabActive();

  // Anti double-consommation (F5 / retour sur une série / "Reprendre la
  // série") : si l'exercice actuellement dû (seriesQueue[seriesIndex]) est
  // exactement celui déjà persisté par le dernier loadCurrent() réussi, on le
  // réaffiche depuis le snapshot SANS rappeler /api/practice/load — cet
  // exercice a déjà été consommé une fois, le backend reste la seule source
  // de vérité de ce qui a réellement été facturé (voir loadCurrent/
  // persistProgress). Toute incertitude (snapshot absent, id différent)
  // retombe sur un vrai appel réseau, jamais sur une supposition côté client.
  const cached = snapshot.currentExercise;
  if (cached && cached.id === seriesQueue[seriesIndex]) {
    current = cached;
    lastVerdictLabel = null;
    renderExercise();
    refreshExercisesQuota();
    return;
  }
  await loadCurrent();
  } finally {
    exerciseActionInFlight = false;
    setExerciseActionButtonsDisabled(false);
  }
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
    // Snapshot de l'exercice actuellement affiché (`current`), s'il y en a
    // un — permet à resumeSeries() de le réafficher sans rappeler
    // /api/practice/load (donc sans reconsommer le quota) quand il
    // correspond encore à seriesQueue[seriesIndex] au moment de la reprise.
    currentExercise: current,
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

// Nombre d'exercices classiques restants aujourd'hui (QuotaType.EXERCISES_DAILY,
// voir quota_service.py) — même pattern que chatbot.js::refreshQuota : source
// unique GET /api/quota, jamais recalculé côté client. Rafraîchi au chargement
// de la page et après chaque exercice réellement chargé (voir loadCurrent).
const quotaIndicator = $("exercises-quota-indicator");
const quotaValue = $("exercises-quota-value");

async function refreshExercisesQuota() {
  if (!quotaIndicator || !quotaValue) return;
  try {
    const { exercises_daily: q } = await api.getQuota();
    quotaIndicator.hidden = false;
    quotaIndicator.classList.toggle("is-unlimited", q.unlimited);
    quotaIndicator.classList.toggle("is-exhausted", !q.unlimited && q.remaining === 0);
    quotaIndicator.classList.toggle("is-low", !q.unlimited && q.remaining > 0 && q.remaining <= Math.ceil(q.limit * 0.15));
    quotaValue.textContent = q.unlimited
      ? "Exercices illimités"
      : `${q.remaining} exercice${q.remaining === 1 ? "" : "s"} restant${q.remaining === 1 ? "" : "s"} aujourd'hui`;
  } catch { /* silencieux : l'indicateur reste dans son dernier état connu */ }
}

// Message affiché quand /api/practice/load répond 429 (QuotaExceededError,
// voir quota_service.py) : réutilise la zone "empty-state" déjà existante
// (aucune nouvelle structure DOM) plutôt qu'un toast qui redirigerait
// hors de la page en pleine série (voir api.js::buildApiError, qui ne
// déclenche PAS le toast générique pour ce quota précis).
function showExercisesQuotaExceeded(err) {
  clearChrono();
  timer.stop();
  $("series-topbar").hidden = true;
  $("screen-ex").hidden = true;
  $("screen-ex").classList.remove("is-loading");
  $("screen-recap").hidden = true;
  $("empty-state").hidden = false;
  const limitText = err.limit != null ? `ta limite de ${err.limit} exercices` : "ta limite d'exercices";
  $("empty-state").querySelector("p").textContent =
    `Tu as atteint ${limitText} aujourd'hui. Elle sera réinitialisée demain.`;
  refreshExercisesQuota();
}

/** Rendu pur de `current` déjà connu (fraîchement chargé, ou restauré depuis
 * une reprise sans nouvel appel réseau — voir resumeSeries) : aucune
 * requête ici, jamais de double consommation du quota. */
function renderExercise() {
  $("screen-ex").classList.remove("is-loading");

  $("series-count").textContent = `Question ${seriesIndex + 1}/${SERIES_TOTAL}`;
  $("series-progress-fill").style.width = `${(seriesIndex / SERIES_TOTAL) * 100}%`;
  renderSeriesDots();

  $("ex-chapter-badge").textContent = current.chapter_id;
  $("ex-notion-badge").textContent = current.notion || "";
  $("ex-xp-badge").textContent = `+${DIFF_XP[current.difficulty] || 10} XP`;
  const diffBadge = $("ex-difficulty-badge");
  diffBadge.textContent = `${DIFF_EMOJI[current.difficulty] || ""} ${DIFF_LABEL_SHORT[current.difficulty] || ""}`.trim();
  diffBadge.className = `badge ${DIFF_BADGE[current.difficulty] || "badge--neutral"}`;
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

/** Charge RÉELLEMENT un nouvel exercice depuis le backend (seul point qui
 * consomme QuotaType.EXERCISES_DAILY, voir server.py::api_practice_load).
 * Un 429 (série ayant épuisé le quota du jour, ex: 3 exercices restants sur
 * une série de 10) arrête proprement la série sans la casser — la série
 * reste reprenable demain (voir lumis:series_in_progress / resumeSeries),
 * le quota se réinitialisant à minuit UTC côté serveur. */
async function loadCurrent() {
  const id = seriesQueue[seriesIndex];
  $("screen-ex").classList.add("is-loading");
  let data;
  try {
    data = await api.practiceLoad(id, getStoredClassLevel());
  } catch (err) {
    if (err.isQuotaExceeded && err.quota === "exercises_daily") {
      showExercisesQuotaExceeded(err);
      return;
    }
    $("screen-ex").classList.remove("is-loading");
    throw err;
  }
  current = data.exercise;
  lastVerdictLabel = null;
  // Persisté ICI (exercice déjà réellement chargé et consommé côté serveur) :
  // un F5/reprise juste après pourra restaurer `current` sans nouvel appel
  // réseau, donc sans reconsommer le même exercice — voir resumeSeries().
  persistProgress();
  refreshExercisesQuota();
  renderExercise();
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
  // Double-clic sur "Réussi"/"Échoué" (ou clic pile au moment où le chrono
  // expire, voir startChronoIfNeeded) : la deuxième invocation ne doit ni
  // renvoyer un second verdict, ni avancer une seconde fois dans la série, ni
  // déclencher un second /api/practice/load (voir exerciseActionInFlight).
  if (exerciseActionInFlight) return;
  exerciseActionInFlight = true;
  setExerciseActionButtonsDisabled(true);
  try {
    clearChrono();
    lastVerdictLabel = isCorrect ? "Réussi" : "Échoué";
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
  } finally {
    exerciseActionInFlight = false;
    setExerciseActionButtonsDisabled(false);
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
  clearTabActive();
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
$("btn-report-exercise").addEventListener("click", () => {
  if (!current) return;
  openReportTicketPopup({
    sourceLabel: "Exercice",
    defaultCategory: "bug",
    contextLines: [
      { label: "Exercice", value: current.id },
      { label: "Chapitre", value: current.chapter_id },
      { label: "Classe", value: getStoredClassLevel() },
      { label: "Réponse utilisateur", value: lastVerdictLabel || "non renseignée (signalé avant réponse)" },
      { label: "Difficulté", value: current.difficulty },
      { label: "URL", value: window.location.href },
    ],
  });
});
$("btn-next-ex").addEventListener("click", () => startSeries(mode, seriesConfig));
$("btn-recap-restart").addEventListener("click", () => startSeries(mode, seriesConfig));

function quitSeries() {
  clearChrono();
  timer.stop();
  // Sauvegarde explicite (en plus de la sauvegarde déjà faite après chaque
  // réponse) : chapitre, notion, question actuelle, réponses, score, temps,
  // progression, date de début et id de série sont tous dans `draft`/`seriesConfig`.
  persistProgress();
  // Sortie volontaire : un prochain clic générique sur "Entraînement" (même
  // onglet) ne doit pas rouvrir automatiquement cette série — voir
  // TAB_ACTIVE_KEY plus haut. La reprise reste possible explicitement via la
  // carte "Reprendre la série" (resume.js, lumis:series_in_progress conservé).
  clearTabActive();
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
  refreshExercisesQuota();

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
    // Ne reprend automatiquement que si la demande est explicite (carte
    // "Reprendre la série", ?resume=1 — voir resume.js) ou si cet onglet est
    // déjà dans cette session d'entraînement (F5 en cours de série, voir
    // TAB_ACTIVE_KEY). Un clic générique "Entraînement" (sidebar), sans l'un
    // de ces deux signaux, ne doit pas rouvrir silencieusement une série
    // ancienne restée en pause — voir carte "Série en cours" pour y revenir
    // volontairement.
    const params = new URLSearchParams(window.location.search);
    const explicitResume = params.get("resume") === "1";
    if (explicitResume) {
      params.delete("resume");
      const clean = window.location.pathname + (params.toString() ? `?${params}` : "");
      window.history.replaceState({}, "", clean);
    }

    if (explicitResume || isTabActive()) {
      // Préférence "Reprendre automatiquement une série interrompue" : si
      // désactivée, on demande confirmation au lieu de reprendre en silence.
      if (!trainingSettings.autoResume && !window.confirm("Une série est en cours. Veux-tu la reprendre ?")) {
        clearInProgressSeries();
        clearTabActive();
        showEmpty(emptyMessageFor("revisions"));
        return;
      }
      await resumeSeries(inProgress);
      return;
    }
  }

  showEmpty(emptyMessageFor("revisions"));
}

init();
