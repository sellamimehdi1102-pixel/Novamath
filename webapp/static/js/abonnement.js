// ── Page Abonnements : 3 cartes (Gratuit/Premium/Ultra) + intégration Stripe
// Checkout ───────────────────────────────────────────────────────────────
// Les boutons Premium/Ultra appellent POST /api/checkout/create-session
// (voir api.checkoutCreateSession, webapp/server.py::api_checkout_create_session)
// puis redirigent immédiatement le navigateur vers l'URL Stripe Checkout
// renvoyée. Après paiement, Stripe ramène l'utilisateur sur /checkout/success
// ou /checkout/cancel (webapp/server.py), qui redirigent à leur tour ici avec
// ?checkout=success|cancel — géré ci-dessous pour afficher un toast et
// rafraîchir l'état "plan actuel" des cartes sans recharger la page.
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { bindLiveTranslations } from "./i18n.js";
import { icon } from "./icons.js";
import { api } from "./api.js";
import { PLAN_LABELS, featureLabel, requiredPlanFor, nextPlanAbove, hasFeature } from "./features.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);

// ── Toast (même pattern que settings.js, dupliqué localement : cette page
// n'ouvre pas le popup Paramètres par défaut, donc pas de #settings-toast
// disponible dans le DOM). ───────────────────────────────────────────────
let toastTimer = null;
function showToast(message, isError = false) {
  const el = $("abonnement-toast");
  if (!el) return;
  clearTimeout(toastTimer);
  el.className = `toast${isError ? " toast--error" : ""}`;
  el.innerHTML = `${icon(isError ? "x" : "check")}<span>${message}</span>`;
  el.hidden = false;
  toastTimer = setTimeout(() => {
    el.classList.add("is-leaving");
    el.addEventListener("animationend", () => { el.hidden = true; }, { once: true });
  }, 3200);
}

// Un compte déjà Premium/Ultra ne "s'abonne" plus depuis les autres cartes :
// il change de plan (voir startChangePlan, POST /api/billing/change-plan),
// jamais un nouveau Checkout — sinon Stripe créerait un second abonnement en
// doublon au lieu de modifier l'existant.
function paintCurrentPlan(plan) {
  const isSubscribed = plan === "premium" || plan === "ultra";
  document.querySelectorAll(".pricing-card").forEach((card) => {
    const cardPlan = card.dataset.plan;
    const btn = card.querySelector("[data-plan-button]");
    const isCurrent = cardPlan === plan;
    card.toggleAttribute("data-plan-current", isCurrent);
    if (!btn) return;
    // Sur une page publique réutilisant ces cartes (landing /index.html), un
    // bouton porte par défaut .js-open-signup (ouvre l'inscription, voir
    // auth.js::wireOpeners) tant qu'aucune session n'est confirmée. Une fois
    // ici, l'utilisateur a une session réelle : ce bouton bascule
    // définitivement sur le comportement Stripe (voir wireButtons), jamais
    // les deux à la fois.
    btn.classList.remove("js-open-signup");
    delete btn.dataset.changePlan;
    if (cardPlan === "free") {
      btn.disabled = true;
      btn.textContent = isCurrent ? "Plan actuel" : "Formule de base";
      return;
    }
    if (isCurrent) {
      btn.disabled = true;
      btn.textContent = "Plan actuel";
    } else if (isSubscribed) {
      btn.disabled = false;
      btn.textContent = `Changer vers ${PLAN_LABELS[cardPlan]}`;
      btn.dataset.changePlan = "true";
    } else {
      btn.disabled = false;
      btn.textContent = `Passer à ${PLAN_LABELS[cardPlan]}`;
    }
  });
}

function setButtonLoading(btn, loading) {
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.classList.add("is-loading");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Redirection…';
  } else {
    btn.classList.remove("is-loading");
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText || btn.textContent;
  }
}

async function startCheckout(plan, btn) {
  setButtonLoading(btn, true);
  try {
    const { checkout_url } = await api.checkoutCreateSession(plan);
    if (!checkout_url) throw new Error("Réponse invalide du serveur de paiement.");
    window.location.href = checkout_url;
  } catch (err) {
    setButtonLoading(btn, false);
    showToast(err.message || "Impossible de démarrer le paiement. Réessaie dans un instant.", true);
  }
}

