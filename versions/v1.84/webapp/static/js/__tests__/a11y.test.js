// ── Accessibilité : axe-core (outil standard) sur les composants générés
// dynamiquement en JS — boutons, aria-label, focus, navigation clavier.
// color-contrast/CSS layout sont désactivés : jsdom ne charge aucune feuille
// de style réelle (les couleurs ne sont jamais résolues), ce qui produirait
// uniquement de faux positifs sans rapport avec le code testé ici.
// Ni curriculumSelector.js (renderCurriculumCard) ni popup.js n'effectuent le
// moindre appel réseau : aucun mock nécessaire ici (voir a11y-sidebar.test.js
// pour la sidebar, qui elle en a besoin — fichier séparé pour ne jamais avoir
// à mocker api.js/curriculumSelector.js dans CE fichier-ci).
import { describe, it, expect } from "vitest";
import axe from "axe-core";
import { renderCurriculumCard } from "../curriculumSelector.js";
import { openPopup, openPromptPopup } from "../popup.js";

const AXE_OPTIONS = {
  rules: {
    "color-contrast": { enabled: false },
    "landmark-one-main": { enabled: false },
    region: { enabled: false },
  },
};

async function runAxe(target = document) {
  const results = await axe.run(target === document ? document.body : target, AXE_OPTIONS);
  return results.violations;
}

describe("a11y — carte de cursus (curriculumSelector.js)", () => {
  it("ne produit aucune violation axe-core", async () => {
    const card = renderCurriculumCard({
      classLevel: "seconde", label: "Seconde", totalExercises: 100, chapters: 12, notions: 40,
    });
    document.body.appendChild(card);
    const violations = await runAxe();
    expect(violations).toEqual([]);
  });

  it("porte un aria-label descriptif (jamais seulement une icône décorative)", () => {
    const card = renderCurriculumCard({ classLevel: "seconde", label: "Seconde", totalExercises: 1, chapters: 1, notions: 1 });
    expect(card.getAttribute("aria-label")).toContain("Seconde");
    expect(card.querySelector(".cursus-card-icon").getAttribute("aria-hidden")).toBe("true");
  });

  it("le CTA est un vrai <button type=button> (focusable/activable au clavier)", () => {
    const card = renderCurriculumCard({ classLevel: "seconde", label: "Seconde", totalExercises: 1, chapters: 1, notions: 1 });
    const cta = card.querySelector(".cursus-card-cta");
    expect(cta.tagName).toBe("BUTTON");
    expect(cta.getAttribute("type")).toBe("button");
    expect(cta.tabIndex).not.toBe(-1);
  });
});

describe("a11y — popup.js (dialog, focus, clavier)", () => {
  it("pose role=dialog et aria-modal=true", () => {
    const { el } = openPopup({ title: "Titre", bodyHtml: "<p>x</p>" });
    const card = el.querySelector(".popup-card");
    expect(card.getAttribute("role")).toBe("dialog");
    expect(card.getAttribute("aria-modal")).toBe("true");
  });

  it("le bouton de fermeture a un aria-label explicite (pas seulement une icône)", () => {
    const { el } = openPopup({ title: "Titre" });
    expect(el.querySelector(".popup-close").getAttribute("aria-label")).toBe("Fermer");
  });

  it("openPromptPopup déplace le focus sur le champ de saisie", async () => {
    openPromptPopup({ title: "Renommer", label: "Nom" });
    // requestAnimationFrame réel (voir popup.js) — un court délai réel est
    // plus robuste ici que des fake timers, dont la couverture de rAF varie
    // selon les versions de Vitest/@sinonjs/fake-timers.
    await new Promise((r) => setTimeout(r, 50));
    expect(document.activeElement.id).toBe("popup-prompt-input");
  });

  it("ne produit aucune violation axe-core sur un popup avec titre + champ", async () => {
    openPromptPopup({ title: "Renommer la conversation", label: "Nouveau titre" });
    const violations = await runAxe();
    expect(violations).toEqual([]);
  });
});
