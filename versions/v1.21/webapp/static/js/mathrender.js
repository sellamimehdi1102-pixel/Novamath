// ── Rendu des énoncés : KaTeX pour le LaTeX déjà présent dans la banque,
// + un "prettifier" de secours qui transforme les rares notations brutes
// résiduelles (2*5, sqrt(x)...) en texte lisible, sans jamais toucher au
// contenu déjà en LaTeX/français rédigé.
const RAW_PATTERNS = [
  [/sqrt\(([^)]+)\)/g, "√($1)"],
  [/(\d+)\s*\*\s*(\d+)/g, "$1 × $2"],
  [/(\d+)\s*\*\s*([a-zA-Z])/g, "$1$2"],
  [/([a-zA-Z])\s*\*\s*(\d+)/g, "$1 × $2"],
  [/([a-zA-Z])\s*\*\s*([a-zA-Z])/g, "$1 × $2"],
];

function prettify(text) {
  if (!text) return text;
  let out = text;
  for (const [pattern, replacement] of RAW_PATTERNS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

export function setMathContent(el, text) {
  el.innerHTML = prettify(text || "").replace(/\n/g, "<br>");
  if (window.renderMathInElement) {
    window.renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
    });
  }
}
