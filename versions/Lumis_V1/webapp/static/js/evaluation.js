import { api } from "./api.js";
import { setMathContent } from "./mathrender.js";
import { fadeInTransition } from "./animations.js";
import { recordAnswer } from "./store.js";

const $ = (id) => document.getElementById(id);
const screenQuiz = $("screen-quiz");
const screenLoading = $("screen-loading");
const screenResult = $("screen-result");

let current = null;
let startedAt = Date.now();
let chronoInterval = null;

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
}

$("btn-hint").addEventListener("click", () => {
  setMathContent($("eval-hint"), `💡 ${current.hint}`);
  $("eval-hint").hidden = false;
});

$("btn-ans").addEventListener("click", () => {
  setMathContent($("eval-answer"), `✅ ${current.answer}`);
  $("eval-answer").hidden = false;
});

async function handleAnswer(isCorrect) {
  const usedHint = !$("eval-hint").hidden;
  recordAnswer({
    id: current.id,
    chapter: current.chapter_id,
    notion: current.notion,
    difficulty: current.difficulty,
    correct: isCorrect,
    usedHint,
    mode: "evaluation",
  });

  const data = await api.answer(current.id, isCorrect);
  if (data.finished) {
    clearInterval(chronoInterval);
    localStorage.setItem("lumis:last_level", JSON.stringify({ level: data.level, label: data.level_label, icon: data.level_icon }));
    localStorage.setItem("lumis:practice_choices", JSON.stringify(data.practice_choices || []));
    $("result-icon").textContent = data.level_icon;
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

async function init() {
  let chapters = [];
  try {
    chapters = JSON.parse(localStorage.getItem("lumis:selected_chapters")) || [];
  } catch {
    chapters = [];
  }
  const data = await api.start(chapters);
  startChrono();
  showQuestion(data.progress, data.exercise);
}

init();