// Changement de plan d'un abonnement déjà actif (voir paintCurrentPlan) :
// upgrade immédiat ou downgrade à la prochaine période de facturation selon
// le sens du changement, décidé côté serveur (billing_service.change_plan).
// Aucune redirection Stripe ici (contrairement à startCheckout) : le
// changement est appliqué directement sur l'abonnement existant.
async function startChangePlan(plan, btn) {
  setButtonLoading(btn, true);
  try {
    await api.billingChangePlan(plan);
    showToast(`Changement vers ${PLAN_LABELS[plan]} confirmé. Ton nouveau plan sera bientôt actif.`);
    await loadCurrentPlan();
  } catch (err) {
    showToast(err.message || "Impossible de changer de plan. Réessaie dans un instant.", true);
  } finally {
    setButtonLoading(btn, false);
  }
}

// Idempotent (appelée une 2e fois par loadCurrentPlan une fois la session
// confirmée, voir plus bas) et défensive vis-à-vis d'une page publique : un
// bouton encore .js-open-signup n'a pas de session confirmée, on le laisse à
// auth.js plutôt que de le câbler ici — sinon un visiteur non connecté
// déclencherait à la fois l'ouverture du formulaire d'inscription ET un
// appel Stripe voué à échouer (401).
function wireButtons() {
  document.querySelectorAll("[data-plan-button]").forEach((btn) => {
    const plan = btn.dataset.planButton;
    if (plan === "free" || btn.dataset.wired === "true" || btn.classList.contains("js-open-signup")) return;
    btn.dataset.wired = "true";
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      if (btn.dataset.changePlan === "true") {
        startChangePlan(plan, btn);
      } else {
        startCheckout(plan, btn);
      }
    });
  });
}

