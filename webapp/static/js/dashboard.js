import { initSettingsManager, onSettingsChange, getSettings } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { getAccentColor, getAccentColorSecondary } from "./theme.js";
import { bindLiveTranslations } from "./i18n.js";
import {
  getState,
  hydrateFromServer,
  computeStreak,
  masteryByChapter,
  coverageByChapter,
  levelFromXp,
  badgeDefs,
  accuracyOutOf20,
  getChapterStatus,
  scopedStats,
  notionBreakdown,
  getInProgressSeries,
} from "./store.js";
import { getStoredClassLevel } from "./curriculumSelector.js";
import { renderResumeCard } from "./resume.js";
import { renderCourseResumeCard } from "./courseResume.js";
import { getChaptersMeta, buildSeriesRow } from "./seriesview.js";
import { icon } from "./icons.js";
import { badgeIconSvg } from "./badgeIcons.js";
import { api } from "./api.js";
import { isPedagogyFree } from "./pedagogyFree.js";
import { animateCount } from "./animations.js";
import { mountGuestLockOverlay, dismissGuestLockOverlay, unmountGuestLockOverlay } from "./guestLockOverlay.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));
renderResumeCard(document.getElementById("resume-card"));
renderCourseResumeCard(document.getElementById("course-resume-card"));

const $ = (id) => document.getElementById(id);
const RING_CIRCUMFERENCE = 2 * Math.PI * 18;

let chartWindow = 5;
let chaptersMeta = [];
let currentUser = null;
let lastChartSeries = [];

