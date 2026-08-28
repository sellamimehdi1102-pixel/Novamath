// ── Exercice sur mesure (Ultra) — Chantier "Différenciateurs Premium/Ultra"
// (2026-08-27). Module ENTIÈREMENT AUTONOME, volontairement séparé de
// exercice.js (845 lignes, boucle de série existante) : cette carte ne
// touche à aucun état de série en cours, aucune quota EXERCISES_DAILY,
// aucun XP — un exercice généré ici n'est jamais posté à
// /api/practice/result (voir server.py::api_practice_generate, distinct de
// _class_bank). Toute régression potentielle reste donc confinée à ce
// fichier, jamais à la boucle de pratique classique.
import { api } from "./api.js";
import { hasFeature } from "./features.js";
import { getStoredClassLevel } from "./curriculumSelector.js";
import { setMathContent } from "./mathrender.js";
import { icon } from "./icons.js";

const $ = (id) => document.getElementById(id);

function lockedHtml() {
  return `
    <div class="dashboard-locked-card">
      ${icon("lock")}
      <div>
        <div class="dashboard-locked-title">Exercice sur mesure — Ultra</div>
        <div class="dashboard-locked-desc">Demande un exercice généré à la demande sur la notion de ton choix, avec correction immédiate.</div>
      </div>
    </div>`;
}

function emptyHtml() {
  return `<p style="color:var(--text-muted); font-size:0.85rem;">Aucune génération disponible pour cette classe pour l'instant.</p>`;
}

// notionsByClass[classLevel] = [{chapter_id, notion, families}, ...]
function groupByClassLevel(notions) {
  const out = {};
  notions.forEach((n) => {
    out[n.class_level] = out[n.class_level] || [];
    out[n.class_level].push(n);
  });
  return out;
}

function selectorHtml(notionsForClass) {
  const notionOptions = notionsForClass
    .map((n, i) => `<option value="${i}">${n.chapter_id} — ${n.notion}</option>`)
    .join("");
  return `
    <label class="sub" for="custom-ex-notion">Notion</label>
    <select id="custom-ex-notion" class="custom-exercise-select">${notionOptions}</select>
    <label class="sub" for="custom-ex-family">Type d'exercice</label>
    <select id="custom-ex-family" class="custom-exercise-select"></select>
    <div class="custom-exercise-actions">
      <button type="button" id="custom-ex-generate" class="btn btn-primary btn-sm">
        ${icon("sparkles")} Générer un exercice
      </button>
    </div>
    <div id="custom-ex-result"></div>
  `;
}

function populateFamilies(notionsForClass) {
  const notionSelect = $("custom-ex-notion");
  const familySelect = $("custom-ex-family");
  if (!notionSelect || !familySelect) return;
  const notion = notionsForClass[Number(notionSelect.value)];
  familySelect.innerHTML = (notion?.families || [])
    .map((f) => `<option value="${f.family_id}">${f.label}</option>`)
    .join("");
}

function renderExercise(ex) {
  const resultEl = $("custom-ex-result");
  if (!resultEl) return;
  resultEl.innerHTML = `
    <div class="question-badges" style="margin-top:12px;">
      <span class="badge badge--indigo">${ex.chapter_id}</span>
      <span class="badge badge--neutral">${ex.notion}</span>
      <span class="badge">${ex.difficulty_emoji || ""} ${ex.difficulty_label || ""}</span>
    </div>
    <div class="custom-exercise-enonce" id="custom-ex-enonce"></div>
    <div class="custom-exercise-actions">
      <button type="button" id="custom-ex-toggle-correction" class="btn btn-secondary btn-sm">Voir la correction</button>
    </div>
    <div id="custom-ex-correction" class="custom-exercise-correction" hidden></div>
  `;
  setMathContent($("custom-ex-enonce"), ex.enonce);

  $("custom-ex-toggle-correction").addEventListener("click", () => {
    const box = $("custom-ex-correction");
    const nowHidden = !box.hidden;
    box.hidden = nowHidden;
    if (!nowHidden && !box.dataset.filled) {
      box.dataset.filled = "1";
      const steps = (ex.solution_steps || []).map((s) => `<li>${s}</li>`).join("");
      box.innerHTML = `<div><strong>Réponse :</strong></div><div id="custom-ex-answer"></div>${steps ? `<ol>${steps}</ol>` : ""}`;
      setMathContent($("custom-ex-answer"), ex.answer);
    }
  });
}

async function handleGenerate(classLevel, notionsForClass) {
  const notionSelect = $("custom-ex-notion");
  const familySelect = $("custom-ex-family");
  const btn = $("custom-ex-generate");
  if (!notionSelect || !familySelect || !btn) return;
  const notion = notionsForClass[Number(notionSelect.value)];
  if (!notion || !familySelect.value) return;

  btn.disabled = true;
  try {
    const { exercise } = await api.practiceGenerate({
      classLevel,
      chapterId: notion.chapter_id,
      notion: notion.notion,
      familyId: familySelect.value,
    });
    renderExercise(exercise);
  } catch {
    const resultEl = $("custom-ex-result");
    if (resultEl) resultEl.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">Impossible de générer un exercice pour l'instant.</p>`;
  } finally {
    btn.disabled = false;
  }
}

async function mount() {
  const body = $("custom-exercise-body");
  if (!body) return;

  const { user } = await api.me();
  if (!hasFeature(user, "custom_exercises")) {
    body.innerHTML = lockedHtml();
    return;
  }

  let notions;
  try {
    ({ notions } = await api.practiceGenerateOptions());
  } catch {
    body.innerHTML = emptyHtml();
    return;
  }

  const byClass = groupByClassLevel(notions || []);
  const classLevel = getStoredClassLevel();
  const notionsForClass = byClass[classLevel] || [];
  if (!notionsForClass.length) {
    body.innerHTML = emptyHtml();
    return;
  }

  body.innerHTML = selectorHtml(notionsForClass);
  populateFamilies(notionsForClass);
  $("custom-ex-notion").addEventListener("change", () => populateFamilies(notionsForClass));
  $("custom-ex-generate").addEventListener("click", () => handleGenerate(classLevel, notionsForClass));
}

mount();
