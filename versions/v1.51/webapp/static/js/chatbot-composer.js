// ── Composeur de message du chatbot (contenteditable) ──────────────────────
// Remplace l'ancien <textarea> : un <div contenteditable> permet d'insérer de
// vrais badges de mention (span non-éditable), supprimables par un simple
// Backspace comme dans Slack/Discord/Notion — impossible avec un <textarea>
// qui ne peut contenir que du texte brut. Ce module isole toute la
// sérialisation DOM <-> texte/mentions, chatbot.js et chatbot-mentions.js ne
// manipulent jamais directement les nœuds internes.

/** Sérialise le contenu en texte brut envoyé au backend : une mention devient
 * "@Label" (lisible pour l'élève et pour l'IA), un <br>/bloc devient "\n". */
export function getText(el) {
  let out = "";
  const walk = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      out += node.data;
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if (node.classList?.contains("chatbot-mention-chip")) {
      out += `@${node.dataset.label}`;
      return;
    }
    if (node.tagName === "BR") {
      out += "\n";
      return;
    }
    const isBlock = node.tagName === "DIV" || node.tagName === "P";
    if (isBlock && out && !out.endsWith("\n")) out += "\n";
    node.childNodes.forEach(walk);
  };
  el.childNodes.forEach(walk);
  return out;
}

/** Collecte les mentions insérées (badges), dans l'ordre d'apparition. */
export function getMentions(el) {
  return Array.from(el.querySelectorAll(".chatbot-mention-chip")).map((chip) => ({
    type: chip.dataset.type,
    chapter_id: chip.dataset.chapterId || undefined,
    notion_id: chip.dataset.notionId || undefined,
    exercise_id: chip.dataset.exerciseId ? Number(chip.dataset.exerciseId) : undefined,
    label: chip.dataset.label,
  }));
}

export function isEmpty(el) {
  return getText(el).trim().length === 0;
}

export function clear(el) {
  el.innerHTML = "";
}

/** Insère du texte brut à la position du curseur (ou en fin de contenu si le
 * focus n'est pas dans le composeur — cas des pièces jointes). */
export function insertText(el, text) {
  el.focus();
  const sel = window.getSelection();
  let range;
  if (sel && sel.rangeCount && el.contains(sel.anchorNode)) {
    range = sel.getRangeAt(0);
  } else {
    range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
  }
  range.deleteContents();
  const node = document.createTextNode(text);
  range.insertNode(node);
  range.setStartAfter(node);
  range.setEndAfter(node);
  sel.removeAllRanges();
  sel.addRange(range);
}

export function prependParagraphIfNotEmpty(el) {
  if (!isEmpty(el)) insertText(el, "\n\n");
}

/** Construit un badge de mention (non-éditable) — supprimable en un seul
 * Backspace par le navigateur (comportement natif des nœuds atomiques
 * contenteditable="false"). */
export function createMentionChip(mention) {
  const chip = document.createElement("span");
  chip.className = "chatbot-mention-chip";
  chip.contentEditable = "false";
  chip.dataset.type = mention.type;
  if (mention.chapter_id) chip.dataset.chapterId = mention.chapter_id;
  if (mention.notion_id) chip.dataset.notionId = mention.notion_id;
  if (mention.exercise_id !== undefined) chip.dataset.exerciseId = String(mention.exercise_id);
  chip.dataset.label = mention.label;
  chip.textContent = `@${mention.label}`;
  return chip;
}

/** Remplace le texte [start, end) du nœud texte `node` par `nodeToInsert`
 * (un badge) suivi d'un espace insécable-friendly, et replace le curseur
 * juste après. Utilisé par chatbot-mentions.js pour transformer "@requête"
 * en badge une fois une ressource choisie. */
export function replaceRangeWithNode(node, start, end, nodeToInsert) {
  const after = node.data.slice(end);
  node.data = node.data.slice(0, start);
  const space = document.createTextNode(" " + after);
  node.parentNode.insertBefore(nodeToInsert, node.nextSibling);
  node.parentNode.insertBefore(space, nodeToInsert.nextSibling);

  const range = document.createRange();
  range.setStart(space, 1);
  range.setEnd(space, 1);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}

/** Supprime le texte [start, end) du nœud texte `node` et replace le curseur
 * à `start` — utilisé quand une catégorie de navigation/action est choisie
 * (pas de badge à insérer). */
export function removeRange(node, start, end) {
  node.data = node.data.slice(0, start) + node.data.slice(end);
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, start);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}
