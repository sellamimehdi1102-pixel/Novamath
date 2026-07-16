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
import { PLAN_LABELS, featureLabel, requiredPlanFor, planMeetsRequirement, nextPlanAbove } from "./features.js";

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

function paintCurrentPlan(plan) {
  document.querySelectorAll(".pricing-card").forEach((card) => {
    const cardPlan = card.dataset.plan;
    const btn = card.querySelector("[data-plan-button]");
    const isCurrent = cardPlan === plan;
    card.toggleAttribute("data-plan-current", isCurrent);
    if (!btn) return;
    if (cardPlan === "free") {
      btn.disabled = true;
      btn.textContent = isCurrent ? "Plan actuel" : "Formule de base";
      return;
    }
    if (isCurrent) {
      btn.disabled = true;
      btn.textContent = "Plan actuel";
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

function wireButtons() {
  document.querySelectorAll("[data-plan-button]").forEach((btn) => {
    const plan = btn.dataset.planButton;
    if (plan === "free") return;
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      startCheckout(plan, btn);
    });
  });
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

function showRequiredFeatureBanner(featureValue, currentPlan) {
  const requiredPlan = requiredPlanFor(featureValue);
  if (planMeetsRequirement(currentPlan, requiredPlan)) return;
  const planLabel = PLAN_LABELS[requiredPlan] || "Premium";
  paintUpgradeBanner({
    title: `Cette fonctionnalité nécessite ${planLabel}.`,
    desc: `${featureLabel(featureValue)} fait partie de la formule ${planLabel}. Débloque-la dès maintenant :`,
    requiredPlan,
  });
}

// Free -> Premium mis en avant ; Premium -> Ultra mis en avant (jamais
// déclenché pour un compte déjà Ultra, qui n'épuise jamais son quota — voir
// quota_service.consume). `quotaValue` n'affecte pas le texte générique de
// la bannière (le message reste le même quel que soit le quota concerné,
// aujourd'hui uniquement chat_messages) mais reste transporté pour un futur
// message spécifique par type de quota si besoin.
function showQuotaExceededBanner(currentPlan) {
  const requiredPlan = nextPlanAbove(currentPlan);
  const planLabel = PLAN_LABELS[requiredPlan] || "Premium";
  paintUpgradeBanner({
    title: "Tu as atteint ta limite quotidienne.",
    desc: `Les quotas sont réinitialisés chaque jour. Passe à ${planLabel} pour continuer immédiatement.`,
    requiredPlan,
  });
}

function handleUpgradeParams(currentPlan) {
  const params = new URLSearchParams(window.location.search);
  const feature = params.get("required");
  const reason = params.get("reason");
  if (feature) {
    showRequiredFeatureBanner(feature, currentPlan);
  } else if (reason === "quota") {
    showQuotaExceededBanner(currentPlan);
  }
}

async function loadCurrentPlan() {
  try {
    const { user } = await api.me();
    const plan = user.plan || "free";
    paintCurrentPlan(plan);
    handleUpgradeParams(plan);
  } catch {
    // Page protégée côté serveur : si la session a expiré entre-temps, on
    // laisse les cartes dans leur état par défaut plutôt que de planter.
  }
}

wireButtons();
handleCheckoutReturn();
loadCurrentPlan();
