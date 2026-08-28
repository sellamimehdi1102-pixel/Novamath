// ── Détecteur réutilisable de LaTeX affiché en brut ─────────────────────────
// Utilisé à la fois par les tests Vitest (rendu jsdom simulé) et par les
// scripts de vérification navigateur (Playwright, rendu KaTeX réel) : une
// page correctement rendue ne doit plus contenir aucun de ces motifs dans le
// texte visible, qu'ils viennent d'un délimiteur `$...$` resté littéral ou
// d'une commande LaTeX (`\frac`, `\sqrt`...) jamais consommée par KaTeX.
export const RAW_LATEX_PATTERNS = [
  /\$\$?[^$]*\$\$?/, // délimiteur $...$ / $$...$$ resté littéral
  /\\frac\b/, /\\dfrac\b/, /\\sqrt\b/, /\\lim\b/, /\\sum\b/, /\\int\b/,
  /\\vec\b/, /\\alpha\b/, /\\beta\b/, /\\pi\b/, /\\Delta\b/,
  /\\cos\b/, /\\sin\b/, /\\tan\b/, /\\to\b/, /\\cap\b/, /\\cup\b/,
  /\\in\b/, /\\leq\b/, /\\geq\b/, /\\neq\b/, /\\times\b/, /\\div\b/,
  /\\cdot\b/, /\\left\b/, /\\right\b/, /\\mathbb\b/,
];

/** Renvoie la liste des textes de nœuds visibles (hors <script>/<style>/<code>/<pre>,
 * qui peuvent légitimement contenir du texte technique) correspondant à un motif
 * LaTeX non rendu. Vide = aucune régression détectée. */
export function findRawLatexInDom(root) {
  const found = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      // `annotation`/`.katex-mathml` : KaTeX y stocke volontairement le LaTeX
      // source (accessibilité/MathML), visuellement masqué — ce n'est jamais
      // une régression, juste du texte technique légitime, invisible à l'écran.
      const tag = node.parentElement?.closest("script, style, code, pre, annotation, .katex-mathml");
      return tag ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    },
  });
  let node;
  while ((node = walker.nextNode())) {
    const text = node.textContent;
    for (const pattern of RAW_LATEX_PATTERNS) {
      if (pattern.test(text)) {
        found.push(text.trim().slice(0, 120));
        break;
      }
    }
  }
  return found;
}
