// ── landing.js : FAQ accessible + menus « Classes » + contenu statique ─────
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

vi.mock("../theme.js", () => ({ bindThemeToggle: vi.fn() }));

const CLASS_HREFS = [
  "/choisir-classe.html?classe=quatrieme",
  "/choisir-classe.html?classe=troisieme",
  "/choisir-classe.html?classe=seconde",
  "/choisir-classe.html?classe=premiere",
  "/choisir-classe.html?classe=premiere_specifique",
];

async function mountLanding() {
  document.body.innerHTML = loadPageBody("index.html");
  vi.resetModules();
  await import("../landing.js");
  await flushPromises();
}

function key(el, k) {
  el.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true }));
}

describe("index.html — structure de la page d'accueil", () => {
  beforeEach(async () => {
    await mountLanding();
  });

  it("un seul h1, au texte exact validé", () => {
    const h1s = document.querySelectorAll("h1");
    expect(h1s).toHaveLength(1);
    expect(h1s[0].textContent.replace(/\s+/g, " ").trim()).toBe(
      "En maths, ton point de départ ne définit pas jusqu'où tu peux aller.",
    );
  });

  it("sections dans l'ordre validé, sections redondantes supprimées", () => {
    const ids = [...document.querySelectorAll("body > section[id]")].map((s) => s.id);
    expect(ids.filter((id) => id !== "avis")).toEqual(["avantages", "chiffres", "commencer", "faq"]);
    // Section quantitative juste après les avantages, avant les avis.
    expect(ids.slice(0, 3)).toEqual(["avantages", "chiffres", "avis"]);
    for (const removed of ["classes", "comment-ca-marche", "chatbot-showcase", "fonctionnalites", "tarifs"]) {
      expect(document.getElementById(removed)).toBeNull();
    }
    expect(document.querySelector(".stats-strip")).toBeNull();
    expect(document.getElementById("class-badge-btn")).toBeNull();
  });

  it("cinq cartes d'avantages dont une principale", () => {
    const cards = document.querySelectorAll("#avantages .advantage-card");
    expect(cards).toHaveLength(5);
    expect(cards[0].classList.contains("advantage-card--main")).toBe(true);
  });

  it("aucun lien de navigation interne vers une section absente", () => {
    document.querySelectorAll('a[href^="#"]').forEach((a) => {
      expect(document.getElementById(a.getAttribute("href").slice(1))).not.toBeNull();
    });
  });

  it("cockpit : une seule image accessible, aucun élément interactif à l'intérieur", () => {
    const cockpit = document.querySelector(".cockpit");
    expect(cockpit.getAttribute("role")).toBe("img");
    expect(cockpit.getAttribute("aria-label")).toBeTruthy();
    expect(cockpit.querySelector(".ck-grid").getAttribute("aria-hidden")).toBe("true");
    expect(cockpit.querySelectorAll("a, button, input, select, textarea, [tabindex]")).toHaveLength(0);
  });
});

describe("index.html — section « Les maths, en grand. » (chiffres audités)", () => {
  beforeEach(async () => {
    await mountLanding();
  });

  const clean = (el) => el.textContent.replace(/[\s\u202f\u00a0]+/g, " ").trim();

  it("titre et sous-titre exacts", () => {
    const section = document.getElementById("chiffres");
    expect(clean(section.querySelector("h2"))).toBe("Les maths, en grand.");
    expect(clean(section.querySelector(".section-header p"))).toBe(
      "Des milliers de questions, des centaines de notions et un entraînement adapté à tes acquis.",
    );
  });

  it("quatre statistiques exactes, dans l'ordre", () => {
    const cards = [...document.querySelectorAll("#chiffres .stat-card")].map((c) => [
      clean(c.querySelector(".stat-card-value")),
      clean(c.querySelector(".stat-card-title")),
      clean(c.querySelector(".stat-card-desc")),
    ]);
    expect(cards).toEqual([
      ["22 000+", "Questions", "Pour t’entraîner sur tout le programme"],
      ["200+", "Notions", "Pour cibler précisément tes révisions"],
      ["5", "Parcours scolaires", "De la 4e à la Première"],
      ["5", "Niveaux de difficulté", "Jusqu’à 5 niveaux selon ta classe"],
    ]);
  });

  it("le nombre de questions reste insécable (« 22 000+ » sur une seule ligne)", () => {
    expect(document.querySelector("#chiffres .stat-card-value").textContent).toContain("22 000+");
  });

  it("niveaux : jamais présentés comme exactement cinq pour toutes les classes", () => {
    const text = clean(document.getElementById("chiffres"));
    expect(text).toContain("Jusqu’à 5 niveaux selon ta classe");
    expect(text).not.toMatch(/5 niveaux (pour|dans) (toutes|chaque)/i);
  });
});

