// ── Sélection du cursus (classe) ────────────────────────────────────────────
// Source unique de vérité pour "quel programme scolaire est actif" côté
// client : persistance (localStorage, "seconde" par défaut), récupération de
// la liste des programmes disponibles (/api/curricula, alimentée par
// curriculum_registry.py + curriculum_stats.py côté serveur — jamais une
// valeur codée en dur ici), et le composant carte réutilisé à la fois par la
// page de sélection ET par le badge d'en-tête. Aucune branche `if id ===
// "seconde"` nulle part dans ce module : tout provient de la liste renvoyée
// par l'API, ajouter un programme ne touche jamais ce fichier.
import { api } from "./api.js";
import { ICONS } from "./icons.js";

export const CLASS_LEVEL_KEY = "novamath:class_level";
const DEFAULT_CLASS_LEVEL = "seconde";

export function getStoredClassLevel() {
  try {
    return localStorage.getItem(CLASS_LEVEL_KEY) || DEFAULT_CLASS_LEVEL;
  } catch {
    return DEFAULT_CLASS_LEVEL;
  }
}

export function setStoredClassLevel(classLevel) {
  try {
    localStorage.setItem(CLASS_LEVEL_KEY, classLevel);
  } catch {
    /* localStorage indisponible (mode privé strict) — le choix ne survivra
       pas à cette visite, mais la navigation continue de fonctionner. */
  }
}

let _curriculaPromise = null;
/** Un seul appel réseau par chargement de page, même si plusieurs composants
 * (badge d'en-tête + grille de cartes) en ont besoin en même temps. */
export function fetchCurricula() {
  if (!_curriculaPromise) _curriculaPromise = api.getCurricula();
  return _curriculaPromise;
}

const NUMBER_FORMAT = new Intl.NumberFormat("fr-FR");

function statRow(value, label) {
  const stat = document.createElement("div");
  stat.className = "cursus-stat";
  const valueEl = document.createElement("span");
  valueEl.className = "cursus-stat-value tabular";
  valueEl.textContent = NUMBER_FORMAT.format(value);
  const labelEl = document.createElement("span");
  labelEl.className = "cursus-stat-label";
  labelEl.textContent = label;
  stat.append(valueEl, labelEl);
  return stat;
}

/** Composant carte réutilisable représentant UN cursus, quel qu'il soit —
 * utilisé pour Seconde, Première, et tout programme futur sans modification.
 * `onEnter` est appelé avec `curriculum.classLevel` au clic (carte ou CTA). */
export function renderCurriculumCard(curriculum, { isCurrent = false, onEnter } = {}) {
  const card = document.createElement("article");
  card.className = "cursus-card card card--interactive";
  if (isCurrent) card.classList.add("is-current");
  card.setAttribute("aria-label", `${curriculum.label} — Programme officiel`);

  const icon = document.createElement("div");
  icon.className = "cursus-card-icon";
  icon.innerHTML = ICONS.bookOpen;
  icon.setAttribute("aria-hidden", "true");

  if (isCurrent) {
    const badge = document.createElement("span");
    badge.className = "badge badge--indigo cursus-card-current-badge";
    badge.textContent = "Cursus actuel";
    card.appendChild(badge);
  }

  const title = document.createElement("h3");
  title.className = "cursus-card-title";
  title.textContent = curriculum.label;

  const desc = document.createElement("p");
  desc.className = "cursus-card-desc";
  desc.textContent = "Programme officiel";

  const stats = document.createElement("div");
  stats.className = "cursus-card-stats";
  stats.append(
    statRow(curriculum.totalExercises, "exercices"),
    statRow(curriculum.chapters, "chapitres"),
    statRow(curriculum.notions, "notions"),
  );

  const cta = document.createElement("button");
  cta.type = "button";
  cta.className = "btn btn-primary cursus-card-cta";
  cta.innerHTML = `Entrer dans ce cursus ${ICONS.arrowRight}`;

  const enter = (ev) => {
    ev.stopPropagation();
    onEnter?.(curriculum.classLevel);
  };
  cta.addEventListener("click", enter);
  card.addEventListener("click", enter);

  card.append(icon, title, desc, stats, cta);
  return card;
}

// ── Panneau flottant de changement rapide (badge du topnav, toutes pages) ──
// Un seul panneau ouvert à la fois, quelle que soit la page — construit à
// partir de renderCurriculumCard (même carte que choisir-classe.html), donc
// aucune deuxième implémentation du choix de cursus.
let _panel = null;
let _outsideHandler = null;

function closeClassPanel() {
  if (_panel) { _panel.remove(); _panel = null; }
  if (_outsideHandler) {
    document.removeEventListener("mousedown", _outsideHandler);
    _outsideHandler = null;
  }
}

function openClassPanel(buttonEl) {
  if (_panel) { closeClassPanel(); return; }

  const panel = document.createElement("div");
  panel.className = "class-badge-panel card";
  panel.setAttribute("role", "menu");
  panel.setAttribute("aria-busy", "true");
  panel.textContent = "Chargement…";

  const rect = buttonEl.getBoundingClientRect();
  panel.style.top = `${rect.bottom + 8}px`;
  panel.style.left = `${Math.min(rect.left, window.innerWidth - 336)}px`;

  document.body.appendChild(panel);
  _panel = panel;

  fetchCurricula()
    .then((curricula) => {
      const current = getStoredClassLevel();
      panel.removeAttribute("aria-busy");
      panel.innerHTML = "";
      curricula.forEach((curriculum) => {
        panel.appendChild(renderCurriculumCard(curriculum, {
          isCurrent: curriculum.classLevel === current,
          onEnter: (classLevel) => {
            setStoredClassLevel(classLevel);
            closeClassPanel();
            // Met à jour immédiatement le contexte de la page courante — pas
            // de retour à l'accueil, contrairement à choisir-classe.html.
            window.location.reload();
          },
        }));
      });
    })
    .catch(() => {
      panel.removeAttribute("aria-busy");
      panel.innerHTML = '<p class="cursus-select-error">Impossible de charger les classes disponibles pour le moment.</p>';
    });

  _outsideHandler = (e) => {
    if (panel.contains(e.target) || buttonEl.contains(e.target)) return;
    closeClassPanel();
  };
  document.addEventListener("mousedown", _outsideHandler);
}

/** Badge "classe actuelle" d'en-tête, réutilisé sur toutes les pages
 * principales : affiche le libellé de la classe active et ouvre au clic un
 * panneau de changement rapide, sans jamais quitter la page courante. */
export function initClassBadge(buttonEl) {
  if (!buttonEl) return;
  const labelEl = buttonEl.querySelector(".class-badge-label");
  buttonEl.setAttribute("aria-haspopup", "true");
  buttonEl.addEventListener("click", (e) => {
    e.stopPropagation();
    openClassPanel(buttonEl);
  });

  fetchCurricula()
    .then((curricula) => {
      const current = curricula.find((c) => c.classLevel === getStoredClassLevel());
      if (current && labelEl) labelEl.textContent = current.label;
    })
    .catch(() => { /* garde le libellé par défaut déjà affiché dans le HTML */ });
}
