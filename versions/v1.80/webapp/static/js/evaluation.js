import { api } from "./api.js";
import { setMathContent } from "./mathrender.js";
import { fadeInTransition } from "./animations.js";
import { recordAnswer, createSeriesDraft, addSeriesQuestion, finalizeSeries } from "./store.js";
import { ActivityTimer } from "./timetrack.js";
import { ICONS } from "./icons.js";
import { getStoredClassLevel } from "./curriculumSelector.js";

const $ = (id) => document.getElementById(id);
const screenQuiz = $("screen-quiz");
const screenLoading = $("screen-loading");
const screenResult = $("screen-result");

let current = null;
let startedAt = Date.now();
let chronoInterval = null;
let seriesDraft = null;
const questionTimer = new ActivityTimer();

function startChrono() {
  startedAt = Date.now();
  chronoInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startedAt) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const s = String(elapsed % 60).padStart(2, "0");
    $("eval-chrono").textContent = `${m}:${s}`;
  }, 1000);
}

function showQuestion(progress, exercise) {
  current = exercise;
  $("eval-question-count").textContent = `Question ${progress.current}/${progress.total}`;
  $("eval-progress-fill").style.width = `${(progress.current / progress.total) * 100}%`;
  $("eval-chapter-badge").textContent = exercise.chapter_id;
  $("eval-notion-badge").textContent = exercise.notion || "";
  setMathContent($("eval-enonce"), exercise.enonce);
  $("eval-hint").hidden = true;
  $("eval-answer").hidden = true;

  screenLoading.hidden = true;
  screenQuiz.hidden = false;
  fadeInTransition(screenQuiz);
  questionTimer.start();
}

$("btn-hint").addEventListener("click", () => {
  setMathContent($("eval-hint"), current.hint);
  $("eval-hint").prepend(iconEl("lightbulb"));
  $("eval-hint").hidden = false;
});

$("btn-ans").addEventListener("click", () => {
  setMathContent($("eval-answer"), current.answer);
  $("eval-answer").prepend(iconEl("check"));
  $("eval-answer").hidden = false;
});

function iconEl(name) {
  const span = document.createElement("span");
  span.className = "eval-inline-icon";
  span.innerHTML = ICONS[name] || "";
  return span;
}

async function handleAnswer(isCorrect) {
  const usedHint = !$("eval-hint").hidden;
  const duration_s = questionTimer.stop();
  recordAnswer({
    id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    usedHint,
    mode: "evaluation",
    duration_s,
  });
  addSeriesQuestion(seriesDraft, {
    exercise_id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    duration_s,
  });

  const data = await api.answer(current.id, isCorrect);
  if (data.finished) {
    clearInterval(chronoInterval);
    localStorage.setItem("lumis:last_level", JSON.stringify({ level: data.level, label: data.level_label, icon: data.level_icon }));
    localStorage.setItem(
      "lumis:practice_choices",
      JSON.stringify({ classLevel: getStoredClassLevel(), choices: data.practice_choices || [] }),
    );
    finalizeSeries(seriesDraft, { levelAtTime: data.level_label });
    $("result-icon").innerHTML = ICONS[data.level_icon] || ICONS.trophy;
    $("result-label").textContent = `Ton niveau : ${data.level_label}`;
    screenQuiz.hidden = true;
    screenResult.hidden = false;
    fadeInTransition(screenResult);
  } else {
    showQuestion(data.progress, data.exercise);
  }
}

$("btn-yes").addEventListener("click", () => handleAnswer(true));
$("btn-no").addEventListener("click", () => handleAnswer(false));

$("btn-quit-eval").addEventListener("click", () => {
  $("quit-eval-modal-overlay").hidden = false;
});
$("btn-quit-eval-cancel").addEventListener("click", () => {
  $("quit-eval-modal-overlay").hidden = true;
});
$("btn-quit-eval-confirm").addEventListener("click", async () => {
  clearInterval(chronoInterval);
  await api.restart();
  window.location.href = "chapitres.html";
});

// Entrées historiques (avant ce correctif) : un simple tableau de
// chapterId, sans classe associée — traité comme seconde par convention,
// même repli que partout ailleurs dans le projet.
function selectedChaptersForActiveClass() {
  let raw;
  try {
    raw = JSON.parse(localStorage.getItem("lumis:selected_chapters"));
  } catch {
    return [];
  }
  if (!raw) return [];
  const stored = Array.isArray(raw) ? { classLevel: "seconde", chapters: raw } : raw;
  return (stored.classLevel || "seconde") === getStoredClassLevel() ? (stored.chapters || []) : [];
}

async function init() {
  const chapters = selectedChaptersForActiveClass();
  const data = await api.start(chapters, getStoredClassLevel());
  seriesDraft = createSeriesDraft({ mode: "evaluation", chapterId: null, notion: null, total: data.progress.total });
  startChrono();
  showQuestion(data.progress, data.exercise);
}

init();