describe("landing.js — menus « Classes »", () => {
  beforeEach(async () => {
    await mountLanding();
  });

  it("« Commencer » mène directement à la page de choix de classe (aucun menu)", () => {
    const start = [...document.querySelectorAll(".hero a, .hero button")].filter(
      (el) => el.textContent.trim() === "Commencer",
    );
    expect(start).toHaveLength(1);
    expect(start[0].tagName).toBe("A");
    expect(start[0].getAttribute("href")).toBe("/choisir-classe.html");
    expect(start[0].closest("[data-class-menu]")).toBeNull();
  });

  it("deux menus (navigation « Classes », « Choisir ma classe »), mêmes cinq classes", () => {
    const menus = document.querySelectorAll("[data-class-menu]");
    expect(menus).toHaveLength(2);
    const labels = [...menus].map((m) => m.querySelector(".class-menu-toggle").textContent.trim());
    expect(labels).toEqual(["Classes", "Choisir ma classe"]);
    menus.forEach((menu) => {
      const hrefs = [...menu.querySelectorAll(".class-menu-list a")].map((a) => a.getAttribute("href"));
      expect(hrefs).toEqual(CLASS_HREFS);
    });
  });

  it("fermés par défaut, ouverture/fermeture au clic avec aria-expanded", () => {
    const menu = document.querySelector("[data-class-menu]");
    const toggle = menu.querySelector(".class-menu-toggle");
    const list = menu.querySelector(".class-menu-list");
    expect(list.hidden).toBe(true);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(toggle.getAttribute("aria-controls")).toBe(list.id);
    toggle.click();
    expect(list.hidden).toBe(false);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    toggle.click();
    expect(list.hidden).toBe(true);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("un seul menu ouvert à la fois", () => {
    const [nav, cta] = document.querySelectorAll("[data-class-menu]");
    nav.querySelector(".class-menu-toggle").click();
    cta.querySelector(".class-menu-toggle").click();
    expect(nav.querySelector(".class-menu-list").hidden).toBe(true);
    expect(cta.querySelector(".class-menu-list").hidden).toBe(false);
  });

  it("clavier : flèche bas ouvre et focalise la première classe, Échap referme et rend le focus", () => {
    const menu = document.querySelector("[data-class-menu]");
    const toggle = menu.querySelector(".class-menu-toggle");
    const links = menu.querySelectorAll(".class-menu-list a");
    toggle.focus();
    key(toggle, "ArrowDown");
    expect(menu.querySelector(".class-menu-list").hidden).toBe(false);
    expect(document.activeElement).toBe(links[0]);
    key(links[0], "ArrowDown");
    expect(document.activeElement).toBe(links[1]);
    key(links[1], "End");
    expect(document.activeElement).toBe(links[4]);
    key(links[4], "ArrowDown");
    expect(document.activeElement).toBe(links[0]);
    key(links[0], "Escape");
    expect(menu.querySelector(".class-menu-list").hidden).toBe(true);
    expect(document.activeElement).toBe(toggle);
  });

  it("clic en dehors : le menu se referme", () => {
    const menu = document.querySelector("[data-class-menu]");
    menu.querySelector(".class-menu-toggle").click();
    document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(menu.querySelector(".class-menu-list").hidden).toBe(true);
  });
});

describe("landing.js — FAQ accordéon accessible", () => {
  beforeEach(async () => {
    await mountLanding();
  });

  it("exactement trois questions, fermées par défaut", () => {
    const items = document.querySelectorAll("#faq .faq-item");
    expect(items).toHaveLength(3);
    items.forEach((item) => {
      const q = item.querySelector("button.faq-question");
      expect(q.getAttribute("aria-expanded")).toBe("false");
      expect(document.getElementById(q.getAttribute("aria-controls"))).toBe(item.querySelector(".faq-answer"));
      expect(item.classList.contains("open")).toBe(false);
    });
  });

  it("ouvre un item au clic, un second clic le referme (aria-expanded synchronisé)", () => {
    const item = document.querySelector(".faq-item");
    const q = item.querySelector(".faq-question");
    q.click();
    expect(item.classList.contains("open")).toBe(true);
    expect(q.getAttribute("aria-expanded")).toBe("true");
    q.click();
    expect(item.classList.contains("open")).toBe(false);
    expect(q.getAttribute("aria-expanded")).toBe("false");
  });
});
