// ── Métadonnées des Feature Flags côté frontend ─────────────────────────────
// Miroir volontairement minimal de webapp/plan_service.py (Plan/Feature) : le
// backend reste l'unique source de vérité pour QUI a droit à QUOI (chaque
// route vérifie via @requires_feature, jamais le JS) — ce module ne sert
// qu'à afficher un message cohérent (page "Premium requis", cadenas de la
// sidebar) une fois qu'un refus 403 a déjà été décidé côté serveur.
export const PLAN_LABELS = { free: "Gratuit", premium: "Premium", ultra: "Ultra" };

// Ordre croissant des paliers (miroir de plan_service._PLAN_ORDER) — permet de
// comparer "l'utilisateur a-t-il au moins le plan requis ?" sans jamais
// comparer de chaînes de plan directement dans les modules appelants.
export const PLAN_RANK = { free: 0, premium: 1, ultra: 2 };

export function planMeetsRequirement(currentPlan, requiredPlan) {
  return (PLAN_RANK[currentPlan] ?? 0) >= (PLAN_RANK[requiredPlan] ?? 0);
}

const PLAN_ORDER = ["free", "premium", "ultra"];

// Palier suivant après `currentPlan` (Free -> Premium -> Ultra), en miroir de
// quota_service._next_plan_with_more — utilisé pour la bannière "quota
// dépassé" (voir abonnement.js), où le plan à proposer se déduit du plan
// actuel plutôt que d'une feature précise. Ultra n'a pas de palier suivant :
// renvoie "ultra" (jamais atteint en pratique, un compte Ultra n'épuise
// jamais son quota — voir quota_service.consume).
export function nextPlanAbove(currentPlan) {
  const idx = PLAN_ORDER.indexOf(currentPlan);
  return PLAN_ORDER[Math.min(idx + 1, PLAN_ORDER.length - 1)] || "premium";
}

// feature.value (Python) -> { label, requiredPlan }. requiredPlan est le
// palier le moins élevé qui débloque la feature (voir
// plan_service.minimal_plan_for_feature) — tenu à jour manuellement en
// miroir de plan_service.FEATURE_MATRIX.
export const FEATURE_META = {
  chatbot: { label: "Chatbot IA", requiredPlan: "free" },
  chatbot_unlimited: { label: "Chatbot IA illimité", requiredPlan: "premium" },
  advanced_ai: { label: "IA avancée (analyse de documents joints)", requiredPlan: "ultra" },
  advanced_explanations: { label: "Explications avancées", requiredPlan: "premium" },
  courses: { label: "Cours", requiredPlan: "free" },
  exercises: { label: "Exercices", requiredPlan: "free" },
  custom_exercises: { label: "Exercices sur mesure", requiredPlan: "ultra" },
  statistics: { label: "Statistiques", requiredPlan: "free" },
  history: { label: "Historique", requiredPlan: "free" },
  goals: { label: "Objectifs quotidiens", requiredPlan: "free" },
  export: { label: "Export des données", requiredPlan: "free" },
  profile_analytics: { label: "Statistiques avancées du profil", requiredPlan: "premium" },
  early_access: { label: "Accès anticipé aux nouveautés", requiredPlan: "ultra" },
  priority_queue: { label: "File d'attente prioritaire", requiredPlan: "ultra" },
  priority_support: { label: "Support prioritaire", requiredPlan: "premium" },
  long_responses: { label: "Réponses longues", requiredPlan: "ultra" },
};

// Carte "nom de fichier de page" -> feature.value requise, en miroir de
// server.py::PAGE_FEATURE_REQUIREMENTS (vide aujourd'hui : aucune page
// n'excède le plan Free). Seul point que sidebar.js consulte pour décider
// d'afficher un cadenas sur un lien de nav — ajouter une entrée ici ET côté
// serveur (avec le Feature Python correspondant) suffit à verrouiller une
// future page, sans toucher à sidebar.js.
export const PAGE_FEATURE_REQUIREMENTS = {};

export function featureLabel(featureValue) {
  return FEATURE_META[featureValue]?.label || "Cette fonctionnalité";
}

export function requiredPlanFor(featureValue) {
  return FEATURE_META[featureValue]?.requiredPlan || "premium";
}