function initials(name) {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

// ── Mode invité : Dashboard verrouillé après la première découverte ─────────
// La toute première consultation du Dashboard par un invité (juste après son
// évaluation initiale) reste entièrement libre. Dès la consultation suivante
// (retour sur le Dashboard, ou nouvelle évaluation), le contenu du Dashboard
// — et uniquement lui, jamais la sidebar/navigation — est flouté, avec une
// carte de déverrouillage au-dessus. "Continuer en mode invité" ferme
// seulement la carte (le flou reste) ; ce choix ne doit pas revenir hanter
// l'utilisateur à chaque re-rendu pendant la session en cours (sessionStorage).
const GUEST_LOCK_CARD_DISMISS_KEY = "novamath:guest_lock_card_dismissed";
const GUEST_LOCK_OVERLAY_ID = "dashboard-guest-lock-overlay";

function applyGuestDashboardLock(locked) {
  const content = $("dashboard-content");

  if (!locked) {
    unmountGuestLockOverlay(content, GUEST_LOCK_OVERLAY_ID);
    return;
  }

  // Le flou reste posé pour le reste de la session dès que le Dashboard est
  // verrouillé, même si la popup a déjà été fermée ("Continuer en mode
  // invité" ne fait fermer QUE la popup, jamais lever le flou — voir
  // dismissGuestLockOverlay).
  content.classList.add("guest-lock-target");
  if (sessionStorage.getItem(GUEST_LOCK_CARD_DISMISS_KEY)) {
    dismissGuestLockOverlay(GUEST_LOCK_OVERLAY_ID);
    return;
  }

  const overlay = mountGuestLockOverlay(content, {
    id: GUEST_LOCK_OVERLAY_ID,
    icon: "star",
    title: "Créez votre compte Mathadap",
    description: "Vous avez découvert Mathadap en mode invité.<br>Créez gratuitement votre compte pour :",
    listItems: [
      "sauvegarder votre progression ;",
      "retrouver vos statistiques ;",
      "accéder à votre historique ;",
      "personnaliser votre profil ;",
      "débloquer un Dashboard permanent.",
    ],
    actionsHtml: `
      <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
      <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
      <button type="button" class="btn btn-ghost" id="btn-guest-lock-dismiss">Continuer en mode invité</button>
    `,
  });
  overlay.querySelector("#btn-guest-lock-dismiss").addEventListener("click", () => {
    sessionStorage.setItem(GUEST_LOCK_CARD_DISMISS_KEY, "1");
    dismissGuestLockOverlay(GUEST_LOCK_OVERLAY_ID);
  });
  overlay.querySelectorAll(".js-open-signup, .js-open-login").forEach((btn) => {
    btn.addEventListener("click", () => dismissGuestLockOverlay(GUEST_LOCK_OVERLAY_ID));
  });
}

function renderAccountCard(user) {
  currentUser = user;
  $("account-avatar").innerHTML = "";
  if (user.avatar) {
    const img = document.createElement("img");
    img.src = user.avatar;
    img.alt = "";
    $("account-avatar").appendChild(img);
  } else {
    $("account-avatar").textContent = initials(user.pseudo);
  }
  $("account-pseudo").textContent = user.pseudo;
  $("account-username").textContent = `@${user.username}`;
  $("account-email").textContent = user.email;
}

// Le dégradé #xpgrad (dashboard.html) est un <linearGradient> SVG statique :
// ses <stop> ne peuvent pas lire une variable CSS nativement, donc on les
// resynchronise en JS à chaque rendu — jamais mis en cache, pour suivre un
// changement d'accent en direct (voir novamath:settings-changed ci-dessous).
function syncXpRingGradient() {
  const stops = document.querySelectorAll("#xpgrad stop");
  if (stops[0]) stops[0].setAttribute("stop-color", getAccentColor());
  if (stops[1]) stops[1].setAttribute("stop-color", getAccentColorSecondary());
}

function render(state) {
  $("greeting").textContent = `Bonjour ${currentUser?.pseudo || "Élève"}`;

  const streak = computeStreak(state.history);
  animateCount($("streak-value"), { to: streak, duration: 700 });

  const { level, progress } = levelFromXp(state.xp);
  $("xp-level").textContent = `Niveau ${level}`;
  animateCount($("xp-value"), { to: state.xp, duration: 900, formatter: (n) => `${Math.round(n)} XP` });
  const offset = RING_CIRCUMFERENCE * (1 - progress);
  syncXpRingGradient();
  $("xp-ring-fill").setAttribute("stroke-dasharray", RING_CIRCUMFERENCE.toFixed(1));
  $("xp-ring-fill").setAttribute("stroke-dashoffset", offset.toFixed(1));

  renderRealTime(state.history);
  renderAccuracy(state.history);
  renderWeekGrid(state.history);
  renderDailyGoal(state.history, streak);
  renderProgressChart(state.series || []);
  renderHeroPriority(state.history);
  // La carte "Série en cours" (resume.js) ne doit jamais dupliquer la
  // recommandation déjà promue dans le hero ci-dessus (priorité 1).
  if (getInProgressSeries()) $("resume-card").hidden = true;
  renderMasteryLists(state.history);
  renderSuggestions(state.history, state.suggestions_limit);
  renderNotionBreakdown(state.history, state.notion_breakdown_enabled);
  renderSeriesTable(state.series || []);
  renderBadges(state.badges);
}

// ── Objectif quotidien (Paramètres → Apprentissage → dailyGoalExercises) ────
// Préférence déjà persistée côté serveur mais jamais affichée nulle part
// avant : cette carte la rend visible et vivante sur le Dashboard, mise à
// jour en direct (voir l'abonnement novamath:settings-changed dans init()).
// Phrase motivante : simple sélection de texte à partir de valeurs déjà
// calculées ci-dessus (done/goal/remaining/reached) et de la série déjà
// calculée dans render() — aucune nouvelle donnée, aucun nouveau calcul.
function dailyGoalMotivation({ done, remaining, reached, streak }) {
  if (reached) {
    return streak >= 3
      ? `${streak} jours d'affilée et l'objectif du jour atteint — belle régularité.`
      : "Objectif atteint aujourd'hui — prends un instant pour souffler.";
  }
  if (done === 0 && streak > 0) {
    return `Ta série de ${streak} jour${streak > 1 ? "s" : ""} t'attend — une question suffit pour la préserver.`;
  }
  if (done === 0) {
    return "Une première question suffit pour lancer ta journée.";
  }
  if (remaining <= 2) {
    return "Tu y es presque — encore un petit effort.";
  }
  return "Continue, chaque question compte pour ta progression.";
}

function renderDailyGoal(history, streak) {
  const goal = Math.max(1, Number(getSettings()?.learning?.dailyGoalExercises) || 10);
  const today = todayStr();
  const done = history.filter((h) => h.date === today).length;
  const pct = Math.min(100, Math.round((done / goal) * 100));
  const remaining = Math.max(0, goal - done);
  const reached = done >= goal;

  $("daily-goal-value").textContent = `${done} / ${goal} question${goal > 1 ? "s" : ""}`;
  $("daily-goal-fill").style.width = `${pct}%`;
  $("daily-goal-sub").textContent = reached
    ? "Objectif atteint aujourd'hui — bravo !"
    : `Encore ${remaining} question${remaining > 1 ? "s" : ""} pour atteindre ton objectif`;
  $("daily-goal-motivation").textContent = dailyGoalMotivation({ done, remaining, reached, streak });
  $("daily-goal-card").classList.toggle("is-reached", reached);
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function renderRealTime(history) {
  const today = todayStr();
  const now = Date.now();
  const weekMs = 7 * 86400000;

  const sumDuration = (predicate) => history.filter(predicate).reduce((sum, h) => sum + (h.duration_s || 0), 0);

  const todaySeconds = sumDuration((h) => h.date === today);
  const weekSeconds = sumDuration((h) => now - h.ts < weekMs);
  const totalSeconds = sumDuration(() => true);

  $("time-today").textContent = formatDuration(todaySeconds);
  $("time-week").textContent = `Cette semaine : ${formatDuration(weekSeconds)}`;
  $("time-total").textContent = `Depuis le début : ${formatDuration(totalSeconds)}`;
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours} h ${rest.toString().padStart(2, "0")}`;
}

function renderAccuracy(history) {
  const acc = accuracyOutOf20(history);
  $("accuracy-value").textContent = `${acc} / 20`;
  const badge = $("accuracy-badge");
  badge.classList.remove("badge--success", "badge--warning", "badge--danger", "badge--neutral");
  if (!history.length) {
    badge.classList.add("badge--neutral");
    badge.textContent = "Pas encore de données";
  } else if (acc >= 16) {
    badge.classList.add("badge--success");
    badge.textContent = "Excellent";
  } else if (acc >= 10) {
    badge.classList.add("badge--warning");
    badge.textContent = "Correct";
  } else {
    badge.classList.add("badge--danger");
    badge.textContent = "À renforcer";
  }
}

function renderWeekGrid(history) {
  const grid = $("week-grid");
  grid.innerHTML = "";
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  const activeDays = new Set(history.map((h) => h.date));
  days.forEach((day) => {
    const cell = document.createElement("div");
    cell.className = `week-day${activeDays.has(day) ? " active" : ""}`;
    cell.title = day;
    grid.appendChild(cell);
  });
}

// ── Graphique "Résultats au fil des séries" (refonte) ──────────────────────
// viewBox recalculé à chaque rendu à partir des dimensions RÉELLES du <svg>
// (clientWidth/clientHeight) plutôt qu'un viewBox fixe + preserveAspectRatio
// "none" : c'est ce qui causait le rendu étiré/déformé (points ovalisés,
// courbe distendue) signalé sur le dashboard — un viewBox qui correspond
// exactement à la taille affichée élimine toute mise à l'échelle non
// uniforme. Repli sur une taille fixe si le layout n'est pas encore mesurable
// (ex: environnement de test sans moteur de rendu) pour un comportement
// déterministe.
const CHART_FALLBACK_SIZE = { width: 600, height: 220 };
// `bottom` élargi pour loger deux lignes (date + heure, voir xLabels) plutôt
// qu'une seule date sur l'axe horizontal.
const CHART_PAD = { left: 34, right: 14, top: 14, bottom: 36 };

// Date affichée sur l'axe/tooltip à partir de `endedAt` (timestamp réel),
// jamais du champ `date` persisté (dérivé en UTC côté store.js) — toLocaleDateString
// respecte nativement le fuseau horaire du navigateur de l'utilisateur.
function formatChartDate(s) {
  return new Date(s.endedAt || s.startedAt || Date.now()).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
  });
}

function formatChartTime(s) {
  return new Date(s.endedAt || s.startedAt || Date.now()).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Libellé lisible "X bonne(s) réponse(s) sur Y — Z%" (point 2 du cahier des
// charges) : jamais de pourcentage seul, toujours le score exact à côté.
function chartScoreLabel(s) {
  return `${s.score} bonne${s.score === 1 ? "" : "s"} réponse${s.score === 1 ? "" : "s"} sur ${s.total} — ${s.accuracy}%`;
}

// Fenêtre demandée (5/15/all) vs nombre de points réellement disponibles
// (point 5 du cahier des charges) : avec peu de séries, les fenêtres plus
// larges affichent forcément le même historique — ce n'est jamais un bug,
// seulement un fait à annoncer discrètement plutôt qu'à laisser deviner.
function updateChartWindowNote(requestedWindow, shownCount, totalAvailable) {
  const el = $("chart-window-note");
  if (requestedWindow === "all" || shownCount >= Number(requestedWindow)) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.textContent = `${totalAvailable} série${totalAvailable > 1 ? "s" : ""} disponible${totalAvailable > 1 ? "s" : ""} sur les ${requestedWindow} dernières demandées`;
}

function renderProgressChart(series) {
  lastChartSeries = series;
  const svg = $("progress-chart");
  const tooltip = $("chart-tooltip");

  if (!series.length) {
    svg.setAttribute("viewBox", `0 0 ${CHART_FALLBACK_SIZE.width} ${CHART_FALLBACK_SIZE.height}`);
    svg.innerHTML = `<text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" fill="var(--text-faint)" font-size="13">Termine une série pour voir ta progression</text>`;
    tooltip.style.display = "none";
    $("chart-window-note").hidden = true;
    return;
  }

  const windowed = chartWindow === "all" ? series : series.slice(-chartWindow);
  updateChartWindowNote(chartWindow, windowed.length, series.length);

  const width = svg.clientWidth || CHART_FALLBACK_SIZE.width;
  const height = svg.clientHeight || CHART_FALLBACK_SIZE.height;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  const left = CHART_PAD.left;
  const right = width - CHART_PAD.right;
  const top = CHART_PAD.top;
  const bottom = height - CHART_PAD.bottom;
  const plotWidth = Math.max(1, right - left);
  const plotHeight = Math.max(1, bottom - top);

  // Répartition harmonieuse sur TOUTE la largeur utile, quel que soit le
  // nombre de points — jamais d'espacement plafonné/centré qui compressait
  // artificiellement le tracé au milieu du cadre quel que soit le bouton
  // 10/20/50/Tout sélectionné (cause du graphique "trop petit et concentré").
  const n = windowed.length;
  const points = windowed.map((s, i) => ({
    x: n > 1 ? left + (i / (n - 1)) * plotWidth : left + plotWidth / 2,
    y: top + (1 - s.accuracy / 100) * plotHeight,
    s,
  }));

  const accent1 = getAccentColor();
  const accent2 = getAccentColorSecondary();

  // Repères horizontaux légers + graduations verticales lisibles (0/25/50/75/100%).
  const gridLines = [0, 25, 50, 75, 100]
    .map((pct) => {
      const y = (top + (1 - pct / 100) * plotHeight).toFixed(1);
      return `<line x1="${left}" y1="${y}" x2="${right}" y2="${y}" stroke="var(--border)" stroke-width="1" opacity="0.5"/><text x="${(left - 7).toFixed(1)}" y="${y}" text-anchor="end" dominant-baseline="middle" font-size="9.5" fill="var(--text-faint)">${pct}%</text>`;
    })
    .join("");

  // Repères temporels sur l'axe horizontal, sur deux lignes (date puis
  // heure, ex. "19/10" / "14:35") : la date n'est réaffichée que lorsqu'elle
  // change (plusieurs séries le même jour ne répètent pas "19/10" à chaque
  // point), mais l'HEURE, elle, est toujours affichée pour chaque libellé
  // conservé — c'est elle qui permet de distinguer plusieurs séries du même
  // jour. Avec beaucoup de points sur un espace étroit (mobile, fenêtre
  // Tout), afficher un libellé par point les ferait se chevaucher : un
  // libellé n'est conservé que s'il est à bonne distance en pixels du
  // précédent RÉELLEMENT affiché — jamais un simple pas d'index régulier
  // (qui pouvait encore faire chevaucher le tout dernier point et son voisin
  // direct), et le survol reste la source complète (date + heure) dans tous
  // les cas.
  const MIN_LABEL_SPACING_PX = 34;
  let lastDateLabel = null;
  let lastLabelX = -Infinity;
  const xLabels = points
    .map((p, i) => {
      if (i !== 0 && p.x - lastLabelX < MIN_LABEL_SPACING_PX) return "";
      lastLabelX = p.x;
      const dateLabel = formatChartDate(p.s);
      const showDate = dateLabel !== lastDateLabel;
      lastDateLabel = dateLabel;
      const dateText = showDate
        ? `<text x="${p.x.toFixed(1)}" y="${(bottom + 16).toFixed(1)}" text-anchor="middle" font-size="9.5" fill="var(--text-faint)">${dateLabel}</text>`
        : "";
      const timeText = `<text x="${p.x.toFixed(1)}" y="${(bottom + 27).toFixed(1)}" text-anchor="middle" font-size="8.5" fill="var(--text-faint)" opacity="0.85">${formatChartTime(p.s)}</text>`;
      return dateText + timeText;
    })
    .join("");

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const dots = points
    .map(
      (p, i) =>
        `<circle data-idx="${i}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="${accent2}" class="chart-dot"/>`,
    )
    .join("");
  const hitAreas = points
    .map(
      (p, i) =>
        `<circle data-idx="${i}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="12" fill="transparent" class="chart-hit"/>`,
    )
    .join("");

  svg.innerHTML = `
    ${gridLines}
    ${xLabels}
    <path d="${path}" fill="none" stroke="url(#linegrad)" stroke-width="2" stroke-linecap="round" style="transition: d 300ms ease;"/>
    ${dots}
    ${hitAreas}
    <defs><linearGradient id="linegrad" x1="0" y1="0" x2="${width}" y2="0"><stop offset="0" stop-color="${accent1}"/><stop offset="1" stop-color="${accent2}"/></linearGradient></defs>
  `;

  svg.querySelectorAll(".chart-hit").forEach((hit) => {
    hit.addEventListener("mousemove", () => {
      const idx = Number(hit.dataset.idx);
      const point = points[idx];
      const rect = svg.getBoundingClientRect();
      const scaleX = rect.width / width;
      const scaleY = rect.height / height;
      tooltip.style.display = "block";
      tooltip.style.left = `${point.x * scaleX + 12}px`;
      tooltip.style.top = `${point.y * scaleY - 10}px`;
      const d = point.s;
      const label = d.notion ? `${d.chapterId || ""} · ${d.notion}` : d.chapterId || "Mixte";
      tooltip.innerHTML = `<strong>${chartScoreLabel(d)}</strong><br>${label}<br>${formatChartDate(d)} à ${formatChartTime(d)}`;
    });
    hit.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });
  });
}

