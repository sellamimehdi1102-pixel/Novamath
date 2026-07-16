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

/** Nombre d'exercices distincts réellement tentés, par chapitre et par notion —
 * base de la "Progression" (couverture), à ne jamais confondre avec l'accuracy. */
function coverageByChapter(history) {
  const byChapter = {};
  history.forEach((h) => {
    if (h.id == null) return;
    byChapter[h.chapter] = byChapter[h.chapter] || new Set();
    byChapter[h.chapter].add(h.id);
  });
  return byChapter;
}

function coverageByNotion(history) {
  const byNotion = {};
  history.forEach((h) => {
    if (h.id == null) return;
    const key = `${h.chapter}|${h.notion}`;
    byNotion[key] = byNotion[key] || new Set();
    byNotion[key].add(h.id);
  });
  return byNotion;
}

function masteryLabel(coveragePct, accuracyPct, count) {
  if (count === 0) return { text: "À faire", cls: "badge--neutral" };
  if (coveragePct >= 70 && accuracyPct >= 70) return { text: "Maîtrisé", cls: "badge--success" };
  if (coveragePct >= 30 || accuracyPct >= 50) return { text: "En progrès", cls: "badge--warning" };
  return { text: "À renforcer", cls: "badge--danger" };
}

function renderChapters(chaptersMeta) {
  const state = getState();
  const chapterCoverage = coverageByChapter(state.history);
  const chapterMastery = masteryByChapter(state.history);
  const notionCoverage = coverageByNotion(state.history);
  const notionMastery = masteryByNotion(state.history);

  grid.innerHTML = "";
  chaptersMeta.forEach((ch) => {
    const coveredIds = chapterCoverage[ch.id] || new Set();
    const progressPct = ch.n_exercises ? Math.round((coveredIds.size / ch.n_exercises) * 100) : 0;
    const accuracyPct = Math.round((chapterMastery[ch.id]?.rate || 0) * 100);
    const remaining = Math.max(0, ch.n_exercises - coveredIds.size);
    const estMinutes = remaining * 3;

    const card = document.createElement("article");
    card.className = "chapter-card card card--interactive";
    card.dataset.id = ch.id;

    const notionsHtml = ch.notions_detail
      .map((n) => {
        const key = `${ch.id}|${n.notion}`;
        const covered = (notionCoverage[key] || new Set()).size;
        const nCoveragePct = n.n_exercises ? Math.round((covered / n.n_exercises) * 100) : 0;
        const nm = notionMastery[key] || { count: 0, rate: 0, last: null };
        const nAccuracyPct = Math.round(nm.rate * 100);
        const mastery = masteryLabel(nCoveragePct, nAccuracyPct, nm.count);
        return `
        <div class="notion-row" data-chapter="${ch.id}" data-notion="${n.notion.replace(/"/g, "&quot;")}" data-ids="${n.exercise_ids.join(",")}">
          <div class="notion-row-top">
            <span>${n.notion}</span>
            <span class="badge ${DIFF_BADGE[n.difficulty_dominant]}">${DIFF_LABEL[n.difficulty_dominant]}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${nCoveragePct}%"></div></div>
          <div class="notion-meta">
            <span>${nm.count}/${n.n_exercises} exercices faits · Accuracy ${nAccuracyPct}% · Temps moyen ${avgDuration(state.history, ch.id, n.notion)}</span>
            <span>Dernier entraînement : ${formatDate(nm.last)}</span>
          </div>
          <div class="notion-meta" style="margin-top:6px;">
            <span class="badge ${mastery.cls}">${mastery.text}</span>
            <span class="notion-launch">Cliquer pour lancer une série ciblée →</span>
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
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <span class="badge ${DIFF_BADGE[ch.difficulty_dominant]}">${DIFF_LABEL[ch.difficulty_dominant]} dominant</span>
        <span class="badge badge--neutral">Réussite ${accuracyPct}%</span>
      </div>
      <button class="chapter-expand-btn" type="button">
        Voir les notions
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <div class="notions-panel">${notionsHtml}</div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.closest(".chapter-expand-btn") || e.target.closest(".notion-row")) return;
      toggleSelection(ch.id, card);
    });
    card.querySelector(".chapter-expand-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      card.classList.toggle("expanded");
    });
    card.querySelectorAll(".notion-row").forEach((row) => {
      row.addEventListener("click", (e) => {
        e.stopPropagation();
        launchNotionSeries(row.dataset.chapter, row.dataset.notion, row.dataset.ids.split(",").map(Number));
      });
    });

    grid.appendChild(card);
  });
}

function avgDuration(history, chapter, notion) {
  const matches = history.filter((h) => h.chapter === chapter && h.notion === notion && h.duration_s);
  if (!matches.length) return "—";
  const avg = matches.reduce((s, h) => s + h.duration_s, 0) / matches.length;
  return `${Math.round(avg)} s`;
}

function launchNotionSeries(chapterId, notion, exerciseIds) {
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: "notion", chapterId, notion, exerciseIds })
  );
  window.location.href = "exercice.html";
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
