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

function computeLayout(spec) {
  const [xmin, ymin, w, h] = spec.viewBox;
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
function buildTicks(layout) {
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
  const [ox, oy] = project(layout, 0, 0);
  ticks += `<text x="${ox - 9}" y="${oy + 16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`;
  return ticks;
}

function buildAxes(layout, axisMarkerId) {
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
  out += buildTicks(layout);
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
  // Grille légère activée par défaut dès qu'un repère est affiché (sauf
  // désactivation explicite), pour rester lisible sans être surchargée.
  const showGrid = spec.grid === true || (spec.grid !== false && spec.axes);
  if (showGrid) content += buildGrid(layout);
  if (spec.axes) content += buildAxes(layout, axisMarkerId);

  (spec.curves || []).forEach((c) => {
    const pts = c.points.map(([x, y]) => project(layout, x, y).join(",")).join(" ");
    content += `<polyline points="${pts}" class="geom-curve${c.dashed ? " geom-curve--dashed" : ""}" fill="none"/>`;
  });

  (spec.polygons || []).forEach((poly) => {
    const pts = poly.points.map((ref) => project(layout, ...resolvePoint(spec, ref)).join(",")).join(" ");
    content += `<polygon points="${pts}" class="geom-polygon"/>`;
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
    content += `<path d="M ${pcx} ${pcy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z" class="geom-angle-arc"/>`;
    if (a.label) {
      const midRad = ((a.startDeg + a.endDeg) / 2) * (Math.PI / 180);
      const lx = pcx + (r + 12) * Math.cos(midRad);
      const ly = pcy - (r + 12) * Math.sin(midRad);
      content += `<text x="${lx}" y="${ly}" class="geom-label">${a.label}</text>`;
    }
  });

  (spec.segments || []).forEach((s) => {
    const [x1, y1] = project(layout, ...resolvePoint(spec, s.from));
    const [x2, y2] = project(layout, ...resolvePoint(spec, s.to));
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-segment${s.dashed ? " geom-segment--dashed" : ""}"/>`;
  });

  (spec.vectors || []).forEach((v) => {
    const [x1, y1] = project(layout, ...resolvePoint(spec, v.from));
    const [x2, y2] = project(layout, ...resolvePoint(spec, v.to));
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-vector" marker-end="url(#${vectorMarkerId})"/>`;
    if (v.label) {
      const lx = (x1 + x2) / 2 + 8;
      const ly = (y1 + y2) / 2 - 8;
      content += `<text x="${lx}" y="${ly}" class="geom-label geom-label--vector">${v.label}</text>`;
    }
  });

  // Points remarquables : coordonnées affichées sous le label si demandées
  // (spec.showCoords ou p.showCoords) pour rendre le repère auto-suffisant.
  (spec.points || []).forEach((p) => {
    const [px, py] = project(layout, p.x, p.y);
    content += `<circle cx="${px}" cy="${py}" r="4.5" class="geom-point"/>`;
    if (p.label) content += `<text x="${px + 9}" y="${py - 9}" class="geom-label">${p.label}</text>`;
    if (p.showCoords || spec.showCoords) {
      content += `<text x="${px + 9}" y="${py - 9 + 15}" class="geom-label geom-coord-label">(${p.x} ; ${p.y})</text>`;
    }
  });

  (spec.texts || []).forEach((t) => {
    const [x, y] = project(layout, t.x, t.y);
    content += `<text x="${x}" y="${y}" class="geom-label">${t.label}</text>`;
  });

  (spec.angles || []).forEach((a) => {
    const [cx, cy] = project(layout, ...resolvePoint(spec, a.vertex));
    content += `<circle cx="${cx}" cy="${cy}" r="2.5" class="geom-point"/>`;
    if (a.label) content += `<text x="${cx + 10}" y="${cy + 4}" class="geom-label">${a.label}</text>`;
  });

  return `
    <svg viewBox="0 0 ${layout.width} ${layout.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${spec.alt || "Figure géométrique"}">
      <defs>
        ${buildArrowMarker(axisMarkerId, "geom-arrow-head geom-arrow-head--axis")}
        ${buildArrowMarker(vectorMarkerId, "geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${content}
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
