// ── Export PDF premium du rapport de progression NovaMath ───────────────────
// jsPDF est chargé à la demande (jamais au chargement de page) via un
// <script> injecté au clic — voir loadJsPDF(). Le PDF est volontairement en
// thème clair fixe (fond blanc, texte noir) même si le site est en mode
// sombre, pour rester imprimable et professionnel (voir buildHeader/PALETTE).
// Chaque section est une petite fonction pure (doc, ctx, y) -> nouveau y, qui
// gère elle-même son saut de page — permet d'ajouter facilement une section
// supplémentaire plus tard (QR code, certificat, rapport enseignant) sans
// toucher aux sections existantes.
import { api } from "./api.js";
import { getSettings } from "./settingsManager.js";
import {
  getState, masteryByChapter, coverageByChapter, masteryByNotion,
  levelFromXp, accuracyOutOf20, computeStreak,
} from "./store.js";

const JSPDF_CDN = "https://cdn.jsdelivr.net/npm/jspdf@2.5.2/dist/jspdf.umd.min.js";

function loadJsPDF() {
  if (window.jspdf) return Promise.resolve(window.jspdf);
  return new Promise((resolve, reject) => {
    const existing = document.getElementById("jspdf-cdn-script");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.jspdf));
      existing.addEventListener("error", reject);
      return;
    }
    const s = document.createElement("script");
    s.id = "jspdf-cdn-script";
    s.src = JSPDF_CDN;
    s.onload = () => resolve(window.jspdf);
    s.onerror = () => reject(new Error("Impossible de charger la librairie PDF."));
    document.head.appendChild(s);
  });
}

const PAGE = { w: 595.28, h: 841.89, margin: 40 }; // A4 en points
const PALETTE = {
  text: "#14141a",
  muted: "#62636f",
  faint: "#9798a3",
  border: "#e4e4ec",
  surface: "#f7f7fb",
};

function chapterLabel(id) {
  return String(id || "?").replace(/^Chapitre_?/i, "Chapitre ");
}
function formatDurationShort(seconds) {
  const s = seconds || 0;
  if (s < 60) return `${s}s`;
  const h = Math.floor(s / 3600);
  const m = Math.round((s % 3600) / 60);
  return h ? `${h}h${String(m).padStart(2, "0")}` : `${m}min`;
}
function formatDateFR(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  } catch {
    return iso;
  }
}

function drawHeader(doc, ctx) {
  const { margin } = PAGE;
  doc.setFillColor(ctx.accent);
  doc.roundedRect(margin, 28, 34, 34, 8, 8, "F");
  doc.setTextColor("#ffffff");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text("N", margin + 17, 51, { align: "center" });

  doc.setTextColor(PALETTE.text);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text("NovaMath — Rapport de progression", margin + 44, 42);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(PALETTE.muted);
  doc.text(`${ctx.user.pseudo} · @${ctx.user.username}`, margin + 44, 56);

  doc.setFontSize(8.5);
  doc.setTextColor(PALETTE.faint);
  doc.text(`Généré le ${formatDateFR(new Date().toISOString())}`, PAGE.w - margin, 42, { align: "right" });

  doc.setDrawColor(PALETTE.border);
  doc.line(margin, 74, PAGE.w - margin, 74);
  return 92;
}

function drawFooter(doc, pageNum) {
  const { margin } = PAGE;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(PALETTE.faint);
  doc.text("NovaMath — Rapport généré automatiquement", margin, PAGE.h - 24);
  doc.text(`Page ${pageNum}`, PAGE.w - margin, PAGE.h - 24, { align: "right" });
}

/** Vérifie l'espace restant avant d'écrire `needed` points ; saute de page et
 * redessine l'en-tête si nécessaire. Retourne le y courant (inchangé ou reset
 * après saut de page). */
function ensureSpace(doc, ctx, y, needed) {
  if (y + needed <= PAGE.h - 50) return y;
  drawFooter(doc, ctx.pageNum);
  doc.addPage();
  ctx.pageNum += 1;
  return drawHeader(doc, ctx);
}

