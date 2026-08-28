// ── features.js : miroir frontend de plan_service.py (Plan/Feature) ────────
import { describe, it, expect } from "vitest";
import {
  PLAN_LABELS,
  PLAN_RANK,
  planMeetsRequirement,
  nextPlanAbove,
  FEATURE_META,
  featureLabel,
  requiredPlanFor,
} from "../features.js";

describe("features.js — PLAN_RANK / planMeetsRequirement", () => {
  it("ordonne free < premium < ultra", () => {
    expect(PLAN_RANK.free).toBeLessThan(PLAN_RANK.premium);
    expect(PLAN_RANK.premium).toBeLessThan(PLAN_RANK.ultra);
  });

  it("un plan ultra satisfait une exigence premium", () => {
    expect(planMeetsRequirement("ultra", "premium")).toBe(true);
  });

  it("un plan free ne satisfait pas une exigence premium", () => {
    expect(planMeetsRequirement("free", "premium")).toBe(false);
  });

  it("un plan satisfait toujours une exigence de même niveau", () => {
    expect(planMeetsRequirement("premium", "premium")).toBe(true);
  });

  it("traite un plan inconnu comme free (rang 0)", () => {
    expect(planMeetsRequirement("inconnu", "free")).toBe(true);
    expect(planMeetsRequirement("inconnu", "premium")).toBe(false);
  });
});

describe("features.js — nextPlanAbove", () => {
  it("free -> premium", () => {
    expect(nextPlanAbove("free")).toBe("premium");
  });
  it("premium -> ultra", () => {
    expect(nextPlanAbove("premium")).toBe("ultra");
  });
  it("ultra reste ultra (aucun palier supérieur)", () => {
    expect(nextPlanAbove("ultra")).toBe("ultra");
  });
  it("un plan inconnu retombe sur 'free' (indexOf=-1, palier suivant=index 0)", () => {
    expect(nextPlanAbove("inconnu")).toBe("free");
  });
});

describe("features.js — featureLabel / requiredPlanFor", () => {
  it("renvoie le libellé français pour une feature connue", () => {
    expect(featureLabel("chatbot_unlimited")).toBe("Chatbot illimité");
  });

  it("renvoie un libellé générique pour une feature inconnue", () => {
    expect(featureLabel("feature_qui_n_existe_pas")).toBe("Cette fonctionnalité");
  });

  it("renvoie le plan minimal requis pour chaque feature connue", () => {
    expect(requiredPlanFor("chatbot")).toBe("free");
    expect(requiredPlanFor("advanced_ai")).toBe("ultra");
    expect(requiredPlanFor("priority_support")).toBe("premium");
  });

  it("retombe sur 'premium' pour une feature inconnue", () => {
    expect(requiredPlanFor("inconnue")).toBe("premium");
  });

  it("chaque entrée de FEATURE_META a un plan requis valide", () => {
    const validPlans = new Set(["free", "premium", "ultra"]);
    Object.values(FEATURE_META).forEach((meta) => {
      expect(validPlans.has(meta.requiredPlan)).toBe(true);
      expect(typeof meta.label).toBe("string");
      expect(meta.label.length).toBeGreaterThan(0);
    });
  });
});

describe("features.js — PLAN_LABELS", () => {
  it("couvre les 3 paliers", () => {
    expect(PLAN_LABELS).toEqual({ free: "Gratuit", premium: "Premium", ultra: "Ultra" });
  });
});
