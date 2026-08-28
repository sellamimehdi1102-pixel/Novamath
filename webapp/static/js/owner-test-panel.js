// Widget "Mode test Owner" — réservé exclusivement au compte owner (voir
// webapp/owner_service.py::is_owner_account, webapp/owner_test_plan_service.py).
// Auto-injecté sur toute page avec .sidebar (voir sidebar.js::init), mais ne
// fait AUCUN appel réseau vers /api/owner/test-plan tant que api.me() n'a
// pas confirmé user.is_owner === true : pour tout autre compte (y compris un
// super_admin), ce module ne fait strictement rien de visible ni de réseau
// au-delà de l'appel /api/auth/me déjà effectué ailleurs par les autres
// widgets de sidebar.js (même pattern que applyAdminMenuEntry/applyFeatureLocks).
//
// Simulation locale uniquement : ce panneau ne modifie jamais users.plan ni
// Stripe (voir server.py::api_owner_test_plan_patch) — uniquement le plan
// EFFECTIF utilisé en interne par plan_service/quota_service/provider_manager
// pour CE compte. Le rappel "Simulation locale — aucun changement Stripe"
// est affiché en permanence dans le panneau pour éviter toute confusion.
import { api } from "./api.js";

const PLAN_LABELS = { free: "FREE", premium: "PREMIUM", ultra: "ULTRA" };
const PLANS = ["free", "premium", "ultra"];

let injectedStyles = false;

function injectStyles() {
  if (injectedStyles) return;
  injectedStyles = true;
  const style = document.createElement("style");
  style.textContent = `
    #owner-test-toggle {
      position: fixed; bottom: 20px; right: 20px; z-index: 9998;
      width: 44px; height: 44px; border-radius: 50%; border: none;
      background: #1f2937; color: #fff; font-size: 18px; cursor: pointer;
      box-shadow: 0 4px 14px rgba(0,0,0,.25);
    }
    #owner-test-panel {
      position: fixed; bottom: 74px; right: 20px; z-index: 9999;
      width: 300px; background: #fff; color: #1f2937;
      border: 1px solid #e5e7eb; border-radius: 12px;
      box-shadow: 0 8px 30px rgba(0,0,0,.18);
      font: 13px/1.4 system-ui, sans-serif; padding: 14px;
    }
    #owner-test-panel.is-hidden { display: none; }
    #owner-test-panel h3 { margin: 0 0 10px; font-size: 13px; font-weight: 700; }
    #owner-test-panel .otp-row { display: flex; justify-content: space-between; align-items: center; margin: 6px 0; }
    #owner-test-panel .otp-label { color: #6b7280; }
    #owner-test-panel .otp-value { font-weight: 600; }
    #owner-test-panel .otp-plan-buttons { display: flex; gap: 6px; margin: 8px 0; }
    #owner-test-panel .otp-plan-buttons button {
      flex: 1; padding: 5px 0; font-size: 11px; font-weight: 600;
      border: 1px solid #d1d5db; border-radius: 6px; background: #f9fafb; cursor: pointer;
    }
    #owner-test-panel .otp-plan-buttons button.is-active { background: #1f2937; color: #fff; border-color: #1f2937; }
    #owner-test-panel .otp-reset {
      width: 100%; margin-top: 10px; padding: 6px 0; font-size: 12px;
      border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer;
    }
    #owner-test-panel .otp-note { margin-top: 10px; font-size: 11px; color: #9ca3af; }
    #owner-test-panel .otp-quota-toggle { display: flex; align-items: center; gap: 6px; }
  `;
  document.head.appendChild(style);
}

function buildPanel() {
  const toggle = document.createElement("button");
  toggle.id = "owner-test-toggle";
  toggle.type = "button";
  toggle.title = "Mode test Owner";
  toggle.textContent = "🧪";

  const panel = document.createElement("div");
  panel.id = "owner-test-panel";
  panel.className = "is-hidden";
  panel.innerHTML = `
    <h3>🧪 Mode test Owner</h3>
    <div class="otp-row"><span class="otp-label">Plan réel</span><span class="otp-value" data-field="real_plan">—</span></div>
    <div class="otp-plan-buttons" data-field="plan-buttons"></div>
    <div class="otp-row"><span class="otp-label">Plan effectif</span><span class="otp-value" data-field="effective_plan">—</span></div>
    <div class="otp-row otp-quota-toggle">
      <label><input type="checkbox" data-field="unlimited_quotas" /> Quotas owner illimités</label>
    </div>
    <div class="otp-row"><span class="otp-label">Provider</span><span class="otp-value" data-field="provider">—</span></div>
    <div class="otp-row"><span class="otp-label">Modèle</span><span class="otp-value" data-field="model">—</span></div>
    <button type="button" class="otp-reset" data-action="reset">Réinitialiser le test</button>
    <p class="otp-note">Simulation locale — aucun changement Stripe. users.plan n'est jamais modifié.</p>
  `;

  const planButtons = panel.querySelector('[data-field="plan-buttons"]');
  PLANS.forEach((plan) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.plan = plan;
    btn.textContent = PLAN_LABELS[plan];
    planButtons.appendChild(btn);
  });

  document.body.append(toggle, panel);
  toggle.addEventListener("click", () => panel.classList.toggle("is-hidden"));
  return { toggle, panel };
}

