import { api } from "./api.js";
import { bindThemeToggle } from "./theme.js";
import { getState, masteryByChapter, masteryByNotion } from "./store.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const DIFF_LABEL = { 1: "Facile", 2: "Moyen", 3: "Difficile" };
const DIFF_BADGE = { 1: "badge--success", 2: "badge--warning", 3: "badge--danger" };

const selected = new Set();
const grid = document.getElementById("chapters-grid");
const selectionBar = document.getElementById("selection-bar");
const selectionCount = document.getElementById("selection-count");

function formatDate(ts) {
  if (!ts) return "jamais";
  const diffDays = Math.floor((Date.now() - ts) / 86400000);
  if (diffDays <= 0) return "aujourd'hui";
  if (diffDays === 1) return "hier";
  return `il y a ${diffDays} j`;
}

function chapterIcon() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>`;
}

function renderChapters(chaptersMeta) {
  const state = getState();
  const chapterMastery = masteryByChapter(state.history);
  const notionMastery = masteryByNotion(state.history);

  grid.innerHTML = "";
  chaptersMeta.forEach((ch) => {
    const mastery = chapterMastery[ch.id] || { count: 0, rate: 0 };
    const progressPct = Math.round(mastery.rate * 100);
    const doneExercises = mastery.count;
    const remaining = Math.max(0, ch.n_exercises - doneExercises);
    const estMinutes = remaining * 3;

    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;

    const notionsHtml = ch.notions_detail
      .map((n) => {
        const key = `${ch.id}|${n.notion}`;
        const nm = notionMastery[key] || { count: 0, rate: 0, last: null };
        const status = nm.count === 0 ? "À faire" : nm.rate >= 0.8 ? "Maîtrisé" : "En cours";
        return `
        <div class="notion-row">
          <div class="notion-row-top">
            <span>${n.notion}</span>
            <span class="badge ${DIFF_BADGE[n.difficulty_dominant]}">${DIFF_LABEL[n.difficulty_dominant]}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${Math.round(nm.rate * 100)}%"></div></div>
          <div class="notion-meta">
            <span>${n.n_exercises} exercices · ${status}</span>
            <span>Dernier entraînement : ${formatDate(nm.last)} · Réussite ${Math.round(nm.rate * 100)}%</span>
          </div>
        </div>`;
      })
      .join("");

    card.innerHTML = `
      <div class="chapter-card-top">
        <div class="chapter-icon">${chapterIcon()}</div>
        <div class="chapter-select-dot"></div>
      </div>
      <h3>${ch.title}</h3>
      <div class="chapter-id">${ch.id.replace("_", " ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Progression</span><span>${progressPct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${progressPct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>⏱ ~${estMinutes} min restantes</span>
        <span>📝 ${ch.n_exercises} exercices</span>
        <span>📚 ${ch.n_notions} notions</span>
      </div>
      <span class="badge ${DIFF_BADGE[ch.difficulty_dominant]}" style="margin-bottom:12px; display:inline-block;">${DIFF_LABEL[ch.difficulty_dominant]} dominant</span>
      <button class="chapter-expand-btn" type="button">
        Voir les notions
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <div class="notions-panel">${notionsHtml}</div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.closest(".chapter-expand-btn")) return;
      toggleSelection(ch.id, card);
    });
    card.querySelector(".chapter-expand-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      card.classList.toggle("expanded");
    });

    grid.appendChild(card);
  });
}

function toggleSelection(id, card) {
  if (selected.has(id)) {
    selected.delete(id);
    card.classList.remove("selected");
  } else {
    selected.add(id);
    card.classList.add("selected");
  }
  updateSelectionBar();
}

function updateSelectionBar() {
  const n = selected.size;
  selectionCount.textContent = n === 0 ? "Tous les chapitres (aucune sélection)" : `${n} chapitre${n > 1 ? "s" : ""} sélectionné${n > 1 ? "s" : ""}`;
  selectionBar.classList.add("visible");
}

document.getElementById("btn-start-evaluation").addEventListener("click", (e) => {
  e.preventDefault();
  localStorage.setItem("lumis:selected_chapters", JSON.stringify([...selected]));
  window.location.href = "evaluation.html";
});

api.chapters().then((data) => {
  renderChapters(data.chapters_meta || []);
  selectionBar.classList.add("visible");
});
