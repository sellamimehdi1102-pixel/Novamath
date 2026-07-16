// ── Générateur de figures géométriques SVG, déclaratif et léger ────────────
// Utilisé par cours.js pour les notions de géométrie (chapitres 4, 5, 6...).
// Un "spec" décrit une figure en coordonnées mathématiques (repère standard,
// y vers le haut) ; ce module convertit en SVG (pixels, y vers le bas) et
// respecte le thème (currentColor + var(--accent)) pour rester cohérent avec
// l'apparence choisie par l'utilisateur (thème, accent, transparence).
const PADDING = 28;
const SIZE = 260;

function project(spec, x, y) {
  const [xmin, ymin, w, h] = spec.viewBox;
  const scale = (SIZE - 2 * PADDING) / Math.max(w, h);
  const px = PADDING + (x - xmin) * scale;
  const py = SIZE - PADDING - (y - ymin) * scale;
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

function buildGrid(spec) {
  const [xmin, ymin, w, h] = spec.viewBox;
  let lines = "";
  for (let x = Math.ceil(xmin); x <= xmin + w; x++) {
    const [x1, y1] = project(spec, x, ymin);
    const [x2, y2] = project(spec, x, ymin + h);
    lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-grid-line"/>`;
  }
  for (let y = Math.ceil(ymin); y <= ymin + h; y++) {
    const [x1, y1] = project(spec, xmin, y);
    const [x2, y2] = project(spec, xmin + w, y);
    lines += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-grid-line"/>`;
  }
  return lines;
}

function buildAxes(spec) {
  const [xmin, ymin, w, h] = spec.viewBox;
  if (xmin > 0 || xmin + w < 0 || ymin > 0 || ymin + h < 0) return "";
  const [xA1, yA1] = project(spec, xmin, 0);
  const [xA2, yA2] = project(spec, xmin + w, 0);
  const [yA1x, yA1y] = project(spec, 0, ymin);
  const [yA2x, yA2y] = project(spec, 0, ymin + h);
  return `
    <line x1="${xA1}" y1="${yA1}" x2="${xA2}" y2="${yA2}" class="geom-axis"/>
    <line x1="${yA1x}" y1="${yA1y}" x2="${yA2x}" y2="${yA2y}" class="geom-axis"/>
  `;
}

function buildArrowMarker(id) {
  return `<marker id="${id}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="geom-arrow-head"/>
  </marker>`;
}

export function renderFigure(spec) {
  const markerId = `geom-arrow-${Math.random().toString(36).slice(2, 8)}`;
  let content = "";
  if (spec.grid) content += buildGrid(spec);
  if (spec.axes) content += buildAxes(spec);

  (spec.polygons || []).forEach((poly) => {
    const pts = poly.points.map((ref) => project(spec, ...resolvePoint(spec, ref)).join(",")).join(" ");
    content += `<polygon points="${pts}" class="geom-polygon"/>`;
  });

  (spec.circles || []).forEach((c) => {
    const [cx, cy] = project(spec, ...resolvePoint(spec, c.center));
    const scale = (SIZE - 2 * PADDING) / Math.max(spec.viewBox[2], spec.viewBox[3]);
    content += `<circle cx="${cx}" cy="${cy}" r="${c.radius * scale}" class="geom-circle"/>`;
  });

  (spec.segments || []).forEach((s) => {
    const [x1, y1] = project(spec, ...resolvePoint(spec, s.from));
    const [x2, y2] = project(spec, ...resolvePoint(spec, s.to));
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-segment${s.dashed ? " geom-segment--dashed" : ""}"/>`;
  });

  (spec.vectors || []).forEach((v) => {
    const [x1, y1] = project(spec, ...resolvePoint(spec, v.from));
    const [x2, y2] = project(spec, ...resolvePoint(spec, v.to));
    content += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="geom-vector" marker-end="url(#${markerId})"/>`;
    if (v.label) {
      const lx = (x1 + x2) / 2 + 8;
      const ly = (y1 + y2) / 2 - 8;
      content += `<text x="${lx}" y="${ly}" class="geom-label geom-label--vector">${v.label}</text>`;
    }
  });

  (spec.points || []).forEach((p) => {
    const [px, py] = project(spec, p.x, p.y);
    content += `<circle cx="${px}" cy="${py}" r="3.5" class="geom-point"/>`;
    if (p.label) content += `<text x="${px + 8}" y="${py - 8}" class="geom-label">${p.label}</text>`;
  });

  (spec.angles || []).forEach((a) => {
    const [cx, cy] = project(spec, ...resolvePoint(spec, a.vertex));
    content += `<circle cx="${cx}" cy="${cy}" r="2.5" class="geom-point"/>`;
    if (a.label) content += `<text x="${cx + 10}" y="${cy + 4}" class="geom-label">${a.label}</text>`;
  });

  return `
    <svg viewBox="0 0 ${SIZE} ${SIZE}" class="geom-figure" role="img" aria-label="${spec.alt || "Figure géométrique"}">
      <defs>${buildArrowMarker(markerId)}</defs>
      ${content}
    </svg>
  `;
}