// Redessine le graphique quand la taille réelle du conteneur change (resize
// fenêtre, rotation mobile) — le viewBox dépend des dimensions mesurées, donc
// un simple CSS fluide ne suffit pas à garder les points/graduations alignés.
let chartResizeTimer = null;
window.addEventListener("resize", () => {
  clearTimeout(chartResizeTimer);
  chartResizeTimer = setTimeout(() => renderProgressChart(lastChartSeries), 150);
});

// ── Répartition dashboard par plan (simplifiée en 5/15/Tout, Chantier
// "Simplifier les fenêtres du graphique") : le backend (/api/stats, voir
// server.py::_STATS_SERIES_WINDOW) limite déjà `series[]` à la fenêtre
// autorisée par le plan EFFECTIF — ces boutons ne font qu'exposer/verrouiller
// visuellement les fenêtres que l'utilisateur n'a pas le droit d'atteindre,
// jamais une deuxième logique de filtrage (la donnée reçue est déjà la
// bonne, on ne fait qu'informer).
const PLAN_WINDOW_ACCESS = { free: ["5"], premium: ["5", "15"], ultra: ["5", "15", "all"] };
const WINDOW_LOCK_PLAN_LABEL = { 15: "Premium", all: "Ultra" };

// Gratuité pédagogique : toutes les fenêtres du graphique sont accessibles
// (le serveur renvoie alors l'historique complet, voir pedagogy_plan).
const windowPlan = (plan) => (isPedagogyFree() ? "ultra" : plan);

