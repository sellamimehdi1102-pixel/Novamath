// Chantier Administrateur — clarification de l'onglet Fonctionnalités de la
// fiche Abonnement : le catalogue cosmétique et les fonctionnalités
// réellement appliquées (plan_service.FEATURE_MATRIX) doivent être rendus
// dans deux blocs visuellement distincts, jamais fusionnés — c'était le
// point le plus fragile identifié par l'audit (risque qu'un admin croie que
// modifier le catalogue change le comportement réel du produit).
import { describe, it, expect } from "vitest";
import { renderFeaturesTab } from "../admin-subscription-detail.js";

function sampleData() {
  return {
    advantages: ["Chatbot illimité", "Exercices personnalisés"],
    limits: ["Support standard"],
    quota_daily: { available: true, value: 50 },
    quota_chatbot: { available: true, value: 20 },
    real_features: [
      { key: "chatbot", label: "Chatbot" },
      { key: "chatbot_unlimited", label: "Chatbot illimité" },
    ],
    real_quotas: [
      { key: "chat_messages", label: "Messages chatbot", unlimited: false, limit: 30 },
      { key: "llm_calls", label: "Appels IA", unlimited: true, limit: null },
    ],
    real_note: "\"real_features\"/\"real_quotas\" reflètent ce qui est RÉELLEMENT appliqué aujourd'hui.",
  };
}

describe("admin-subscription-detail.js — renderFeaturesTab (2 blocs distincts)", () => {
  it("rend deux blocs séparés : catalogue (.admin-feature-block--catalog) et réel (.admin-feature-block--real)", () => {
    const wrap = renderFeaturesTab(sampleData());
    const catalogBlock = wrap.querySelector(".admin-feature-block--catalog");
    const realBlock = wrap.querySelector(".admin-feature-block--real");
    expect(catalogBlock).not.toBeNull();
    expect(realBlock).not.toBeNull();
    expect(catalogBlock).not.toBe(realBlock);
  });

  it("le bloc catalogue contient les avantages/limites/quotas catalogue modifiables", () => {
    const wrap = renderFeaturesTab(sampleData());
    const catalogBlock = wrap.querySelector(".admin-feature-block--catalog");
    expect(catalogBlock.textContent).toContain("Catalogue");
    expect(catalogBlock.textContent).toContain("Chatbot illimité");
    expect(catalogBlock.textContent).toContain("Support standard");
  });

  it("le bloc réel contient les fonctionnalités issues de FEATURE_MATRIX et les quotas réels, jamais de formulaire", () => {
    const wrap = renderFeaturesTab(sampleData());
    const realBlock = wrap.querySelector(".admin-feature-block--real");
    expect(realBlock.textContent).toContain("réellement appliquées");
    expect(realBlock.querySelectorAll(".admin-badge").length).toBe(2);
    expect(realBlock.textContent).toContain("Messages chatbot");
    expect(realBlock.querySelector("input")).toBeNull();
    expect(realBlock.querySelector("textarea")).toBeNull();
  });

  it("le bloc catalogue précède le bloc réel dans le DOM (ordre de lecture stable)", () => {
    const wrap = renderFeaturesTab(sampleData());
    const blocks = wrap.querySelectorAll(".admin-feature-block");
    expect(blocks.length).toBe(2);
    expect(blocks[0].classList.contains("admin-feature-block--catalog")).toBe(true);
    expect(blocks[1].classList.contains("admin-feature-block--real")).toBe(true);
  });
});