// ── Carte de statut d'abonnement (Premium/Ultra actif) + Portail client ──
function formatDateFR(unixSeconds) {
  const d = new Date(unixSeconds * 1000);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

const SUBSCRIPTION_STATUS_LABELS = {
  active: "Actif", trialing: "Période d'essai", past_due: "Paiement en retard",
  canceled: "Résilié", unpaid: "Impayé", incomplete: "Incomplet", incomplete_expired: "Expiré",
};

async function openCustomerPortal(btn) {
  setButtonLoading(btn, true);
  try {
    const { portal_url } = await api.billingCustomerPortal();
    if (!portal_url) throw new Error("Réponse invalide du serveur de facturation.");
    window.location.href = portal_url;
  } catch (err) {
    setButtonLoading(btn, false);
    showToast(err.message || "Impossible d'ouvrir le portail client. Réessaie dans un instant.", true);
  }
}

async function loadBillingStatus(plan) {
  const card = $("billing-status-card");
  if (!card) return;
  if (plan !== "premium" && plan !== "ultra") {
    card.hidden = true;
    return;
  }
  try {
    const status = await api.billingStatus();
    $("billing-status-plan").textContent = PLAN_LABELS[status.plan] || status.plan;
    $("billing-status-badge").textContent = SUBSCRIPTION_STATUS_LABELS[status.subscription_status] || "Actif";

    const renewEl = $("billing-status-renew");
    if (status.renew_at && !status.cancel_at) {
      renewEl.textContent = `Renouvellement le ${formatDateFR(status.renew_at)}`;
      renewEl.hidden = false;
    } else {
      renewEl.hidden = true;
    }

    const cancelEl = $("billing-status-cancel");
    if (status.cancel_at) {
      cancelEl.textContent = `Résiliation effective le ${formatDateFR(status.cancel_at)}`;
      cancelEl.hidden = false;
    } else {
      cancelEl.hidden = true;
    }

    card.hidden = !status.customer_portal_available;
  } catch {
    card.hidden = true;
  }
}

// Absent sur une page publique réutilisant ces cartes sans la carte de statut
// d'abonnement (landing /index.html) : ce module reste chargeable partout.
const billingStatusManageBtn = $("billing-status-manage");
if (billingStatusManageBtn) {
  billingStatusManageBtn.addEventListener("click", () => openCustomerPortal(billingStatusManageBtn));
}

// ── Retour depuis Stripe Checkout (/checkout/success ou /checkout/cancel,
// redirigés ici par le serveur avec ?checkout=success|cancel) ───────────
function handleCheckoutReturn() {
  const params = new URLSearchParams(window.location.search);
  const status = params.get("checkout");
  if (!status) return;

  if (status === "success") {
    showToast("Merci ! Ton abonnement est en cours d'activation.");
  } else if (status === "cancel") {
    showToast("Paiement annulé, aucun montant n'a été prélevé.", true);
  }
  // Nettoie l'URL (évite de réafficher le toast à chaque rechargement/retour
  // arrière) sans perdre la position de scroll ni recharger la page.
  params.delete("checkout");
  const clean = window.location.pathname + (params.toString() ? `?${params}` : "");
  window.history.replaceState({}, "", clean);
}

// ── Bannière de mise à niveau ("Fonctionnalité verrouillée" ou "Quota
// dépassé") ─────────────────────────────────────────────────────────────
// Un seul composant visuel pour les deux déclencheurs possibles :
// - ?required=<feature> : server.py::_serve_protected (page premium non
//   accessible) ou un 403 "premium_required" intercepté côté client ;
// - ?reason=quota&quota=<type> : redirection automatique après un 429
//   "quota_exceeded" (voir api.js::handleQuotaExceeded, chatbot.js).
// Jamais d'erreur brute affichée à l'utilisateur, toujours ce message +
// l'offre correspondante — avec proposition d'Ultra plutôt que Premium si le
// palier actuel l'exige (Free -> Premium -> Ultra selon le déclencheur).
function paintUpgradeBanner({ title, desc, requiredPlan }) {
  const banner = $("premium-required-banner");
  if (!banner) return;
  const planLabel = PLAN_LABELS[requiredPlan] || "Premium";

  $("premium-required-title").textContent = title;
  $("premium-required-desc").textContent = desc;

  const benefitsList = $("premium-required-benefits");
  const sourceList = document.querySelector(`.pricing-card[data-plan="${requiredPlan}"] .pricing-features`);
  benefitsList.innerHTML = sourceList ? sourceList.innerHTML : "";

  const cta = $("premium-required-cta");
  cta.textContent = `Passer à ${planLabel}`;
  cta.addEventListener("click", () => startCheckout(requiredPlan, cta));

  banner.hidden = false;

  // "Le plan recommandé doit être automatiquement sélectionné" : la carte
  // ciblée est mise en évidence (halo) ET amenée à l'écran, jamais laissée à
  // l'utilisateur de la retrouver lui-même dans la grille.
  const targetCard = document.querySelector(`.pricing-card[data-plan="${requiredPlan}"]`);
  if (targetCard) {
    targetCard.classList.add("pricing-card--target");
    targetCard.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function showRequiredFeatureBanner(featureValue, user) {
  // Chantier 10 (centralisation du feature gating) : la décision d'accès
  // passe par hasFeature(user, ...) — SEULE source de vérité, déjà
  // Owner-aware (voir features.js/plan_service.has_feature) — jamais un
  // recalcul local à partir du nom du plan réel (user.plan) comme avant. Un
  // Owner en mode test Premium/Ultra a désormais accès à cette page/bannière
  // sans être compté "Free" ici alors que le backend le considère déjà
  // éligible. requiredPlanFor() reste utilisé UNIQUEMENT pour le libellé du
  // plan mis en avant dans la bannière (present à titre indicatif), jamais
  // pour la décision d'accès elle-même.
  if (hasFeature(user, featureValue)) return;
  const requiredPlan = requiredPlanFor(featureValue);
  const planLabel = PLAN_LABELS[requiredPlan] || "Premium";
  paintUpgradeBanner({
    title: `Cette fonctionnalité nécessite ${planLabel}.`,
    desc: `${featureLabel(featureValue)} fait partie de la formule ${planLabel}. Débloque-la dès maintenant :`,
    requiredPlan,
  });
}

// Le palier à proposer vient du serveur (quota_service._next_plan_with_more,
// transporté dans le paramètre required_plan par api.js::handleQuotaExceeded)
// — jamais recalculé ici : Free (15) et Premium (25) ont des limites
// CHAT_MESSAGES distinctes, donc "le palier suivant" est bien Premium pour
// un Free qui épuise ce quota précis, et Ultra pour un Premium qui épuise le
// sien (Premium==Ultra n'est jamais le cas).
// nextPlanAbove(currentPlan) ne reste qu'un repli défensif si le paramètre est
// absent (lien externe/ancien, jamais le cas pour une redirection récente).
// `quotaValue` n'affecte pas le texte générique de la bannière (le message
// reste le même quel que soit le quota concerné, aujourd'hui uniquement
// chat_messages) mais reste transporté pour un futur message spécifique par
// type de quota si besoin.
function showQuotaExceededBanner(currentPlan, requiredPlanParam) {
  const requiredPlan = requiredPlanParam || nextPlanAbove(currentPlan);
  const planLabel = PLAN_LABELS[requiredPlan] || "Premium";
  paintUpgradeBanner({
    title: "Tu as atteint ta limite quotidienne.",
    desc: `Les quotas sont réinitialisés chaque jour. Passe à ${planLabel} pour continuer immédiatement.`,
    requiredPlan,
  });
}

function handleUpgradeParams(user) {
  const params = new URLSearchParams(window.location.search);
  const feature = params.get("required");
  const reason = params.get("reason");
  if (feature) {
    // Décision d'accès (hasFeature) : a besoin de l'objet `user` complet
    // (features Owner-aware), pas seulement du nom du plan réel — voir
    // showRequiredFeatureBanner.
    showRequiredFeatureBanner(feature, user);
  } else if (reason === "quota") {
    // Un quota (CHAT_MESSAGES/LLM_CALLS) n'est jamais Owner-aware côté
    // affichage ici : seul le nom du plan sert à choisir le libellé du
    // palier suivant proposé (voir showQuotaExceededBanner) — jamais une
    // décision d'accès à une Feature, donc le plan réel suffit.
    showQuotaExceededBanner(user.plan || "free", params.get("required_plan"));
  }
}

// ── Compte Owner uniquement (Chantier 6) : les cartes deviennent des
// boutons de simulation locale — /api/owner/test-plan, jamais Stripe. La
// distinction Owner/utilisateur normal est déjà décidée côté serveur
// (owner_service.is_owner_account, voir user.is_owner exposé par
// /api/auth/me dans auth.py::_public_user) : ce module ne fait que suivre
// ce que le serveur a déjà déterminé, jamais une logique de confiance côté
// client — la sécurité réelle reste entièrement dans owner_service.owner_only
// sur la route /api/owner/test-plan elle-même. Réutilise le widget flottant
// owner-test-panel.js pour les réglages avancés (quotas illimités, provider/
// modèle) : celui-ci s'auto-masque sur cette page (voir son propre module)
// pour ne jamais dupliquer visuellement les mêmes boutons FREE/PREMIUM/ULTRA.
function paintOwnerMode(status) {
  const banner = $("owner-mode-banner");
  if (banner) banner.hidden = false;
  const footnote = $("pricing-footnote");
  if (footnote) footnote.hidden = true;

  document.querySelectorAll(".pricing-card").forEach((card) => {
    const cardPlan = card.dataset.plan;
    const btn = card.querySelector("[data-plan-button]");
    const isCurrent = cardPlan === status.effective_plan;
    card.toggleAttribute("data-plan-current", isCurrent);
    if (!btn) return;
    btn.classList.remove("js-open-signup");
    delete btn.dataset.changePlan;
    btn.dataset.ownerTest = "true";
    btn.disabled = isCurrent;
    btn.textContent = isCurrent ? "Mode testé" : `Tester ${PLAN_LABELS[cardPlan]}`;
  });
}

async function startOwnerTest(plan, btn) {
  setButtonLoading(btn, true);
  try {
    // unlimited_quotas: false — sans ce réglage (True par défaut pour le
    // compte Owner, voir owner_test_plan_service.get_unlimited_quotas), les
    // quotas resteraient illimités quel que soit le plan "testé", ce qui
    // viderait "Tester Premium/Ultra" de son intérêt (impossible d'observer
    // les vraies limites 25/20 ou 40/40 depuis cette page). Le widget
    // flottant (autres pages) garde, lui, son propre réglage indépendant —
    // ce chantier ne le modifie pas.
    const status = await api.ownerTestPlanUpdate({ plan, unlimited_quotas: false });
    // setButtonLoading(false) DOIT s'exécuter avant paintOwnerMode : il
    // restaure textContent/disabled depuis l'état "avant clic" (voir
    // btn.dataset.originalText), ce qui écraserait sinon le nouvel état
    // correct ("Mode testé"/disabled=true) que paintOwnerMode vient de poser.
    setButtonLoading(btn, false);
    showToast(`Mode test Owner : ${PLAN_LABELS[plan]} activé — aucun paiement Stripe.`);
    paintOwnerMode(status);
    // Notifie les autres widgets de la page (sidebar/identity.js, carte
    // compte…) — voir le commentaire dans loadCurrentPlan(). `status` n'a pas
    // la forme d'un objet `user` (pas de pseudo/avatar), donc un second appel
    // à api.me() est nécessaire ici plutôt que de dispatcher `status` tel quel.
    try {
      const { user } = await api.me();
      notifyAccountUpdated(user);
    } catch {
      // Best-effort : la carte Owner elle-même est déjà à jour (paintOwnerMode
      // ci-dessus), seule la notification des autres widgets échouerait.
    }
  } catch (err) {
    setButtonLoading(btn, false);
    showToast(err.message || "Impossible de changer le plan de test.", true);
  }
}

// Câblage dédié Owner : contrairement à wireButtons() (utilisateurs normaux),
// le bouton "free" est ici aussi actif (l'Owner doit pouvoir tester FREE).
// Le module appelle wireButtons() de façon inconditionnelle au chargement
// (voir le bas de ce fichier, pour la page landing publique) AVANT de savoir
// si le compte est Owner (api.me() est asynchrone) : sur abonnement.html, ça
// peut donc déjà avoir posé l'écouteur Stripe sur ces mêmes boutons. On clone
// chaque bouton (sans ses écouteurs) avant d'attacher celui d'Owner, pour
// ne JAMAIS avoir deux gestionnaires actifs sur le même clic (Stripe +
// simulation locale déclenchés en même temps serait un vrai bug de sécurité
// perçue, même si /api/checkout/create-session resterait de toute façon
// fonctionnel pour ce compte côté serveur).
function wireOwnerButtons() {
  document.querySelectorAll("[data-plan-button]").forEach((btn) => {
    const clean = btn.cloneNode(true);
    btn.replaceWith(clean);
    delete clean.dataset.wired;
    clean.dataset.ownerTest = "true";
    const plan = clean.dataset.planButton;
    clean.addEventListener("click", () => {
      if (clean.disabled) return;
      startOwnerTest(plan, clean);
    });
  });
}

// Notifie les autres widgets de la page (sidebar/identity.js, carte compte du
// dashboard, page profil) qu'un plan à jour est disponible — même événement
// que settings.js après une modification de profil. Sans ça,
// startChangePlan()/startOwnerTest() changent le plan en place (sans
// rechargement de page) et la sidebar, peinte une seule fois au chargement
// initial, continue d'afficher l'ancien plan indéfiniment.
function notifyAccountUpdated(user) {
  window.dispatchEvent(new CustomEvent("novamath:account-updated", { detail: user }));
}

async function loadCurrentPlan() {
  try {
    const { user } = await api.me();
    notifyAccountUpdated(user);

    if (user.is_owner) {
      try {
        const status = await api.ownerTestPlanStatus();
        paintOwnerMode(status);
        wireOwnerButtons();
        // Statut de facturation basé sur le VRAI plan (toujours "free" pour
        // l'Owner, voir owner_test_plan_service.py) : la carte Stripe reste
        // masquée, jamais un abonnement Stripe fictif affiché pour un plan
        // de test simulé.
        loadBillingStatus(user.plan || "free");
        return;
      } catch {
        // /api/owner/test-plan a renvoyé 404 (NOVAMATH_OWNER_USER_ID mal
        // configuré au moment de l'appel) : repli sur le parcours normal
        // ci-dessous, jamais un panneau Owner à moitié affiché.
      }
    }

    const plan = user.plan || "free";
    paintCurrentPlan(plan);
    handleUpgradeParams(user);
    loadBillingStatus(plan);
    // Re-câble les boutons devenus éligibles (paintCurrentPlan vient de leur
    // retirer .js-open-signup) : no-op sur abonnement.html (déjà câblés plus
    // bas, data-wired empêche tout double-câblage), indispensable sur la
    // landing page pour un visiteur dont la session vient d'être confirmée.
    wireButtons();
  } catch {
    // Page protégée côté serveur (abonnement.html) : si la session a expiré
    // entre-temps, on laisse les cartes dans leur état par défaut plutôt que
    // de planter. Sur une page publique (landing), c'est aussi le chemin
    // normal pour un visiteur non connecté : les boutons restent .js-open-signup,
    // gérés par auth.js (ouverture du formulaire d'inscription).
  }
}

wireButtons();
handleCheckoutReturn();
loadCurrentPlan();