function applyChartWindowLocks(plan) {
  plan = windowPlan(plan);
  const allowed = PLAN_WINDOW_ACCESS[plan] || PLAN_WINDOW_ACCESS.free;
  document.querySelectorAll(".chart-zoom-btn").forEach((btn) => {
    const w = btn.dataset.window;
    const locked = !allowed.includes(w);
    btn.classList.toggle("is-locked", locked);
    btn.disabled = locked;
    // Un bouton qui redevient verrouillé (rétrogradation de plan) ne doit
    // jamais rester visuellement "actif" (dégradé violet plein) en même
    // temps que verrouillé — ce cumul de classes laissait croire que la
    // fenêtre restait sélectionnée/utilisable alors qu'elle ne l'était plus.
    // Le choix de la fenêtre de repli revient à refreshChartWindowForPlan().
    if (locked) btn.classList.remove("active");
    let badge = btn.querySelector(".chart-zoom-lock-badge");
    if (locked) {
      btn.title = `Fonctionnalité ${WINDOW_LOCK_PLAN_LABEL[w]}`;
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "chart-zoom-lock-badge";
        badge.textContent = WINDOW_LOCK_PLAN_LABEL[w];
        btn.appendChild(badge);
      }
    } else {
      btn.removeAttribute("title");
      badge?.remove();
    }
  });
}