function sectionTitle(doc, ctx, y, title) {
  y = ensureSpace(doc, ctx, y, 30);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(PALETTE.text);
  doc.text(title, PAGE.margin, y);
  doc.setDrawColor(ctx.accent);
  doc.setLineWidth(1.4);
  doc.line(PAGE.margin, y + 5, PAGE.margin + 26, y + 5);
  doc.setLineWidth(0.5);
  return y + 22;
}

function emptyNotice(doc, y, text) {
  doc.setFont("helvetica", "italic");
  doc.setFontSize(9.5);
  doc.setTextColor(PALETTE.faint);
  doc.text(text, PAGE.margin, y);
  return y + 18;
}

// ── Sections ──────────────────────────────────────────────────────────────

function buildSummarySection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Résumé général");
  const { history } = ctx.state;
  const total = history.length;
  const correct = history.filter((h) => h.correct).length;
  const rate = total ? Math.round((correct / total) * 100) : 0;
  const avgDuration = total ? Math.round(history.reduce((s, h) => s + (h.duration_s || 0), 0) / total) : 0;
  const { level } = levelFromXp(ctx.state.xp);
  const streak = computeStreak(history);
  const bestStreak = ctx.dataSummary?.bestStreak ?? streak;

  const cells = [
    ["Exercices réalisés", String(total)],
    ["Exercices réussis", String(correct)],
    ["Taux de réussite", `${rate}%`],
    ["Temps moyen / exercice", formatDurationShort(avgDuration)],
    ["Niveau estimé", `Niveau ${level}`],
    ["Série actuelle", `${streak} jour(s)`],
    ["Meilleure série", `${bestStreak} jour(s)`],
    ["Accuracy /20", `${accuracyOutOf20(history)}/20`],
  ];

  const colW = (PAGE.w - PAGE.margin * 2 - 24) / 4;
  const rowH = 46;
  cells.forEach(([label, value], i) => {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const x = PAGE.margin + col * (colW + 8);
    const cy = y + row * (rowH + 8);
    doc.setFillColor(PALETTE.surface);
    doc.setDrawColor(PALETTE.border);
    doc.roundedRect(x, cy, colW, rowH, 6, 6, "FD");
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.6);
    doc.setTextColor(PALETTE.muted);
    doc.text(label, x + 10, cy + 16, { maxWidth: colW - 20 });
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.setTextColor(ctx.accent);
    doc.text(value, x + 10, cy + 34);
  });

  return y + Math.ceil(cells.length / 4) * (rowH + 8) + 14;
}

function progressBar(doc, x, y, w, h, rate, accent) {
  doc.setFillColor(PALETTE.border);
  doc.roundedRect(x, y, w, h, h / 2, h / 2, "F");
  const fillW = Math.max(h, w * Math.min(1, Math.max(0, rate)));
  doc.setFillColor(accent);
  doc.roundedRect(x, y, fillW, h, h / 2, h / 2, "F");
}

function buildChapterProgressSection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Progression par chapitre");
  const { history } = ctx.state;
  const mastery = masteryByChapter(history);
  const chapters = Object.keys(mastery).sort();
  if (!chapters.length) return emptyNotice(doc, y, "Pas encore de chapitre travaillé.");

  chapters.forEach((ch) => {
    y = ensureSpace(doc, ctx, y, 26);
    const m = mastery[ch];
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(PALETTE.text);
    doc.text(chapterLabel(ch), PAGE.margin, y + 5, { maxWidth: 160 });
    progressBar(doc, PAGE.margin + 165, y - 2, PAGE.w - PAGE.margin * 2 - 165 - 50, 8, m.rate, ctx.accent);
    doc.setFontSize(8.5);
    doc.setTextColor(PALETTE.muted);
    doc.text(`${Math.round(m.rate * 100)}%`, PAGE.w - PAGE.margin - 4, y + 5, { align: "right" });
    y += 20;
  });
  return y + 10;
}

