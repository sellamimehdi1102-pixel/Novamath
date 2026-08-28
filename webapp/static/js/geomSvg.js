// ── Générateur de figures SVG, déclaratif et léger ──────────────────────────
// Utilisé par cours.js pour illustrer automatiquement les notions (géométrie,
// fonctions, trigonométrie, statistiques, probabilités, suites, dérivation,
// solides...). Un "spec" décrit une figure ; ce module la convertit en SVG et
// respecte le thème (currentColor + var(--accent)) pour rester cohérent avec
// l'apparence choisie par l'utilisateur (thème, accent, transparence).
//
// `spec.kind` sélectionne le moteur de rendu :
//   - absent ou "geom"  : figure en coordonnées mathématiques (repère,
//                         vecteurs, droites, courbes de fonction, angles...)
//   - "tree"            : arbre de probabilités pondéré
//   - "venn"            : diagramme de Venn (deux ensembles)
//   - "nested-sets"     : ensembles emboîtés (N ⊂ Z ⊂ D ⊂ Q ⊂ R)
//   - "numberline"      : droite graduée (intervalles, multiples...)
//   - "bars"            : diagramme en bâtons / histogramme
//   - "pie"             : diagramme circulaire
//   - "boxplot"         : boîte à moustaches
//   - "solid"           : solide usuel (cube, cylindre, cône, sphère...)
// ── Mise à l'échelle dynamique — le canevas n'est plus forcé au carré : on
// calcule un pas (px par unité mathématique) commun aux deux axes (pour ne
// pas déformer cercles/angles), puis on dimensionne le SVG exactement à la
// taille du viewBox mis à l'échelle. Résultat : des figures bien plus
// grandes et lisibles, sans espace perdu quand le repère n'est pas carré.
const TARGET_W = 620, TARGET_H = 460;
const UNIT_MIN = 34, UNIT_MAX = 120;
const PAD_L = 50, PAD_R = 30, PAD_T = 30, PAD_B = 50;