// ── Réaction à un changement de plan EFFECTIF (test Owner, changement réel
// d'abonnement) : deux problèmes corrigés ici (le verrouillage visuel seul,
// posé par applyChartWindowLocks ci-dessus, ne suffisait pas) —
// (1) si la fenêtre actuellement sélectionnée vient d'être verrouillée
// (ex: "Tout" en Ultra puis rétrogradation Free), il faut retomber sur "5"
// (seule fenêtre toujours autorisée) plutôt que de rester bloqué sur un
// bouton désormais désactivé ; (2) la fenêtre de données RÉELLEMENT
// disponible dépend du plan côté serveur (server.py::_STATS_SERIES_WINDOW) —
// le tableau `series[]` déjà en mémoire a été récupéré sous l'ANCIEN plan et
// peut être trop court (upgrade : Free->Premium ne contenait que 5 séries en
// mémoire, la 15 vient d'être débloquée mais les données ne sont pas encore
// là) ou simplement périmé. Un nouvel appel GET /api/stats, systématique,
// est donc nécessaire pour que les boutons déverrouillés correspondent à de
// vraies données plutôt qu'à un historique local insuffisant — jamais un
// second filtrage : le serveur reste la seule source de vérité de la
// troncature par plan.
async function refreshChartWindowForPlan(effectivePlan) {
  effectivePlan = windowPlan(effectivePlan);
  const allowed = PLAN_WINDOW_ACCESS[effectivePlan] || PLAN_WINDOW_ACCESS.free;
  if (!allowed.includes(String(chartWindow))) {
    chartWindow = 5;
    document.querySelectorAll(".chart-zoom-btn").forEach((b) => b.classList.toggle("active", b.dataset.window === "5"));
  }
  try {
    const stats = await api.getStats();
    const classLevel = getStoredClassLevel();
    const series = (stats.series || []).filter((s) => (s.class_level || "seconde") === classLevel);
    renderProgressChart(series);
  } catch {
    // Au pire, on garde l'affichage déjà présent (fenêtre déjà corrigée
    // au besoin ci-dessus) plutôt que de casser l'UI pour un échec réseau.
    renderProgressChart(lastChartSeries);
  }
}

document.querySelectorAll(".chart-zoom-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.disabled) return;
    document.querySelectorAll(".chart-zoom-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    chartWindow = btn.dataset.window === "all" ? "all" : Number(btn.dataset.window);
    // `lastChartSeries` (mis à jour à chaque rendu, voir renderProgressChart)
    // plutôt que de relire `getState()` ici : après un changement de plan
    // (refreshChartWindowForPlan ci-dessus), c'est le tableau fraîchement
    // obtenu du serveur qui doit rester la source pour les clics suivants —
    // relire le store local aurait réintroduit un historique périmé/trop
    // court datant de l'ancien plan.
    renderProgressChart(lastChartSeries);
  });
});

function chapterBubbleHtml(chapterId, m, badgeClass, weakestNotion) {
  const meta = chaptersMeta.find((c) => c.id === chapterId);
  const num = chapterId.replace("Chapitre_", "");
  const title = meta?.title || chapterId;
  const coveragePct = meta?.n_exercises ? Math.round((m.covered / meta.n_exercises) * 100) : 0;
  const accuracyPct = Math.round(m.rate * 100);

  return `
    <div class="mini-row" style="align-items:center;">
      <div>
        <div style="font-weight:600; font-size:0.88rem;">Chapitre ${num} — ${title}</div>
        <div style="color:var(--text-muted); font-size:0.78rem; margin-top:2px;">
          Progression ${coveragePct}% · Accuracy
          <span class="badge ${badgeClass}" style="margin-left:2px;">${accuracyPct}%</span>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm btn-goto-chapter" data-chapter="${chapterId}" data-notion="${weakestNotion || ""}">
        ${icon("arrowRight")} Aller au chapitre
      </button>
    </div>`;
}

