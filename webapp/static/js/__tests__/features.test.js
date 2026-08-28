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
  hasFeature,
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

// Chantier 8 : hasFeature() doit devenir la SEULE façon de décider un accès
// granulaire côté frontend — priorité absolue à user.features (calculé côté
// serveur par plan_service.has_feature(), donc déjà Owner-aware), jamais un
// recalcul local sauf en repli explicite de compatibilité.
describe("features.js — hasFeature", () => {
  it("utilise user.features en priorité, même si ça contredit le plan affiché", () => {
    // Cas volontairement incohérent (ne devrait jamais arriver en pratique)
    // pour prouver que features.js ne recalcule RIEN localement dès que
    // user.features est présent : il fait une confiance absolue au backend.
    const user = { plan: "free", features: { advanced_ai: true } };
    expect(hasFeature(user, "advanced_ai")).toBe(true);
  });

  it("renvoie false si la clé existe et vaut false, sans repli local", () => {
    const user = { plan: "ultra", features: { advanced_ai: false } };
    expect(hasFeature(user, "advanced_ai")).toBe(false);
  });

  it("reflète le plan effectif d'un Owner en mode test (features déjà Owner-aware côté backend)", () => {
    // Simule /api/auth/me pour un Owner dont le plan réel est free mais qui
    // teste "premium" : le backend calcule déjà `features` via effective_plan,
    // donc ce module n'a besoin d'aucune logique Owner de son côté.
    const ownerTestingPremium = { plan: "free", is_owner: true, features: { chatbot_unlimited: true, advanced_ai: false } };
    expect(hasFeature(ownerTestingPremium, "chatbot_unlimited")).toBe(true);
    expect(hasFeature(ownerTestingPremium, "advanced_ai")).toBe(false);
  });

  it("repli sur planMeetsRequirement/requiredPlanFor si user.features est absent (compatibilité)", () => {
    const legacyUser = { plan: "premium" };
    expect(hasFeature(legacyUser, "advanced_explanations")).toBe(true); // requiert premium
    expect(hasFeature(legacyUser, "advanced_ai")).toBe(false); // requiert ultra
  });

  it("repli si user est absent (invité)", () => {
    expect(hasFeature(undefined, "chatbot")).toBe(true); // chatbot requiert free
    expect(hasFeature(undefined, "advanced_ai")).toBe(false);
  });

  // Chantier 10 : une feature inconnue ne doit jamais accorder d'accès à un
  // compte Free (requiredPlanFor() retombe sur "premium", jamais "free" —
  // voir son propre test ci-dessus). Premium/Ultra passent ce repli local
  // (rang >= premium) : décision purement cosmétique côté frontend, sans
  // conséquence réelle puisque la route reste de toute façon protégée côté
  // serveur par @requires_feature sur la VRAIE Feature — jamais sur une
  // chaîne arbitraire (voir plan_service.has_feature(), toujours False pour
  // une valeur inconnue quel que soit le plan, y compris Ultra).
  it("feature inconnue : jamais accordée à Free via le repli local", () => {
    expect(hasFeature({ plan: "free" }, "feature_qui_n_existe_pas")).toBe(false);
  });

  it("feature inconnue : user.features fait toujours foi en priorité, même absente de FEATURE_META", () => {
    const user = { plan: "free", features: { feature_qui_n_existe_pas: true } };
    expect(hasFeature(user, "feature_qui_n_existe_pas")).toBe(true);
  });
});
