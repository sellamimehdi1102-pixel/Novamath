import { api } from "./api.js";
import { bindThemeToggle } from "./theme.js";
import { setMathContent } from "./mathrender.js";
import { fireConfetti, shakeElement, fadeInTransition } from "./animations.js";
import { recordAnswer, getState, masteryByNotion, getFavorites, toggleFavorite } from "./store.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const $ = (id) => document.getElementById(id);
const DIFF_XP = { 1: 10, 2: 15, 3: 20 };
const DAILY_GOAL = 5;
const CHRONO_SECONDS = 45;

let mode = "libre";
let current = null;
let chronoTimer = null;
let chronoRemaining = CHRONO_SECONDS;

function pool() {
  try {
    return JSON.parse(localStorage.getItem("lumis:practice_choices")) || [];
  } catch {
    return [];
  }
}

function updateLevelLine() {
  try {
    const lvl = JSON.parse(localStorage.getItem("lumis:last_level"));
    if (lvl) {
      const state = getState();
      const doneToday = state.history.filter((h) => h.date === new Date().toISOString().slice(0, 10)).length;
      $("level-line").textContent = `${lvl.icon} Niveau ${lvl.label} · ${doneToday}/${DAILY_GOAL} exercices aujourd'hui`;
      return;
    }
  } catch { /* pas de niveau connu */ }
  $("level-line").textContent = "Fais d'abord une évaluation pour débloquer l'entraînement adapté.";
}

function candidateId() {
  const state = getState();
  const choices = pool();

  if (mode === "erreurs") {
    const wrong = state.history.filter((h) => !h.correct && h.id != null);
    if (!wrong.length) return null;
    return wrong[Math.floor(Math.random() * wrong.length)].id;
  }
  if (mode === "favoris") {
    const favs = getFavorites();
    if (!favs.length) return null;
    return favs[Math.floor(Math.random() * favs.length)];
  }
  if (mode === "faibles") {
    const nm = masteryByNotion(state.history);
    const weakKeys = Object.entries(nm).filter(([, v]) => v.rate < 0.5).map(([k]) => k.split("|")[1]);
    const filtered = choices.filter((c) => weakKeys.some((n) => c.label.endsWith(n)));
    const source = filtered.length ? filtered : choices;
    if (!source.length) return null;
    return source[Math.floor(Math.random() * source.length)].id;
  }
  // libre, revisions, objectif, examen, chrono : même pool (niveau + chapitres choisis)
  if (!choices.length) return null;
  return choices[Math.floor(Math.random() * choices.length)].id;
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

async function loadNext() {
  const id = candidateId();
  if (id == null) {
    $("empty-state").hidden = false;
    $("screen-ex").hidden = true;
    $("empty-state").querySelector("p").textContent = emptyMessageFor(mode);
    return;
  }
  const data = await api.practiceLoad(id);
  current = data.exercise;

  $("ex-chapter-badge").textContent = current.chapter_id;
  $("ex-notion-badge").textContent = current.notion || "";
  $("ex-xp-badge").textContent = `+${DIFF_XP[current.difficulty] || 10} XP`;
  setMathContent($("ex-enonce"), current.enonce);
  $("ex-hint").hidden = true;
  $("ex-method").hidden = true;
  $("ex-sol").hidden = true;
  $("btn-fav").textContent = getFavorites().includes(current.id) ? "★" : "☆";

  // En mode examen, on retire les aides pour se rapprocher de conditions réelles.
  const examMode = mode === "examen";
  $("btn-hint").hidden = examMode;
  $("btn-method").hidden = false;
  $("btn-sol").hidden = examMode;

  $("empty-state").hidden = true;
  $("screen-ex").hidden = false;
  fadeInTransition($("screen-ex"));
  startChronoIfNeeded();
}

function emptyMessageFor(m) {
  if (m === "erreurs") return "Aucune erreur enregistrée pour l'instant — bravo !";
  if (m === "favoris") return "Aucun exercice mis en favori. Clique sur ☆ pendant un exercice pour l'ajouter.";
  if (m === "faibles") return "Pas encore assez de données sur tes notions faibles.";
  return "Fais d'abord une évaluation initiale (page Chapitres) pour débloquer l'entraînement.";
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
  const usedHint = !$("ex-hint").hidden;
  const { newlyUnlocked } = recordAnswer({
    id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    usedHint,
    mode,
  });

  await api.practiceResult(current.id, isCorrect);

  if (isCorrect) {
    fireConfetti();
  } else {
    shakeElement($("screen-ex"));
  }
  if (newlyUnlocked.length) {
    setTimeout(() => fireConfetti(), 200);
  }

  renderHistory();
  updateLevelLine();
  await loadNext();
}

$("ex-btn-yes").addEventListener("click", () => handleVerdict(true));
$("ex-btn-no").addEventListener("click", () => handleVerdict(false));
$("btn-next-ex").addEventListener("click", loadNext);

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
$("btn-fav").addEventListener("click", () => {
  const isFav = toggleFavorite(current.id);
  $("btn-fav").textContent = isFav ? "★" : "☆";
});

document.querySelectorAll(".mode-pill").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-pill").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
    loadNext();
  });
});

updateLevelLine();
renderHistory();