function weakestNotionOf(history, chapterId) {
  const byNotion = {};
  history
    .filter((h) => h.chapter === chapterId)
    .forEach((h) => {
      byNotion[h.notion] = byNotion[h.notion] || { total: 0, correct: 0 };
      byNotion[h.notion].total += 1;
      if (h.correct) byNotion[h.notion].correct += 1;
    });
  const entries = Object.entries(byNotion).map(([n, v]) => ({ n, rate: v.correct / v.total }));
  entries.sort((a, b) => a.rate - b.rate);
  return entries[0]?.n || "";
}

function bindGotoChapterButtons(container) {
  container.querySelectorAll(".btn-goto-chapter").forEach((btn) => {
    btn.addEventListener("click", () => {
      localStorage.setItem(
        "lumis:open_chapter",
        JSON.stringify({ chapterId: btn.dataset.chapter, notion: btn.dataset.notion || null }),
      );
      window.location.href = "chapitres.html";
    });
  });
}

function renderMasteryLists(history) {
  const mastery = masteryByChapter(history);
  const coverage = coverageByChapter(history);
  const enriched = Object.entries(mastery).map(([ch, m]) => ({ ch, ...m, covered: (coverage[ch] || new Set()).size }));

  // Règle métier unique (Phase N) : mêmes seuils que chapitres.js, via
  // store.js::getChapterStatus — plus de formule propre à ce tableau de bord.
  const mastered = enriched.filter((m) => getChapterStatus(m.ch, history) === "mastered");
  const toReview = enriched.filter((m) => m.rate < 0.6 && m.count >= 1);

  const masteredEl = $("chapters-mastered");
  const reviewEl = $("chapters-to-review");
  masteredEl.innerHTML = mastered.length
    ? mastered.map((m) => chapterBubbleHtml(m.ch, m, "badge--success")).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Aucun chapitre maîtrisé pour l'instant.</p>`;
  reviewEl.innerHTML = toReview.length
    ? toReview.map((m) => chapterBubbleHtml(m.ch, m, "badge--danger", weakestNotionOf(history, m.ch))).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Rien à signaler — continue comme ça !</p>`;

  bindGotoChapterButtons(masteredEl);
  bindGotoChapterButtons(reviewEl);
}

// ── Notions faibles — source de vérité PARTAGÉE entre le hero "À travailler
// maintenant" (renderHeroPriority) et la liste "À renforcer" (renderSuggestions
// ci-dessous) : un seul calcul, jamais deux formules qui pourraient diverger.
// Seuil de 60% inchangé (comportement historique de renderSuggestions).
function computeWeakNotions(history) {
  const byKey = {};
  history.forEach((h) => {
    const key = `${h.chapter}|${h.notion}`;
    byKey[key] = byKey[key] || { chapter: h.chapter, notion: h.notion, total: 0, correct: 0 };
    byKey[key].total += 1;
    if (h.correct) byKey[key].correct += 1;
  });
  return Object.values(byKey)
    .map((v) => ({ chapter: v.chapter, notion: v.notion, rate: v.correct / v.total }))
    .filter((x) => x.rate < 0.6)
    .sort((a, b) => a.rate - b.rate);
}

// `limit` (GET /api/stats::server.py, champ suggestions_limit) : plafond du
// nombre de cartes affichées, différencié par plan effectif (Free 3 /
// Premium 5 / Ultra 8, voir server.py::_SUGGESTIONS_LIMIT_BY_PLAN — SEULE
// source de vérité de ces valeurs, jamais dupliquées ici). Le calcul du
// classement des notions faibles reste strictement inchangé, jamais
// recalculé/inventé côté client. Repli à 3 (comportement historique) si la
// valeur backend est absente/invalide (ancienne réponse en cache, panne
// réseau — voir store.js::hydrateFromServer) : jamais un crash pour un
// champ optionnel.
function renderSuggestions(history, limit) {
  const el = $("suggestions");
  if (!history.length) {
    el.innerHTML = `<div class="suggestion-card">Fais ta première évaluation pour recevoir des suggestions personnalisées.</div>`;
    return;
  }
  const max = Number.isInteger(limit) && limit > 0 ? limit : 3;
  const weak = computeWeakNotions(history).slice(0, max);

  el.innerHTML = weak.length
    ? weak
        .map(
          (w) =>
            `<div class="suggestion-card">Reprends <strong>${w.chapter} : ${w.notion}</strong> — ${Math.round(w.rate * 100)}% de réussite.</div>`,
        )
        .join("")
    : `<div class="suggestion-card">Belle régularité ! Continue l'entraînement pour progresser encore.</div>`;
}

