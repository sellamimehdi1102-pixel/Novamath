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
//
// Chantier "Synchronisation globale des abonnements" (2026-08-27) — audit
// exhaustif de chaque Feature de plan_service.FEATURE_MATRIX (recherche de
// has_feature()/@requires_feature() dans tout server.py + tout le frontend) :
// 5 entrées ci-dessous (sur les 6 initialement identifiées) sont déclarées
// dans FEATURE_MATRIX et présentes ici, mais AUCUNE route backend ne les
// consomme (`@requires_feature(Feature.X)` introuvable pour ces 5 valeurs)
// — donc jamais déclenchées côté client non plus (ce module n'est consulté
// qu'après un refus 403 déjà décidé côté serveur, voir docstring
// ci-dessus). Volontairement CONSERVÉES : les supprimer changerait
// FEATURE_MATRIX/plan_service.py (hors périmètre d'un chantier de
// cohérence marketing) et pourrait affecter un futur chantier qui les
// brancherait réellement. Ne pas les retirer sans re-vérifier ces deux
// fichiers au moment considéré :
//   - profile_analytics (Premium+) — aucune route/vue "statistiques
//     avancées" n'existe ; le Dashboard actuel (dashboard.js) ne
//     différencie que le nombre de séries/suggestions/le bilan par notion
//     (via advanced_explanations, pas cette Feature-ci), jamais via
//     profile_analytics.
//   - early_access (Ultra) — aucun contenu "en accès anticipé" n'existe
//     dans le produit à distribuer.
//   - priority_queue (Ultra) — aucune file d'attente différenciée dans le
//     pipeline chatbot (llm_fallback_service.py ne connaît aucune notion de
//     priorité par plan).
//   - priority_support (Premium+) — aucune logique de priorité dans
//     support_service.py.
//   - long_responses (Ultra) — max_tokens (2500) est une constante globale,
//     jamais différenciée par plan (voir llm_fallback_service.py).
// custom_exercises (Ultra) N'EST PLUS dans cette liste depuis le Chantier
// "Différenciateurs Premium/Ultra" (même jour) : POST /api/practice/generate
// (server.py) la consomme désormais réellement, voir
// exercise_generator/registry.py — hasFeature(user, "custom_exercises")
// reflète donc un vrai accès, pas seulement un libellé.
export const FEATURE_META = {
  chatbot: { label: "Chatbot", requiredPlan: "free" },
  chatbot_unlimited: { label: "Chatbot illimité", requiredPlan: "premium" },
  advanced_ai: { label: "Analyse de documents joints", requiredPlan: "ultra" },
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

// Chantier 8 : décide si `user` a accès à `featureValue`. Source de vérité
// PRIMAIRE = user.features (voir auth.py::_public_user, calculé côté serveur
// via plan_service.has_feature() — donc déjà "Owner-aware" via
// owner_test_plan_service.effective_plan(), sans que ce module ait besoin de
// le savoir). N'utilise le repli local (planMeetsRequirement/requiredPlanFor,
// déjà existants ci-dessus — jamais une nouvelle matrice) que si `user`
// provient d'une réponse qui n'expose pas encore `features` (compatibilité
// descendante), ce qui ne devrait plus arriver une fois /api/auth/me à jour
// partout. Reste un affichage informatif dans les deux cas : la route reste
// de toute façon protégée côté serveur par @requires_feature.
export function hasFeature(user, featureValue) {
  if (user?.features && Object.prototype.hasOwnProperty.call(user.features, featureValue)) {
    return !!user.features[featureValue];
  }
  return planMeetsRequirement(user?.plan || "free", requiredPlanFor(featureValue));
}
