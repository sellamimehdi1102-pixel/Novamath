// ── Rendu des énoncés : KaTeX pour le LaTeX déjà présent dans la banque,
// + un "prettifier" de secours qui transforme les rares notations brutes
// résiduelles (2*5, sqrt(x)...) en texte lisible, sans jamais toucher au
// contenu déjà en LaTeX/français rédigé.
const RAW_PATTERNS = [
  // Contenu simple (chiffres/lettres seuls) : parenthèses inutiles à l'oral
  // comme à l'écrit ("sqrt(25)" → "√25"). Les contenus composés (avec un
  // opérateur) gardent leurs parenthèses (règle suivante) pour ne pas
  // introduire d'ambiguïté ("sqrt(x+1)" → "√(x+1)", jamais "√x+1").
  [/sqrt\(([a-zA-Z0-9.]+)\)/g, "√$1"],
  [/sqrt\(([^)]+)\)/g, "√($1)"],
  [/(\d+)\s*\*\s*(\d+)/g, "$1 × $2"],
  [/(\d+)\s*\*\s*([a-zA-Z])/g, "$1$2"],
  [/([a-zA-Z])\s*\*\s*(\d+)/g, "$1 × $2"],
  [/([a-zA-Z])\s*\*\s*([a-zA-Z])/g, "$1 × $2"],
  [/(\d+)\s*\/\s*(\d+)/g, "$1 ÷ $2"],
  [/([a-zA-Z0-9])\^(-?\d+)/g, "$1<sup>$2</sup>"],
];

// Segments déjà entre $...$/$$...$$ sont du LaTeX voulu pour KaTeX (qui gère
// déjà nativement \times, \div, \sqrt, ^) : le prettifier ne doit jamais y
// toucher, sinon "$x^2$" deviendrait "$x<sup>2</sup>$", que KaTeX ne sait
// plus parser (throwOnError:false → rendu vide à la place de "x²").
const MATH_SEGMENT = /(\$\$[^$]+\$\$|\$[^$]+\$)/g;