// ── HERO "À travailler maintenant" (Phase 2 refonte Dashboard) ─────────────
// Ordre de priorité (audit Dashboard) : (1) une activité réellement
// interrompue — série d'exercices en cours, via store.js::getInProgressSeries
// (même donnée que resume.js, aucun nouveau calcul) — prime sur toute
// suggestion ; (2) sinon la notion la plus faible (computeWeakNotions, même
// donnée que "À renforcer", jamais une deuxième formule) ; (3) sinon une
// invitation à explorer la suite du programme ; (4) sinon, sans historique du
// tout, le tout premier contenu pertinent. Aucun pourcentage inventé —
// toujours le taux réel calculé depuis history[]. Le CTA réutilise
// bindGotoChapterButtons (déjà utilisé par les listes maîtrise/à revoir),
// donc le même comportement de navigation (localStorage lumis:open_chapter
// -> chapitres.html).
function renderHeroPriority(history) {
  const el = $("hero-priority");

  // Priorité 1 : reprendre une série d'exercices réellement interrompue.
  // Quand ce cas s'applique, la carte secondaire "Série en cours" (resume.js)
  // est masquée (voir render()) pour ne jamais dupliquer la même
  // recommandation à deux endroits de la page.
  const inProgress = getInProgressSeries();
  if (inProgress) {
    const chapter = inProgress.seriesConfig?.chapterId || "Entraînement mixte";
    const notion = inProgress.seriesConfig?.notion || null;
    const total = inProgress.total || 10;
    const seriesIndex = inProgress.seriesIndex || 0;
    el.innerHTML = `
      <div class="hero-priority-eyebrow">Reprendre</div>
      <h2 class="hero-priority-title">${notion || chapter}</h2>
      <p class="hero-priority-reason">Tu t'étais arrêté à la question <strong>${seriesIndex + 1}/${total}</strong> de ta série sur « ${chapter} ». Termine-la pour ne pas perdre ta progression.</p>
      <a href="exercice.html?resume=1" class="btn btn-primary btn-lg">Reprendre ${icon("arrowRight")}</a>
    `;
    return;
  }

  if (!history.length) {
    el.innerHTML = `
      <div class="hero-priority-eyebrow">Ton prochain objectif</div>
      <h2 class="hero-priority-title">Bienvenue sur Mathadap</h2>
      <p class="hero-priority-reason">Choisis un chapitre pour faire ta première série de questions — tes recommandations personnalisées apparaîtront ici dès que tu auras commencé.</p>
      <a href="chapitres.html" class="btn btn-primary btn-lg">Choisir un chapitre ${icon("arrowRight")}</a>
    `;
    return;
  }
  const [weakest] = computeWeakNotions(history);
  if (!weakest) {
    el.innerHTML = `
      <div class="hero-priority-eyebrow">Ton prochain objectif</div>
      <h2 class="hero-priority-title">Tu as bien avancé !</h2>
      <p class="hero-priority-reason">Aucune notion à renforcer pour l'instant — découvre une nouvelle notion pour continuer à progresser.</p>
      <a href="cours.html" class="btn btn-primary btn-lg">Explorer mes cours ${icon("arrowRight")}</a>
    `;
    return;
  }
  const pct = Math.round(weakest.rate * 100);
  const chapterTitle = chaptersMeta.find((c) => c.id === weakest.chapter)?.title || weakest.chapter;
  el.innerHTML = `
    <div class="hero-priority-eyebrow">À travailler maintenant</div>
    <h2 class="hero-priority-title">${weakest.notion}</h2>
    <p class="hero-priority-reason">${chapterTitle} — tu réussis actuellement <strong>${pct}%</strong> des questions sur cette notion. Elle fait partie des points à renforcer.</p>
    <button type="button" class="btn btn-primary btn-lg btn-goto-chapter" data-chapter="${weakest.chapter}" data-notion="${weakest.notion}">Travailler cette notion ${icon("arrowRight")}</button>
  `;
  bindGotoChapterButtons(el);
}

// ── Bilan de progression par notion (Premium+) ──────────────────────────────
// `enabled` (GET /api/stats::server.py, champ notion_breakdown_enabled) :
// seule source de vérité de l'accès — jamais déduit de user.plan côté
// client (voir applyChartWindowLocks ci-dessus pour le contre-exemple à ne
// pas reproduire). Le calcul lui-même (notionBreakdown, store.js) reste
// purement client à partir de history[] déjà reçu en entier, mais n'est
// JAMAIS invoqué quand `enabled` est faux — Free ne calcule ni n'affiche
// rien, seulement la carte verrouillée. Même convention visuelle que
// cours.js::lockedContentCard (dashboard-locked-card, voir dashboard.css) :
// un badge discret, jamais de popup ni de cadenas imposant.
function renderNotionBreakdown(history, enabled) {
  const el = $("notion-breakdown");
  if (!enabled) {
    el.innerHTML = `
      <div class="dashboard-locked-card">
        ${icon("lock")}
        <div>
          <div class="dashboard-locked-title">Bilan détaillé par notion — Premium</div>
          <div class="dashboard-locked-desc">Réussite, temps moyen et tendance sur chaque notion déjà travaillée.</div>
        </div>
      </div>`;
    return;
  }
  if (!history.length) {
    el.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">Fais ta première évaluation pour voir ton bilan par notion.</p>`;
    return;
  }
  const rows = notionBreakdown(history);
  if (!rows.length) {
    el.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem;">Rien à analyser pour l'instant.</p>`;
    return;
  }
  const TREND_LABEL = { up: "↗ En progrès", down: "↘ À surveiller", stable: "→ Stable" };
  const titleFor = (chapterId) => chaptersMeta.find((c) => c.id === chapterId)?.title || chapterId;

  el.innerHTML = `
    <table class="notion-breakdown-table">
      <thead><tr><th>Notion</th><th>Tentatives</th><th>Réussite</th><th>Temps moyen</th><th>Tendance</th></tr></thead>
      <tbody>
        ${rows
          .map(
            (r) => `
          <tr>
            <td>
              <div class="notion-breakdown-name">${r.notion}</div>
              <div class="notion-breakdown-chapter">${titleFor(r.chapter)}</div>
            </td>
            <td class="tabular">${r.count}</td>
            <td><span class="badge ${r.rate >= 0.7 ? "badge--success" : r.rate >= 0.4 ? "badge--warning" : "badge--danger"}">${Math.round(r.rate * 100)}%</span></td>
            <td class="tabular">${formatDuration(r.avgDurationS)}</td>
            <td>${r.trend ? TREND_LABEL[r.trend] : "—"}</td>
          </tr>`,
          )
          .join("")}
      </tbody>
    </table>`;
}

