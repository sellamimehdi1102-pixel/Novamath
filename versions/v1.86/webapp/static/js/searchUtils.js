// ── Petits utilitaires partagés par les barres de recherche (Cours,
// Exercices) — indépendants de toute page, aucune dépendance au DOM. ────────

// Plage Unicode des diacritiques combinants laissés par String.normalize("NFD")
// (U+0300 a U+036F), en notation d'échappement explicite plutôt qu'en
// caractères littéraux pour rester stable quel que soit l'éditeur/encodage.
const DIACRITICS_RE = /[\u0300-\u036f]/g;

/** Minuscules + accents retires, pour une recherche insensible a la casse et
 * aux accents ("vecteur" trouve "Vecteurs", "ecole" trouve "Ecole"). */
export function normalizeText(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(DIACRITICS_RE, "")
    .toLowerCase()
    .trim();
}

export function debounce(fn, wait = 250) {
  let timer;
  function debounced(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  }
  debounced.cancel = () => clearTimeout(timer);
  return debounced;
}

/** Encadre la premiere occurrence de `query` dans `text` avec <mark> — pour
 * un apercu de correspondance dans les resultats de recherche. `text` doit
 * deja etre sur a injecter en HTML (jamais appele sur du contenu utilisateur
 * non echappe dans ce projet — titres de chapitres/notions uniquement). */
export function highlightMatch(text, query) {
  const q = normalizeText(query);
  if (!q) return text;
  const norm = normalizeText(text);
  const idx = norm.indexOf(q);
  if (idx === -1) return text;
  return `${text.slice(0, idx)}<mark>${text.slice(idx, idx + q.length)}</mark>${text.slice(idx + q.length)}`;
}