function prettifyPlainText(str) {
  let out = str;
  for (const [pattern, replacement] of RAW_PATTERNS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

function prettify(text) {
  if (!text) return text;
  return text
    .split(MATH_SEGMENT)
    .map((part, i) => (i % 2 === 1 ? part : prettifyPlainText(part)))
    .join("");
}

// Rendu KaTeX seul, partagé par les deux modes ci-dessous. auto-render
// parcourt le DOM et ignore nativement <code>/<pre>/<script> (option
// ignoredTags intégrée) : jamais de regex sur du texte, toujours DOM-aware.
// \[...\]/\( ... \) (chantier "rendu des formules", 2026-10-18) : convention
// désormais demandée au modèle (prompt_builder.py) — $...$/$$...$$ restent
// reconnus pour ne jamais casser l'affichage des conversations déjà
// persistées avec l'ancienne convention (et la banque d'exercices, voir
// setMathContent ci-dessous).
function renderMathIn(el) {
  if (window.renderMathInElement) {
    window.renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }
}

// ── Protection des formules LaTeX contre l'échappement Markdown ────────────
// CommonMark (donc marked.js, chatbot.js) échappe tout antislash suivi d'un
// caractère de ponctuation ASCII — `(`, `)`, `[`, `]` en font partie. Une
// formule "\(x^2\)" tapée par le modèle perdait donc ses DEUX antislashs dès
// marked.parse(), AVANT même que KaTeX ne voie le texte : il ne restait que
// "(x^2)", sans aucun délimiteur reconnaissable, qui apparaissait alors tel
// quel à l'écran (cause identifiée du LaTeX brut visible, chantier
// "rendu des formules", 2026-10-18 — $...$/$$...$$ n'ont pas ce problème,
// `$` n'étant pas un caractère d'échappement Markdown).
// Solution standard "protéger / parser / restaurer" : chaque segment
// \(...\)/\[...\]/$...$/$$...$$ est extrait du texte brut AVANT
// marked.parse() et remplacé par un jeton inerte qu'aucune règle Markdown ne
// peut altérer (ni échappement, ni emphase, ni liste...), puis réinjecté
// (en texte échappé, jamais en HTML vivant) une fois le HTML produit — voir
// extractMathSegments/restoreMathSegments, utilisées par
// chatbot.js::renderMessageBody. N'affecte jamais le texte ordinaire : un
// antislash hors de ces 4 formes de délimiteurs n'est jamais touché.
const MATH_SEGMENT_RE = /\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$|\$[^$\n]*?\$/g;

function _escapeMathText(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

/** Extrait chaque formule délimitée du texte brut et la remplace par un
 * jeton inerte (texte simple, jamais une syntaxe Markdown/HTML), pour que
 * marked.parse() ne puisse jamais en manger les antislashs ni la mettre en
 * forme par erreur. Renvoie {text, segments} — `segments` est la liste des
 * {placeholder, original} à passer à restoreMathSegments() une fois le
 * Markdown transformé en HTML. Jeton basé sur un nonce aléatoire (différent
 * à chaque appel) : aucun texte réel ne peut le produire par coïncidence, et
 * deux rendus qui se chevauchent (rare, mais déjà vu pendant le streaming)
 * ne peuvent jamais se mélanger. */
export function extractMathSegments(text) {
  if (!text) return { text: text || "", segments: [] };
  const nonce = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
  const segments = [];
  const protectedText = text.replace(MATH_SEGMENT_RE, (match) => {
    const placeholder = ` MATHSEG-${nonce}-${segments.length} `;
    segments.push({ placeholder, original: match });
    return placeholder;
  });
  return { text: protectedText, segments };
}

/** Réinjecte les formules extraites par extractMathSegments() dans le HTML
 * déjà produit par marked.parse() — toujours en texte échappé (jamais du
 * HTML vivant), donc sans risque même si une formule contenait par accident
 * des caractères `<`/`>`/`&`. Remplacement par découpage de chaîne littéral
 * (pas une regex) : le jeton n'est jamais réinterprété. */
export function restoreMathSegments(html, segments) {
  if (!segments || !segments.length) return html;
  let out = html;
  for (const { placeholder, original } of segments) {
    out = out.split(placeholder).join(_escapeMathText(original));
  }
  return out;
}

// Texte brut (banque d'exercices : énoncés, indices, réponses) — jamais du
// HTML. Le prettifier corrige les rares notations non-LaTeX historiques
// (2*5, sqrt(x)) et \n devient <br> puisque ce texte n'est pas structuré.
export function setMathContent(el, text) {
  el.innerHTML = prettify(text || "").replace(/\n/g, "<br>");
  renderMathIn(el);
}

// HTML déjà généré par un parseur Markdown (ex. marked.js côté chatbot) :
// jamais de prettify ni de conversion \n→<br> ici — ce texte est déjà
// structuré en balises de bloc (<p>, <ul>, <table>, <code>...) et le modifier
// corromprait le rendu (cf. audit chatbot). Seul le rendu KaTeX s'applique.
//
// Durcissement production : marked.parse() ne neutralise PAS le HTML brut
// présent dans son entrée (comportement documenté du projet) — un message
// chatbot (utilisateur, ou assistant répétant du HTML lu dans un PDF joint,
// prompt injection classique) contenant p.ex. <img onerror=...> s'exécuterait
// sinon tel quel dans la session de qui le reçoit. sanitizeChatHtml neutralise
// ce HTML AVANT injection dans le DOM, en exportant la logique séparément
// (plutôt qu'inline dans setRenderedHtmlContent) pour rester unitairement
// testable sans dépendre du DOM ni de KaTeX. Fail-safe : DOMPurify absent
// (CDN indisponible) => repli sur un simple retrait de toutes les balises
// (texte brut conservé, lisible, juste non mis en forme) — jamais fail-open
// (jamais le HTML de marked injecté tel quel sans aucune neutralisation).
export function sanitizeChatHtml(html) {
  if (!html) return "";
  if (window.DOMPurify) return window.DOMPurify.sanitize(html);
  return html.replace(/<[^>]*>/g, "");
}

// Les délimiteurs KaTeX ($...$) sont du texte brut au moment du sanitize —
// jamais des balises — donc jamais affectés par sanitizeChatHtml ; le rendu
// LaTeX (renderMathIn, ci-dessous) s'applique ensuite à l'identique.
export function setRenderedHtmlContent(el, html) {
  el.innerHTML = sanitizeChatHtml(html);
  renderMathIn(el);
}