function renderSeriesTable(series) {
  const body = $("history-body");
  body.innerHTML = "";
  const recent = [...series].reverse().slice(0, 8);
  if (!recent.length) {
    body.innerHTML = `<tr><td colspan="11" style="color:var(--text-muted);">Aucune série terminée pour l'instant.</td></tr>`;
    return;
  }
  const titles = {};
  chaptersMeta.forEach((ch) => {
    titles[ch.id] = ch.title;
  });
  recent.forEach((s) => body.appendChild(buildSeriesRow(s, titles)));
}

function renderBadges(unlocked) {
  const grid = $("badges-grid");
  const unlockedSet = new Set(unlocked);
  const defs = badgeDefs();
  $("badges-counter").textContent = `${unlockedSet.size} / ${defs.length}`;
  // Vitrine de trophées : les badges débloqués sont mis en avant en premier,
  // ordre d'affichage uniquement (badgeDefs()/unlockedSet inchangés).
  const ordered = [...defs].sort((a, b) => Number(unlockedSet.has(b.id)) - Number(unlockedSet.has(a.id)));
  grid.innerHTML = ordered
    .map(
      (b) => `
    <div class="badge-tile${unlockedSet.has(b.id) ? " unlocked" : ""}">
      <div class="icon">${badgeIconSvg(b.id)}</div>
      <div class="name">${b.label}</div>
    </div>
  `,
    )
    .join("");
}

// ── Utilisation IA du jour (quota_service.py::QuotaType.CHAT_MESSAGES) ──────
// Source unique : GET /api/quota — jamais recalculé côté client, le serveur
// reste la seule source de vérité de l'usage réel (même principe que
// chatbot.js::refreshQuota, dupliqué ici car les deux pages n'ont aucune
// dépendance commune autre que api.js).
async function renderAiUsageCard() {
  const card = $("ai-usage-card");
  try {
    const { chat_messages: chat } = await api.getQuota();
    card.hidden = false;
    card.classList.toggle("is-unlimited", chat.unlimited);
    card.classList.toggle("is-exhausted", !chat.unlimited && chat.remaining === 0);
    card.classList.toggle(
      "is-low",
      !chat.unlimited && chat.remaining > 0 && chat.remaining <= Math.ceil(chat.limit * 0.15),
    );

    if (chat.unlimited) {
      $("ai-usage-value").innerHTML = 'Illimité <span aria-hidden="true">∞</span>';
      $("ai-usage-fill").style.width = "100%";
      $("ai-usage-sub").textContent = "Aucune limite sur ton plan Ultra";
    } else {
      $("ai-usage-value").textContent = `${chat.used} / ${chat.limit} messages`;
      $("ai-usage-fill").style.width = `${Math.min(100, Math.round((chat.used / chat.limit) * 100))}%`;
      $("ai-usage-sub").textContent =
        chat.remaining > 0
          ? `${chat.remaining} message${chat.remaining > 1 ? "s" : ""} restant${chat.remaining > 1 ? "s" : ""} aujourd'hui`
          : "Limite atteinte — réinitialisée demain";
    }
  } catch {
    /* silencieux : la carte reste masquée plutôt que d'afficher un état cassé */
  }
}

async function init() {
  const { user } = await api.me();
  renderAccountCard(user);
  // `effective_plan` (jamais `plan`) : seul `effective_plan` suit un plan de
  // test Owner en cours (voir auth.py::_public_user) — utiliser `plan` ici
  // laissait les verrous 50/Tout figés sur le plan Free réel pendant un test,
  // ce qui donnait l'impression que ces indicateurs ne changeaient jamais.
  applyChartWindowLocks(user.effective_plan);
  window.addEventListener("novamath:account-updated", (e) => {
    renderAccountCard(e.detail);
    applyChartWindowLocks(e.detail.effective_plan);
    refreshChartWindowForPlan(e.detail.effective_plan);
  });
  renderAiUsageCard();

  if (user.is_guest) {
    const { locked } = await api.guestDashboardSeen();
    applyGuestDashboardLock(locked);
  }

  chaptersMeta = await getChaptersMeta();
  render(scopedStats(getState(), getStoredClassLevel()));
  const fresh = await hydrateFromServer();
  render(scopedStats(fresh, getStoredClassLevel()));

  // Changement de couleur d'accent (Paramètres → Apparence) : redessine
  // immédiatement les graphes déjà affichés, sans reload (voir plan Paramètres,
  // point "communication entre paramètres").
  onSettingsChange((e) => {
    if (!["appearance", "learning", "*"].includes(e.detail.category)) return;
    render(scopedStats(getState(), getStoredClassLevel()));
  });
}

init();