function buildNotionProgressSection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Progression par notion");
  const { history } = ctx.state;
  const mastery = masteryByNotion(history);
  const entries = Object.entries(mastery).sort((a, b) => a[1].rate - b[1].rate).slice(0, 12);
  if (!entries.length) return emptyNotice(doc, y, "Pas encore de notion travaillée.");

  entries.forEach(([key, v]) => {
    y = ensureSpace(doc, ctx, y, 22);
    const [chapter, notion] = key.split("|");
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.8);
    doc.setTextColor(PALETTE.text);
    doc.text(`${notion || "—"}`, PAGE.margin, y + 4, { maxWidth: 210 });
    doc.setTextColor(PALETTE.faint);
    doc.setFontSize(7.6);
    doc.text(chapterLabel(chapter), PAGE.margin, y + 13);
    progressBar(doc, PAGE.margin + 220, y - 3, PAGE.w - PAGE.margin * 2 - 220 - 50, 7, v.rate, ctx.accent);
    doc.setFontSize(8);
    doc.setTextColor(PALETTE.muted);
    doc.text(`${Math.round(v.rate * 100)}%`, PAGE.w - PAGE.margin - 4, y + 3, { align: "right" });
    y += 20;
  });
  return y + 10;
}

function buildLevelStatsSection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Statistiques par niveau de difficulté");
  const { history } = ctx.state;
  const byDiff = {};
  history.forEach((h) => {
    const d = h.difficulty || 1;
    byDiff[d] = byDiff[d] || { total: 0, correct: 0 };
    byDiff[d].total += 1;
    if (h.correct) byDiff[d].correct += 1;
  });
  const diffs = Object.keys(byDiff).map(Number).sort((a, b) => a - b);
  if (!diffs.length) return emptyNotice(doc, y, "Pas encore de données par niveau.");

  const labels = { 1: "Facile", 2: "Moyen", 3: "Confirmé", 4: "Difficile", 5: "Expert" };
  diffs.forEach((d) => {
    y = ensureSpace(doc, ctx, y, 22);
    const v = byDiff[d];
    const rate = v.total ? v.correct / v.total : 0;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(PALETTE.text);
    doc.text(`${labels[d] || `Niveau ${d}`} (${v.total} ex.)`, PAGE.margin, y + 4);
    progressBar(doc, PAGE.margin + 165, y - 2, PAGE.w - PAGE.margin * 2 - 165 - 50, 8, rate, ctx.accent);
    doc.setFontSize(8.5);
    doc.setTextColor(PALETTE.muted);
    doc.text(`${Math.round(rate * 100)}%`, PAGE.w - PAGE.margin - 4, y + 4, { align: "right" });
    y += 20;
  });
  return y + 10;
}

function buildDailyGoalSection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Objectif quotidien");
  const goal = Math.max(1, Number(ctx.settings?.learning?.dailyGoalExercises) || 10);
  const today = new Date().toISOString().slice(0, 10);
  const done = ctx.state.history.filter((h) => h.date === today).length;
  const rate = Math.min(1, done / goal);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(PALETTE.text);
  doc.text(`${done} / ${goal} exercices réalisés aujourd'hui`, PAGE.margin, y + 4);
  progressBar(doc, PAGE.margin + 220, y - 2, PAGE.w - PAGE.margin * 2 - 220 - 50, 9, rate, ctx.accent);
  doc.setFontSize(8.5);
  doc.setTextColor(PALETTE.muted);
  doc.text(`${Math.round(rate * 100)}%`, PAGE.w - PAGE.margin - 4, y + 4, { align: "right" });
  return y + 30;
}