// ── Rendu mathématique réel (KaTeX) pour les labels de figures ─────────────
// Les labels de points/vecteurs/arcs ("x₁ = 0", "S(α ; β)", "x₂ = 7/4"...)
// étaient jusqu'ici de simples chaînes SVG <text> : aucune vraie fraction,
// aucun exposant/indice correctement dessiné. On les fait maintenant passer
// par KaTeX (déjà chargé globalement sur les pages de cours, voir
// mathrender.js) via un <foreignObject>, avec un repli silencieux vers du
// texte SVG brut si KaTeX est indisponible (tests, environnements sans DOM
// complet) — jamais de LaTeX brut affiché, jamais d'exception.
const SUBSCRIPT_DIGITS = { "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9" };

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Convertit une chaîne de label "à la française" (unicode indices/fractions
// écrits en toutes lettres) en source KaTeX. Conversion purement typographique
// — ne change jamais la valeur mathématique ni la formulation pédagogique,
// seulement la façon dont elle est dessinée (vraie fraction au lieu de "7/4").
function toKatexSource(label) {
  let s = String(label)
    .replace(/−/g, "-")
    .replace(/×/g, "\\times ")
    .replace(/±/g, "\\pm ");
  s = s.replace(/([A-Za-z])([₀-₉]+)/g, (_, letter, subs) => {
    const digits = subs.split("").map((c) => SUBSCRIPT_DIGITS[c] ?? c).join("");
    return `${letter}_{${digits}}`;
  });
  s = s.replace(/(-?\d+)\s*\/\s*(\d+)/g, "\\dfrac{$1}{$2}");
  // KaTeX en mode maths ignore les espaces littéraux : on les remplace par
  // une espace maths explicite (\;) entre chaque mot, sinon "signe de a"
  // s'affiche collé ("signedea"). Chaque mot francophone de 2 lettres ou
  // plus est mis en texte droit (\text) pour ne pas être dessiné en
  // italique comme une variable ; les tokens restants (nombres, fractions
  // déjà converties, variables, symboles) restent en mode maths.
  s = s
    .split(/\s+/)
    .filter(Boolean)
    .map((tok) => (/^[A-Za-zÀ-ÖØ-öø-ÿ]{2,}$/.test(tok) ? `\\text{${tok}}` : tok))
    .join("\\;");
  return s;
}

function renderMathHtml(label) {
  if (typeof katex === "undefined" || !label) return null;
  try {
    return katex.renderToString(toKatexSource(label), { throwOnError: false, strict: false, output: "html" });
  } catch {
    return null;
  }
}

// Mesure réelle (DOM) de la taille d'un label déjà converti en HTML/texte —
// utilisée à la fois pour le rendu KaTeX et pour le repli texte brut, afin
// que le système de placement (placeLabel) raisonne sur des tailles fidèles
// plutôt que sur une estimation grossière. jsdom (tests) ne calcule pas de
// vraie mise en page (getBoundingClientRect renvoie 0) : on retombe alors sur
// une estimation par nombre de caractères pour ne jamais produire une boîte
// de taille nulle qui fausserait la détection de collision.
let _measureHost = null;
function measureHtml(html, plainLength, className) {
  if (typeof document === "undefined") return { width: plainLength * 7 + 4, height: 16 };
  if (!_measureHost) {
    _measureHost = document.createElement("div");
    _measureHost.style.cssText = "position:absolute;visibility:hidden;pointer-events:none;left:-9999px;top:-9999px;white-space:nowrap;";
    document.body.appendChild(_measureHost);
  }
  _measureHost.className = className;
  _measureHost.innerHTML = html;
  const rect = _measureHost.getBoundingClientRect();
  // Marge de sécurité (+10 %, +6px) : mesurée avant que les polices KaTeX
  // (webfonts) aient nécessairement fini de charger, cette largeur peut
  // légèrement sous-estimer la largeur réellement rendue une fois insérée
  // dans la figure — observé jusqu'à ~6 % d'écart en conditions réelles.
  // Mieux vaut une boîte un peu trop généreuse (et donc un léger espace
  // en trop) qu'un texte qui déborde du canevas final.
  if (rect.width > 3 && rect.height > 3) return { width: rect.width * 1.1 + 6, height: rect.height * 1.08 + 3 };
  return { width: Math.max(plainLength * 7, 10) + 4, height: 16 };
}

// ── Placement intelligent des labels — évite les chevauchements ────────────
// 8 positions candidates autour de l'ancre (point, sommet d'angle...). On
// choisit la première libre de tout chevauchement avec les labels déjà
// placés dans la même figure (et les zones "occupées" par les courbes) ;
// à défaut, celle qui minimise le chevauchement, puis on la ramène à
// l'intérieur du canevas si besoin. Le canevas est de toute façon agrandi
// ensuite (voir finalizeCanvas) si un label déborde malgré tout, pour ne
// jamais couper un texte.
const LABEL_GAP = 9;
const CANDIDATE_OFFSETS = [
  { dx: 1, dy: -1, ax: "start", ay: "bottom" }, // haut-droite (comportement historique)
  { dx: -1, dy: -1, ax: "end", ay: "bottom" }, // haut-gauche
  { dx: 1, dy: 1, ax: "start", ay: "top" }, // bas-droite
  { dx: -1, dy: 1, ax: "end", ay: "top" }, // bas-gauche
  { dx: 0, dy: -1, ax: "middle", ay: "bottom" }, // haut
  { dx: 0, dy: 1, ax: "middle", ay: "top" }, // bas
  { dx: 1, dy: 0, ax: "start", ay: "middle" }, // droite
  { dx: -1, dy: 0, ax: "end", ay: "middle" }, // gauche
];

// Surface de recouvrement entre deux boîtes, en tenant compte d'une marge de
// sécurité (les boîtes sont virtuellement agrandies avant l'intersection) —
// remplace un simple compteur binaire "ça touche / ça touche pas" par une
// vraie mesure de gravité : un frôlement de 2px ne doit pas coûter autant
// qu'un recouvrement complet, sinon le moteur ne peut pas distinguer un bon
// candidat d'un mauvais quand aucun n'est parfaitement libre.
function overlapFraction(a, b, margin = 4) {
  const ax0 = a.x - margin, ay0 = a.y - margin, ax1 = a.x + a.w + margin, ay1 = a.y + a.h + margin;
  const bx0 = b.x, by0 = b.y, bx1 = b.x + b.w, by1 = b.y + b.h;
  const ix = Math.max(0, Math.min(ax1, bx1) - Math.max(ax0, bx0));
  const iy = Math.max(0, Math.min(ay1, by1) - Math.max(ay0, by0));
  const inter = ix * iy;
  if (inter <= 0) return 0;
  const smallest = Math.max(1, Math.min(a.w * a.h, b.w * b.h));
  return inter / smallest;
}

function boxFromCandidate(anchorPx, size, off) {
  let x = anchorPx[0] + off.dx * LABEL_GAP;
  let y = anchorPx[1] + off.dy * (LABEL_GAP + size.height / 2);
  if (off.ax === "end") x -= size.width;
  else if (off.ax === "middle") x -= size.width / 2;
  if (off.ay === "bottom") y -= size.height;
  else if (off.ay === "middle") y -= size.height / 2;
  return { x, y, w: size.width, h: size.height };
}

// Candidats pour un label "ancré en place" (spec.texts[]) : l'auteur a
// choisi cette position pour une raison précise (centrer une annotation
// dans une zone, ex. "a × b" au milieu d'un rectangle) — on la respecte
// donc en premier choix, et on ne s'en écarte (par petits pas croissants,
// dans l'axe demandé par `anchor`) que si elle chevauche réellement un
// autre élément déjà placé (ex. les annotations de signe d'un trinôme).
function inPlaceCandidates(anchor) {
  const ax = anchor === "end" ? "end" : anchor === "middle" ? "middle" : "start";
  const candidates = [{ dx: 0, dy: 0, ax, ay: "middle" }];
  // Écarte progressivement (verticalement, puis horizontalement — dans les
  // DEUX sens, pas seulement celui suggéré par `anchor` : dans un repère
  // étroit, l'espace libre le plus proche peut très bien être du côté
  // opposé au sens de lecture du label) — nécessaire quand le repère est
  // étroit par rapport au nombre d'annotations (ex. figure du signe d'un
  // trinôme, 3 annotations dans une figure haute et étroite).
  for (let n = 1; n <= 7; n++) {
    candidates.push({ dx: 0, dy: -n, ax, ay: "middle" });
    candidates.push({ dx: 0, dy: n, ax, ay: "middle" });
    for (const dir of [1, -1]) {
      candidates.push({ dx: dir * n * 3, dy: 0, ax, ay: "middle" });
      candidates.push({ dx: dir * n * 3, dy: -n, ax, ay: "middle" });
      candidates.push({ dx: dir * n * 3, dy: n, ax, ay: "middle" });
    }
  }
  return candidates;
}

// `state` : { placed: [{x,y,w,h}], width, height } — partagé par tous les
// labels d'une même figure (créé dans renderGeom, réinitialisé à chaque
// appel : aucun état global entre deux figures).
function placeLabel(state, anchorPx, size, candidates = CANDIDATE_OFFSETS) {
  let best = null, bestScore = Infinity;
  for (const off of candidates) {
    const box = boxFromCandidate(anchorPx, size, off);
    // Score = somme des fractions de recouvrement avec tout ce qui est déjà
    // placé (0 = libre, >0 = chevauchement partiel ou total — voir
    // overlapFraction), + pénalité si la boîte sort du canevas connu à ce
    // stade, + très légère préférence pour la position la plus proche de
    // l'ancre d'origine quand plusieurs candidats sont à égalité (évite
    // qu'un label s'éloigne inutilement loin quand une place plus proche
    // est tout aussi libre).
    let score = 0;
    for (const placed of state.placed) score += overlapFraction(box, placed);
    // Pénalité très faible pour un débordement du canevas connu à ce stade —
    // volontairement petite : le canevas est de toute façon agrandi ensuite
    // (finalizeCanvas) pour tout label qui en sort, donc un léger
    // débordement est toujours préférable à un vrai chevauchement (texte
    // sur la courbe, sur un autre label...). Cette pénalité ne sert qu'à
    // départager des candidats par ailleurs équivalents.
    if (box.x < 0 || box.y < 0 || box.x + box.w > state.width || box.y + box.h > state.height) score += 0.08;
    score += 0.0005 * Math.hypot(box.x + box.w / 2 - anchorPx[0], box.y + box.h / 2 - anchorPx[1]);
    if (score < bestScore) {
      bestScore = score;
      best = { off, box };
      if (score === 0) break;
    }
  }
  // Contrairement à une ancienne version de ce moteur, on ne force plus la
  // boîte choisie à rester dans les limites du canevas connu à ce stade :
  // si la meilleure position pour éviter un vrai chevauchement (texte sur
  // la courbe, sur un autre label...) se trouve légèrement en dehors,
  // finalizeCanvas agrandit le SVG final en conséquence. Mieux vaut un
  // canevas élargi qu'un texte ramené de force sur la courbe.
  state.placed.push(best.box);
  return best;
}

// Émet le SVG d'un label mathématique ancré à `anchorPx`, en tenant compte
// des collisions déjà enregistrées dans `state`. `extraClass` reprend les
// mêmes conventions que le texte SVG classique (`geom-label--vector`, etc.)
// pour garder la charte de couleurs existante.
function emitAnchoredLabel(state, anchorPx, rawLabel, extraClass = "", candidates = CANDIDATE_OFFSETS) {
  if (!rawLabel) return { svg: "", box: null };
  const mathHtml = renderMathHtml(rawLabel);
  const className = `geom-label geom-math-label${extraClass ? " " + extraClass : ""}`;
  const size = measureHtml(mathHtml ?? escapeHtml(rawLabel), rawLabel.length, className);
  const { off, box } = placeLabel(state, anchorPx, size, candidates);
  if (mathHtml) {
    return { svg: `<foreignObject x="${box.x}" y="${box.y}" width="${size.width}" height="${size.height}" class="geom-math-fo"><div xmlns="http://www.w3.org/1999/xhtml" class="${className}">${mathHtml}</div></foreignObject>`, box };
  }
  const tx = off.ax === "start" ? box.x : off.ax === "end" ? box.x + box.w : box.x + box.w / 2;
  const ty = box.y + size.height * 0.78;
  return { svg: `<text x="${tx}" y="${ty}" text-anchor="${off.ax}" class="geom-label${extraClass ? " " + extraClass : ""}">${escapeHtml(rawLabel)}</text>`, box };
}

// Émet un label directement rattaché sous une boîte déjà placée (ex. les
// coordonnées d'un point, sous son label — voir spec.showCoords) : pas de
// recherche de candidats indépendante, juste un empilement vertical, pour
// que les deux annotations restent visuellement associées au même point
// plutôt que dispersées chacune de leur côté par le système de collision.
function emitBelowLabel(state, box, rawLabel, extraClass = "") {
  if (!rawLabel || !box) return "";
  const mathHtml = renderMathHtml(rawLabel);
  const className = `geom-label geom-math-label${extraClass ? " " + extraClass : ""}`;
  const size = measureHtml(mathHtml ?? escapeHtml(rawLabel), rawLabel.length, className);
  const belowBox = { x: box.x, y: box.y + box.h + 3, w: size.width, h: size.height };
  state.placed.push(belowBox);
  if (mathHtml) {
    return `<foreignObject x="${belowBox.x}" y="${belowBox.y}" width="${size.width}" height="${size.height}" class="geom-math-fo"><div xmlns="http://www.w3.org/1999/xhtml" class="${className}">${mathHtml}</div></foreignObject>`;
  }
  return `<text x="${belowBox.x}" y="${belowBox.y + size.height * 0.78}" text-anchor="start" class="geom-label${extraClass ? " " + extraClass : ""}">${escapeHtml(rawLabel)}</text>`;
}

// Enregistre une zone occupée (point, échantillon de courbe...) sans y
// placer de label — sert uniquement à faire éviter cette zone par les
// labels placés ensuite (texte/courbe, texte/point).
function occupy(state, px, py, r = 8) {
  state.placed.push({ x: px - r, y: py - r, w: r * 2, h: r * 2 });
}

// Agrandit le canevas final si un label déborde de la zone peinte (grille,
// axes...) — garantit qu'aucune annotation n'est jamais coupée, quelle que
// soit sa longueur, au lieu de la clamper arbitrairement à l'intérieur.
function finalizeCanvas(layout, state, content) {
  let minX = 0, minY = 0, maxX = layout.width, maxY = layout.height;
  for (const b of state.placed) {
    minX = Math.min(minX, b.x);
    minY = Math.min(minY, b.y);
    maxX = Math.max(maxX, b.x + b.w);
    maxY = Math.max(maxY, b.y + b.h);
  }
  const dx = -minX, dy = -minY;
  const width = maxX - minX, height = maxY - minY;
  const wrapped = dx || dy ? `<g transform="translate(${dx},${dy})">${content}</g>` : content;
  return { width, height, content: wrapped };
}

function computeLayout(spec) {
  // Repli défensif : un spec "geom" sans viewBox (ex. kind mal orthographié
  // retombé sur renderGeom par défaut, voir renderFigure ci-dessous) levait
  // une TypeError ("Cannot destructure property 'xmin' of undefined") qui
  // cassait tout le rendu de la page cours — jamais un simple SVG vide.
  const [xmin, ymin, w, h] = spec.viewBox || [-1, -1, 8, 8];
  let unit = Math.min((TARGET_W - PAD_L - PAD_R) / w, (TARGET_H - PAD_T - PAD_B) / h);
  unit = Math.max(UNIT_MIN, Math.min(UNIT_MAX, unit));
  return {
    xmin, ymin, w, h, unit,
    width: w * unit + PAD_L + PAD_R,
    height: h * unit + PAD_T + PAD_B,
  };
}

function project(layout, x, y) {
  const px = PAD_L + (x - layout.xmin) * layout.unit;
  const py = layout.height - PAD_B - (y - layout.ymin) * layout.unit;
  return [px, py];
}

function resolvePoint(spec, ref) {
  if (typeof ref === "string") {
    const p = (spec.points || []).find((pt) => pt.label === ref);
    if (!p) return [0, 0];
    return [p.x, p.y];
  }
  return [ref.x, ref.y];
}

function buildGrid(layout) {
  const { xmin, ymin, w, h } = layout;
  let lines = "";
  for (let x = Math.ceil(xmin); x <= xmin + w; x++) {
    const [x1, y1] = project(layout, x, ymin);
    const [x2, y2] = project(layout, x, ymin + h);
    lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-grid-line"/>`;
  }
  for (let y = Math.ceil(ymin); y <= ymin + h; y++) {
    const [x1, y1] = project(layout, xmin, y);
    const [x2, y2] = project(layout, xmin + w, y);
    lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-grid-line"/>`;
  }
  return lines;
}

// Graduations chiffrées sur les deux axes + repère de l'origine "O". Les
// graduations trop proches des bords (flèches) sont sautées pour ne pas se
// chevaucher avec la pointe de la flèche.
function buildTicks(layout, skipOrigin) {
  const { xmin, ymin, w, h } = layout;
  const edgeGuardX = w * 0.05, edgeGuardY = h * 0.05;
  let ticks = "";
  for (let x = Math.ceil(xmin); x <= xmin + w; x++) {
    if (x === 0) continue;
    if (x < xmin + edgeGuardX || x > xmin + w - edgeGuardX) continue;
    const [px, py0] = project(layout, x, 0);
    ticks += `<line x1="${px}" y1="${py0 - 4}" x2="${px}" y2="${py0 + 4}" class="geom-tick"/>`;
    ticks += `<text x="${px}" y="${py0 + 18}" class="geom-tick-label" text-anchor="middle">${x}</text>`;
  }
  for (let y = Math.ceil(ymin); y <= ymin + h; y++) {
    if (y === 0) continue;
    if (y < ymin + edgeGuardY || y > ymin + h - edgeGuardY) continue;
    const [px0, py] = project(layout, 0, y);
    ticks += `<line x1="${px0 - 4}" y1="${py}" x2="${px0 + 4}" y2="${py}" class="geom-tick"/>`;
    ticks += `<text x="${px0 - 9}" y="${py + 4}" class="geom-tick-label" text-anchor="end">${y}</text>`;
  }
  // `skipOrigin` : un point remarquable déjà étiqueté se trouve exactement
  // à l'origine (ex. une racine en x=0) — son propre label suffit, "O" en
  // plus au même endroit serait redondant et se superposerait à ce label
  // et au marqueur du point (générique : ne dépend d'aucune figure précise,
  // seulement de la présence d'un point étiqueté en (0,0)).
  if (!skipOrigin) {
    const [ox, oy] = project(layout, 0, 0);
    ticks += `<text x="${ox - 9}" y="${oy + 16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`;
  }
  return ticks;
}

function buildAxes(layout, axisMarkerId, skipOrigin) {
  const { xmin, ymin, w, h } = layout;
  if (xmin > 0 || xmin + w < 0 || ymin > 0 || ymin + h < 0) return "";
  const [xA1, yA1] = project(layout, xmin, 0);
  const [xA2, yA2] = project(layout, xmin + w, 0);
  const [yA1x, yA1y] = project(layout, 0, ymin);
  const [yA2x, yA2y] = project(layout, 0, ymin + h);
  let out = `
    <line x1="${xA1}" y1="${yA1}" x2="${xA2}" y2="${yA2}" class="geom-axis" marker-end="url(#${axisMarkerId})"/>
    <line x1="${yA1x}" y1="${yA1y}" x2="${yA2x}" y2="${yA2y}" class="geom-axis" marker-end="url(#${axisMarkerId})"/>
    <text x="${xA2 - 6}" y="${yA2 - 8}" class="geom-axis-label">x</text>
    <text x="${yA2x + 10}" y="${yA2y + 4}" class="geom-axis-label">y</text>
  `;
  out += buildTicks(layout, skipOrigin);
  return out;
}

function buildArrowMarker(id, className) {
  return `<marker id="${id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${className}"/>
  </marker>`;
}

// ── kind: "geom" (par défaut) — repère mathématique ─────────────────────────
function renderGeom(spec) {
  const uid = Math.random().toString(36).slice(2, 8);
  const axisMarkerId = `geom-arrow-axis-${uid}`;
  const vectorMarkerId = `geom-arrow-vector-${uid}`;
  const layout = computeLayout(spec);
  let content = "";
  // État de placement des labels — propre à cette figure (voir placeLabel).
  const state = { placed: [], width: layout.width, height: layout.height };
  // Grille légère activée par défaut dès qu'un repère est affiché (sauf
  // désactivation explicite), pour rester lisible sans être surchargée.
  const showGrid = spec.grid === true || (spec.grid !== false && spec.axes);
  if (showGrid) content += buildGrid(layout);
  if (spec.axes) {
    // Un point remarquable étiqueté déjà présent exactement à l'origine
    // (ex. une racine en x=0) rend le "O" des graduations redondant et
    // source de superposition avec son propre label — on le saute alors.
    // Règle générique (position, pas identité de figure).
    const originLabeled = (spec.points || []).some((p) => p.label && Math.abs(p.x) < 1e-9 && Math.abs(p.y) < 1e-9);
    content += buildAxes(layout, axisMarkerId, originLabeled);
    // Le label "O" de l'origine et les graduations chiffrées sont dessinés
    // par buildAxes/buildTicks (hors du système de placement) : on réserve
    // tout de même la zone de l'origine pour qu'un label de point voisin
    // ne vienne pas s'y superposer.
    if (!originLabeled) {
      const [ox, oy] = project(layout, 0, 0);
      occupy(state, ox - 9, oy + 12, 10);
    }
  }

  (spec.curves || []).forEach((c) => {
    const projected = c.points.map(([x, y]) => project(layout, x, y));
    content += `<polyline points="${projected.map((p) => p.join(",")).join(" ")}" class="geom-curve${c.dashed ? " geom-curve--dashed" : ""}" fill="none"/>`;
    // La courbe est enregistrée comme zone occupée pour que les labels
    // évitent de la recouvrir. On interpole entre les points échantillonnés
    // (plutôt que de n'occuper que les points bruts) car une courbe pentue
    // laisserait sinon de grands espaces non couverts entre deux points
    // consécutifs pourtant proches sur le tracé réel.
    for (let i = 0; i < projected.length - 1; i++) {
      const [ax, ay] = projected[i], [bx, by] = projected[i + 1];
      const steps = Math.max(1, Math.round(Math.hypot(bx - ax, by - ay) / 10));
      for (let k = 0; k <= steps; k++) occupy(state, ax + ((bx - ax) * k) / steps, ay + ((by - ay) * k) / steps, 8);
    }
  });

  (spec.polygons || []).forEach((poly) => {
    const pts = poly.points.map((ref) => project(layout, ...resolvePoint(spec, ref)).join(",")).join(" ");
    // `variant` (optionnel) : modificateur de couleur (ex. "a"/"b"/"c" pour
    // distinguer plusieurs polygones dans une même figure — voir figure du
    // théorème de Pythagore). `reveal` (optionnel) : groupe de révélation
    // progressive piloté par cours.js (voir .cours-figure-wrap[data-step]).
    // Les deux sont ignorés si absents : comportement strictement inchangé
    // pour toute figure existante.
    const variantClass = poly.variant ? ` geom-polygon--${poly.variant}` : "";
    const revealClass = poly.reveal ? ` reveal-${poly.reveal}` : "";
    content += `<polygon points="${pts}" class="geom-polygon${variantClass}${revealClass}">${poly.tooltip ? `<title>${poly.tooltip}</title>` : ""}</polygon>`;
  });

  (spec.circles || []).forEach((c) => {
    const [cx, cy] = project(layout, ...resolvePoint(spec, c.center));
    content += `<circle cx="${cx}" cy="${cy}" r="${c.radius * layout.unit}" class="geom-circle"/>`;
  });

  (spec.arcs || []).forEach((a) => {
    const [pcx, pcy] = project(layout, ...resolvePoint(spec, a.center));
    const r = a.radius * layout.unit;
    const startRad = (a.startDeg * Math.PI) / 180;
    const endRad = (a.endDeg * Math.PI) / 180;
    const x1 = pcx + r * Math.cos(startRad), y1 = pcy - r * Math.sin(startRad);
    const x2 = pcx + r * Math.cos(endRad), y2 = pcy - r * Math.sin(endRad);
    const large = Math.abs(a.endDeg - a.startDeg) > 180 ? 1 : 0;
    // `reveal`/`tooltip` (optionnels) : mêmes conventions que polygones et
    // segments — un arc peut apparaître à une étape donnée et porter une
    // infobulle explicative.
    const revealClass = a.reveal ? ` reveal-${a.reveal}` : "";
    content += `<path d="M ${pcx} ${pcy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z" class="geom-angle-arc${revealClass}">${a.tooltip ? `<title>${a.tooltip}</title>` : ""}</path>`;
    if (a.label) {
      const midRad = ((a.startDeg + a.endDeg) / 2) * (Math.PI / 180);
      const lx = pcx + (r + 12) * Math.cos(midRad);
      const ly = pcy - (r + 12) * Math.sin(midRad);
      content += emitAnchoredLabel(state, [lx, ly], a.label).svg;
    }
  });

  (spec.segments || []).forEach((s) => {
    const [x1, y1] = project(layout, ...resolvePoint(spec, s.from));
    const [x2, y2] = project(layout, ...resolvePoint(spec, s.to));
    // `variant`/`reveal` (optionnels) : mêmes conventions que les polygones,
    // pour pouvoir mettre en évidence un segment précis (ex. l'hypoténuse)
    // avec sa propre couleur et/ou le faire apparaître à une étape donnée.
    // `tooltip` (optionnel) : infobulle native au survol (balise <title>),
    // sans aucun JS supplémentaire, ignorée si absente.
    const variantClass = s.variant ? ` geom-segment--${s.variant}` : "";
    const revealClass = s.reveal ? ` reveal-${s.reveal}` : "";
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-segment${s.dashed ? " geom-segment--dashed" : ""}${variantClass}${revealClass}">${s.tooltip ? `<title>${s.tooltip}</title>` : ""}</line>`;
    // Le segment est enregistré comme zone occupée (ex. l'axe de symétrie en
    // pointillés d'une parabole) pour que les labels de points évitent de le
    // recouvrir — voir occupy().
    const steps = Math.max(2, Math.round(Math.hypot(x2 - x1, y2 - y1) / 14));
    for (let i = 0; i <= steps; i++) occupy(state, x1 + ((x2 - x1) * i) / steps, y1 + ((y2 - y1) * i) / steps, 7);
  });

  (spec.vectors || []).forEach((v) => {
    const [x1, y1] = project(layout, ...resolvePoint(spec, v.from));
    const [x2, y2] = project(layout, ...resolvePoint(spec, v.to));
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-vector" marker-end="url(#${vectorMarkerId})"/>`;
    if (v.label) {
      const lx = (x1 + x2) / 2, ly = (y1 + y2) / 2;
      content += emitAnchoredLabel(state, [lx, ly], v.label, "geom-label--vector").svg;
    }
  });

  // Points remarquables — dessinés et enregistrés comme zone occupée
  // MAINTENANT (avant de placer le moindre label), en deux passes séparées
  // du placement de leur propre label (voir plus bas) : cela permet aux
  // annotations de zone (`texts`, ex. "signe de a : +") de réclamer leur
  // place en priorité par rapport aux marqueurs de points déjà connus,
  // plutôt que de devoir se faufiler après coup entre des labels de points
  // qui auraient déjà tout occupé.
  (spec.points || []).forEach((p) => {
    const [px, py] = project(layout, p.x, p.y);
    // `tooltip` (optionnel) : infobulle native au survol du point (balise
    // <title>), pour expliquer le rôle du point sans surcharger la figure.
    content += `<circle cx="${px}" cy="${py}" r="4.5" class="geom-point">${p.tooltip ? `<title>${p.tooltip}</title>` : ""}</circle>`;
    occupy(state, px, py, 6);
  });

  // `texts` sert aussi à annoter une zone précise (ex. "a × b" centré dans un
  // rectangle) : leur position (x,y) reste donc exactement celle donnée par
  // l'auteur — seule la typographie est améliorée (KaTeX). Elles sont
  // néanmoins enregistrées comme occupées pour que les labels de points
  // placés ensuite ne viennent pas les recouvrir. Placées avant les labels
  // de points (voir commentaire ci-dessus) : ces annotations de zone,
  // souvent plus grandes et porteuses d'un sens précis (signe d'un
  // intervalle...), ont la priorité sur les petits labels de points qui,
  // eux, disposent d'une recherche de position dans les 8 directions et
  // peuvent donc plus facilement se faufiler autour.
  (spec.texts || []).forEach((t) => {
    const [x, y] = project(layout, t.x, t.y);
    const weightClass = t.weight ? ` geom-label--${t.weight}` : "";
    const revealClass = t.reveal ? ` reveal-${t.reveal}` : "";
    const anchor = t.anchor || "start";
    const className = `geom-label geom-math-label${weightClass}${revealClass}`;
    const mathHtml = renderMathHtml(t.label);
    const size = measureHtml(mathHtml ?? escapeHtml(t.label || ""), (t.label || "").length, className);
    const { off, box } = placeLabel(state, [x, y], size, inPlaceCandidates(anchor));
    if (mathHtml) {
      content += `<foreignObject x="${box.x}" y="${box.y}" width="${size.width}" height="${size.height}" class="geom-math-fo"><div xmlns="http://www.w3.org/1999/xhtml" class="${className}">${mathHtml}</div></foreignObject>`;
    } else {
      const tx = off.ax === "start" ? box.x : off.ax === "end" ? box.x + box.w : box.x + box.w / 2;
      content += `<text x="${tx}" y="${box.y + size.height * 0.78}" class="geom-label${weightClass}${revealClass}" text-anchor="${off.ax}">${escapeHtml(t.label || "")}</text>`;
    }
  });

  // Labels des points (et leurs coordonnées, voir showCoords) : placés
  // maintenant, une fois que les annotations de zone ont déjà réclamé leur
  // place — voir le commentaire au-dessus de la première passe sur
  // `spec.points`. Le marqueur du point est déjà occupé, donc ces labels
  // ne le recouvriront jamais ; ils cherchent leur place dans les 8
  // directions autour de LEUR PROPRE point, jamais loin de lui.
  (spec.points || []).forEach((p) => {
    if (!p.label && !(p.showCoords || spec.showCoords)) return;
    const [px, py] = project(layout, p.x, p.y);
    let labelBox = null;
    if (p.label) {
      const placed = emitAnchoredLabel(state, [px, py], p.label);
      content += placed.svg;
      labelBox = placed.box;
    }
    if (p.showCoords || spec.showCoords) {
      const coordText = `(${p.x} ; ${p.y})`;
      // Rattachée directement sous le label du point plutôt que replacée
      // indépendamment autour du point (voir emitBelowLabel) : les deux
      // annotations restent visuellement associées au lieu de se disperser.
      content += labelBox
        ? emitBelowLabel(state, labelBox, coordText, "geom-coord-label")
        : emitAnchoredLabel(state, [px, py], coordText, "geom-coord-label").svg;
    }
  });

  (spec.angles || []).forEach((a) => {
    const [cx, cy] = project(layout, ...resolvePoint(spec, a.vertex));
    content += `<circle cx="${cx}" cy="${cy}" r="2.5" class="geom-point"/>`;
    occupy(state, cx, cy, 5);
    if (a.label) content += emitAnchoredLabel(state, [cx, cy], a.label).svg;
  });

  const final = finalizeCanvas(layout, state, content);
  return `
    <svg viewBox="0 0 ${final.width} ${final.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${spec.alt || "Figure géométrique"}">
      <defs>
        ${buildArrowMarker(axisMarkerId, "geom-arrow-head geom-arrow-head--axis")}
        ${buildArrowMarker(vectorMarkerId, "geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${final.content}
    </svg>
  `;
}

// ── kind: "tree" — arbre de probabilités pondéré (2 niveaux) ────────────────
function renderTree(spec) {
  // Toutes les figures non-"geom" sont mises à l'échelle ×1.6 (SCALE) par
  // rapport à leurs dimensions d'origine, pour rester visuellement au même
  // niveau que les repères mathématiques dans la colonne graphique agrandie.
  const W = 672, H = 384;
  const rootX = 48, rootY = H / 2;
  const level1X = 264, level2X = 528;
  const branches = spec.branches || [];
  const n1 = branches.length || 1;
  const gap1 = (H - 64) / n1;
  let content = "";
  branches.forEach((b1, i) => {
    const y1 = 32 + gap1 * (i + 0.5);
    const labelUp = i < n1 / 2; // écarte le libellé du nœud, hors du faisceau des branches filles
    content += `<line x1="${rootX}" y1="${rootY}" x2="${level1X}" y2="${y1}" class="geom-tree-edge"/>`;
    content += `<text x="${(rootX + level1X) / 2}" y="${(rootY + y1) / 2 - 13}" class="geom-tree-proba">${b1.proba || ""}</text>`;
    content += `<text x="${level1X - 10}" y="${labelUp ? y1 - 19 : y1 + 29}" class="geom-tree-label" text-anchor="end">${b1.label}</text>`;
    const b2list = b1.branches || [];
    const n2 = b2list.length || 1;
    const gap2 = 54;
    b2list.forEach((b2, j) => {
      const y2 = y1 + (j - (n2 - 1) / 2) * gap2;
      content += `<line x1="${level1X}" y1="${y1}" x2="${level2X}" y2="${y2}" class="geom-tree-edge"/>`;
      content += `<text x="${(level1X + level2X) / 2}" y="${(y1 + y2) / 2 - 13}" class="geom-tree-proba">${b2.proba || ""}</text>`;
      content += `<text x="${level2X + 16}" y="${y2 + 6}" class="geom-tree-label">${b2.label}</text>`;
    });
  });
  content += `<circle cx="${rootX}" cy="${rootY}" r="6" class="geom-tree-node"/>`;
  branches.forEach((b1, i) => {
    const y1 = 32 + gap1 * (i + 0.5);
    content += `<circle cx="${level1X}" cy="${y1}" r="6" class="geom-tree-node"/>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure geom-figure--wide" role="img" aria-label="${spec.alt || "Arbre de probabilités"}">${content}</svg>`;
}

// ── kind: "venn" — diagramme de Venn à deux ensembles ───────────────────────
function renderVenn(spec) {
  const W = 416, H = 288;
  const r = 109, cx1 = 173, cx2 = 269, cy = 147;
  const [labelA, labelB] = spec.sets || ["A", "B"];
  let content = `
    <circle cx="${cx1}" cy="${cy}" r="${r}" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="${cx2}" cy="${cy}" r="${r}" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="${cx1 - 67}" y="${cy}" class="geom-label">${labelA}</text>
    <text x="${cx2 + 67}" y="${cy}" class="geom-label">${labelB}</text>
  `;
  if (spec.overlapLabel) content += `<text x="${(cx1 + cx2) / 2}" y="${cy + 6}" class="geom-label geom-label--overlap" text-anchor="middle">${spec.overlapLabel}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure geom-figure--wide" role="img" aria-label="${spec.alt || "Diagramme de Venn"}">${content}</svg>`;
}

// ── kind: "nested-sets" — ensembles emboîtés (N ⊂ Z ⊂ D ⊂ Q ⊂ R) ───────────
function renderNestedSets(spec) {
  const W = 416, H = 416, cx = 208, cy = 224;
  const labels = spec.labels || [];
  const n = Math.max(labels.length, 1);
  let content = "";
  labels.forEach((label, i) => {
    const r = 42 + i * (160 / Math.max(n - 1, 1));
    content += `<circle cx="${cx}" cy="${cy}" r="${r}" class="geom-nested-circle"/>`;
    content += `<text x="${cx}" y="${cy - r + 24}" class="geom-label" text-anchor="middle">${label}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure" role="img" aria-label="${spec.alt || "Ensembles emboîtés"}">${content}</svg>`;
}

// ── kind: "numberline" — droite graduée (intervalles, multiples...) ────────
function renderNumberline(spec) {
  const W = 448, H = 144;
  const { min, max } = spec;
  const x0 = 32, x1 = W - 32;
  const scale = (x1 - x0) / (max - min || 1);
  const toX = (v) => x0 + (v - min) * scale;
  const axisY = 72;
  let content = `<line x1="${x0}" y1="${axisY}" x2="${x1}" y2="${axisY}" class="geom-axis"/>`;
  if (spec.highlight) {
    const { from, to } = spec.highlight;
    content += `<line x1="${toX(from)}" y1="${axisY}" x2="${toX(to)}" y2="${axisY}" class="geom-numberline-highlight"/>`;
  }
  (spec.marks || []).forEach((m) => {
    const x = toX(m.value);
    content += `<circle cx="${x}" cy="${axisY}" r="8" class="${m.filled === false ? "geom-point--open" : "geom-point"}"/>`;
    content += `<text x="${x}" y="${axisY + 30}" class="geom-label" text-anchor="middle">${m.label ?? m.value}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure geom-figure--wide" role="img" aria-label="${spec.alt || "Droite graduée"}">${content}</svg>`;
}

// ── kind: "bars" — diagramme en bâtons / histogramme ────────────────────────
function renderBars(spec) {
  const W = 448, H = 288;
  const bars = spec.bars || [];
  const max = spec.maxValue || Math.max(...bars.map((b) => b.value), 1);
  const baseY = H - 48, top = 32;
  const gap = (W - 64) / Math.max(bars.length, 1);
  const barW = gap * 0.6;
  let content = `<line x1="32" y1="${baseY}" x2="${W - 32}" y2="${baseY}" class="geom-axis"/>`;
  bars.forEach((b, i) => {
    const h = ((baseY - top) * b.value) / max;
    const x = 32 + i * gap + (gap - barW) / 2;
    content += `<rect x="${x}" y="${baseY - h}" width="${barW}" height="${h}" class="geom-bar"/>`;
    content += `<text x="${x + barW / 2}" y="${baseY + 26}" class="geom-label" text-anchor="middle">${b.label}</text>`;
    content += `<text x="${x + barW / 2}" y="${baseY - h - 10}" class="geom-label" text-anchor="middle">${b.value}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure geom-figure--wide" role="img" aria-label="${spec.alt || "Diagramme en bâtons"}">${content}</svg>`;
}

// ── kind: "pie" — diagramme circulaire ──────────────────────────────────────
function renderPie(spec) {
  const W = 384, H = 352, cx = 176, cy = 160, r = 112;
  const slices = spec.slices || [];
  const total = slices.reduce((s, x) => s + x.value, 0) || 1;
  let angle = -90;
  let content = "";
  slices.forEach((s, i) => {
    const sweep = (s.value / total) * 360;
    const a0 = (angle * Math.PI) / 180, a1 = ((angle + sweep) * Math.PI) / 180;
    const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0);
    const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1);
    const large = sweep > 180 ? 1 : 0;
    content += `<path d="M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1} Z" class="geom-pie-slice geom-pie-slice--${i % 5}"/>`;
    const midA = ((angle + sweep / 2) * Math.PI) / 180;
    content += `<text x="${cx + (r + 32) * Math.cos(midA)}" y="${cy + (r + 32) * Math.sin(midA) + 6}" class="geom-label" text-anchor="middle">${s.label}</text>`;
    angle += sweep;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure" role="img" aria-label="${spec.alt || "Diagramme circulaire"}">${content}</svg>`;
}

// ── kind: "boxplot" — boîte à moustaches ────────────────────────────────────
function renderBoxplot(spec) {
  const W = 448, H = 160;
  const { min, q1, median, q3, max } = spec;
  const x0 = 32, x1 = W - 32;
  const scale = (x1 - x0) / (max - min || 1);
  const toX = (v) => x0 + (v - min) * scale;
  const midY = 74, boxH = 48;
  let content = `
    <line x1="${toX(min)}" y1="${midY}" x2="${toX(q1)}" y2="${midY}" class="geom-segment"/>
    <line x1="${toX(q3)}" y1="${midY}" x2="${toX(max)}" y2="${midY}" class="geom-segment"/>
    <line x1="${toX(min)}" y1="${midY - boxH / 4}" x2="${toX(min)}" y2="${midY + boxH / 4}" class="geom-segment"/>
    <line x1="${toX(max)}" y1="${midY - boxH / 4}" x2="${toX(max)}" y2="${midY + boxH / 4}" class="geom-segment"/>
    <rect x="${toX(q1)}" y="${midY - boxH / 2}" width="${Math.max(toX(q3) - toX(q1), 1)}" height="${boxH}" class="geom-boxplot-box"/>
    <line x1="${toX(median)}" y1="${midY - boxH / 2}" x2="${toX(median)}" y2="${midY + boxH / 2}" class="geom-boxplot-median"/>
  `;
  [min, q1, median, q3, max].forEach((v) => {
    content += `<text x="${toX(v)}" y="${midY + boxH / 2 + 29}" class="geom-label" text-anchor="middle">${v}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" class="geom-figure geom-figure--wide" role="img" aria-label="${spec.alt || "Boîte à moustaches"}">${content}</svg>`;
}

// ── kind: "solid" — solides usuels (schémas génériques en fil de fer) ───────
const SOLID_PATHS = {
  cube: `
    <polygon points="64,112 208,112 208,256 64,256" class="geom-solid-face"/>
    <polygon points="64,112 120,64 264,64 208,112" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="208,112 264,64 264,208 208,256" class="geom-solid-face geom-solid-face--side"/>
  `,
  pave: `
    <polygon points="48,128 240,128 240,256 48,256" class="geom-solid-face"/>
    <polygon points="48,128 96,80 288,80 240,128" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="240,128 288,80 288,208 240,256" class="geom-solid-face geom-solid-face--side"/>
  `,
  cylindre: `
    <ellipse cx="160" cy="88" rx="88" ry="29" class="geom-solid-face geom-solid-face--top"/>
    <line x1="72" y1="88" x2="72" y2="240" class="geom-segment"/>
    <line x1="248" y1="88" x2="248" y2="240" class="geom-segment"/>
    <path d="M 72 240 A 88 29 0 0 0 248 240" class="geom-solid-face"/>
  `,
  cone: `
    <ellipse cx="160" cy="240" rx="88" ry="26" class="geom-solid-face"/>
    <line x1="72" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="248" y1="240" x2="160" y2="56" class="geom-segment"/>
  `,
  sphere: `
    <circle cx="160" cy="160" r="96" class="geom-circle"/>
    <ellipse cx="160" cy="160" rx="96" ry="29" class="geom-solid-face--wire"/>
    <ellipse cx="160" cy="160" rx="32" ry="96" class="geom-solid-face--wire"/>
  `,
  pyramide: `
    <polygon points="56,240 264,240 192,264 32,264" class="geom-solid-face"/>
    <line x1="56" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="264" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="192" y1="264" x2="160" y2="56" class="geom-segment geom-segment--dashed"/>
    <line x1="32" y1="264" x2="160" y2="56" class="geom-segment"/>
  `,
  prisme: `
    <polygon points="64,256 176,256 144,160 32,160" class="geom-solid-face"/>
    <polygon points="32,160 144,160 208,96 96,96" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="176,256 144,160 208,96 240,192" class="geom-solid-face geom-solid-face--side"/>
  `,
};
const SOLID_LABELS = {
  cube: "Cube", pave: "Pavé droit", cylindre: "Cylindre", cone: "Cône",
  sphere: "Sphère", pyramide: "Pyramide", prisme: "Prisme",
};

function renderSolid(spec) {
  const inner = SOLID_PATHS[spec.shape] || "";
  const label = spec.alt || SOLID_LABELS[spec.shape] || "Solide";
  return `<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${label}">${inner}</svg>`;
}

const RENDERERS = {
  geom: renderGeom,
  tree: renderTree,
  venn: renderVenn,
  "nested-sets": renderNestedSets,
  numberline: renderNumberline,
  bars: renderBars,
  pie: renderPie,
  boxplot: renderBoxplot,
  solid: renderSolid,
};

export function renderFigure(spec) {
  const renderer = RENDERERS[spec.kind] || renderGeom;
  return renderer(spec);
}