// Notifie les autres widgets de la page (sidebar/identity.js, carte compte du
// dashboard, page profil) qu'un plan effectif à jour est disponible — même
// convention que abonnement.js::notifyAccountUpdated (Chantier 6/8). Sans ça,
// la sidebar (peinte une seule fois au chargement de la page) continuait
// d'afficher l'ancien plan indéfiniment après un changement fait depuis ce
// panneau flottant, sur toute page autre que abonnement.html (seule page où
// ce widget se désactive — voir initOwnerTestPanel ci-dessous). `status`
// (retour de ownerTestPlanUpdate) n'a pas la forme d'un objet `user` (pas de
// pseudo/avatar/plan réel) : un appel frais à api.me() est nécessaire plutôt
// que de dispatcher `status` tel quel.
async function notifySidebarOfPlanChange() {
  try {
    const { user } = await api.me();
    window.dispatchEvent(new CustomEvent("novamath:account-updated", { detail: user }));
  } catch {
    // Best-effort : le panneau lui-même reste à jour (render() déjà appelé),
    // seule la notification des autres widgets échouerait.
  }
}

function render(panel, status) {
  panel.querySelector('[data-field="real_plan"]').textContent = PLAN_LABELS[status.real_plan] || status.real_plan;
  panel.querySelector('[data-field="effective_plan"]').textContent = PLAN_LABELS[status.effective_plan] || status.effective_plan;
  panel.querySelector('[data-field="provider"]').textContent = status.provider || "—";
  panel.querySelector('[data-field="model"]').textContent = status.model || "—";
  panel.querySelector('[data-field="unlimited_quotas"]').checked = !!status.owner_unlimited_quotas;
  panel.querySelectorAll('[data-field="plan-buttons"] button').forEach((btn) => {
    btn.classList.toggle("is-active", btn.dataset.plan === status.test_plan);
  });
}

export async function initOwnerTestPanel() {
  // abonnement.html (Chantier 6) intègre désormais les mêmes boutons
  // FREE/PREMIUM/ULTRA directement dans ses cartes de prix (voir
  // abonnement.js::wireOwnerButtons) — ce widget flottant s'y masquerait
  // sinon en double avec exactement la même action. Reste actif sur toutes
  // les autres pages (dashboard, chatbot...) pour les réglages avancés que
  // les cartes n'exposent pas (quotas illimités, provider/modèle réels).
  if (window.location.pathname.endsWith("/abonnement.html")) return;

  let user;
  try {
    ({ user } = await api.me());
  } catch {
    return; // Session expirée/invité : jamais de panneau owner à l'aveugle.
  }
  if (!user?.is_owner) return; // Fail-closed côté client aussi : aucun appel /api/owner/test-plan sinon.

  let status;
  try {
    status = await api.ownerTestPlanStatus();
  } catch {
    return; // 404 (NOVAMATH_OWNER_USER_ID mal configuré / incohérence) : rien à afficher.
  }

  injectStyles();
  const { panel } = buildPanel();
  render(panel, status);

  panel.querySelectorAll('[data-field="plan-buttons"] button').forEach((btn) => {
    btn.addEventListener("click", async () => {
      const plan = btn.dataset.plan === status.test_plan ? null : btn.dataset.plan; // re-clic = désactive
      status = await api.ownerTestPlanUpdate({ plan });
      render(panel, status);
      await notifySidebarOfPlanChange();
    });
  });

  panel.querySelector('[data-field="unlimited_quotas"]').addEventListener("change", async (e) => {
    status = await api.ownerTestPlanUpdate({ unlimited_quotas: e.target.checked });
    render(panel, status);
    await notifySidebarOfPlanChange();
  });

  panel.querySelector('[data-action="reset"]').addEventListener("click", async () => {
    status = await api.ownerTestPlanUpdate({ plan: null });
    render(panel, status);
    await notifySidebarOfPlanChange();
  });
}