function buildRecentHistorySection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Historique récent");
  const recent = ctx.state.history.slice(-12).reverse();
  if (!recent.length) return emptyNotice(doc, y, "Aucun exercice réalisé pour l'instant.");

  recent.forEach((h) => {
    y = ensureSpace(doc, ctx, y, 16);
    drawVerdictMark(doc, PAGE.margin + 4, y - 3, h.correct);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.3);
    doc.setTextColor(PALETTE.text);
    doc.text(`${chapterLabel(h.chapter)} · ${h.notion || "—"}`, PAGE.margin + 16, y, { maxWidth: 340 });
    doc.setTextColor(PALETTE.faint);
    doc.text(formatDateFR(h.date), PAGE.w - PAGE.margin, y, { align: "right" });
    y += 15;
  });
  return y + 10;
}

/** Dessine un petit indicateur vectoriel (coche ou croix dans un cercle coloré)
 * — jamais de glyphe Unicode ✓/✕ (dépend de la police, rendu incohérent). */
function drawVerdictMark(doc, cx, cy, correct) {
  const r = 3.2;
  doc.setFillColor(correct ? "#dcfce7" : "#fee2e2");
  doc.circle(cx, cy, r, "F");
  doc.setDrawColor(correct ? "#16a34a" : "#dc2626");
  doc.setLineWidth(0.6);
  if (correct) {
    doc.line(cx - 1.5, cy, cx - 0.3, cy + 1.3);
    doc.line(cx - 0.3, cy + 1.3, cx + 1.6, cy - 1.3);
  } else {
    doc.line(cx - 1.3, cy - 1.3, cx + 1.3, cy + 1.3);
    doc.line(cx - 1.3, cy + 1.3, cx + 1.3, cy - 1.3);
  }
}

function buildAdviceSection(doc, ctx, y) {
  y = sectionTitle(doc, ctx, y, "Conseils personnalisés");
  const mastery = masteryByChapter(ctx.state.history);
  const weakest = Object.entries(mastery).sort((a, b) => a[1].rate - b[1].rate)[0];
  const advices = [];
  if (weakest && weakest[1].total >= 3) {
    advices.push(`Concentre-toi sur ${chapterLabel(weakest[0])} (${Math.round(weakest[1].rate * 100)}% de réussite) pour progresser rapidement.`);
  }
  const streak = computeStreak(ctx.state.history);
  advices.push(streak > 0
    ? `Belle régularité : ${streak} jour(s) de série en cours — continue sur cette lancée !`
    : "Reprends une série aujourd'hui pour relancer ta série de jours actifs.");
  advices.push("La révision espacée (Paramètres → Apprentissage) aide à mémoriser durablement les notions déjà vues.");

  advices.forEach((text) => {
    y = ensureSpace(doc, ctx, y, 18);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    doc.setTextColor(PALETTE.text);
    const lines = doc.splitTextToSize(`•  ${text}`, PAGE.w - PAGE.margin * 2);
    doc.text(lines, PAGE.margin, y);
    y += lines.length * 13 + 4;
  });
  return y + 6;
}

// ── Orchestration ────────────────────────────────────────────────────────

export async function exportProgressPdf() {
  const jspdfLib = await loadJsPDF();
  const { jsPDF } = jspdfLib;
  const doc = new jsPDF({ unit: "pt", format: "a4", compress: true });

  const { user } = await api.me();
  const dataSummary = await api.getDataSummary().catch(() => null);
  const accent = getComputedStyle(document.documentElement).getPropertyValue("--brand-indigo").trim() || "#6366f1";

  const ctx = {
    user,
    dataSummary,
    settings: getSettings(),
    state: getState(),
    accent,
    pageNum: 1,
  };

  let y = drawHeader(doc, ctx);
  y = buildSummarySection(doc, ctx, y);
  y = buildDailyGoalSection(doc, ctx, y);
  y = buildChapterProgressSection(doc, ctx, y);
  y = buildNotionProgressSection(doc, ctx, y);
  y = buildLevelStatsSection(doc, ctx, y);
  y = buildRecentHistorySection(doc, ctx, y);
  buildAdviceSection(doc, ctx, y);
  drawFooter(doc, ctx.pageNum);

  doc.save(`novamath_rapport_${user.username || user.id}.pdf`);
}
