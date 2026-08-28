// ── owner-test-panel.js : widget flottant Owner (dashboard/chatbot/...) ────
// Chantier 8 : après un changement de plan de test, ce widget doit notifier
// le reste de la page (sidebar/identity.js) via novamath:account-updated —
// exactement la même convention que abonnement.js::notifyAccountUpdated
// (Chantier 6). Avant ce correctif, la sidebar restait figée sur l'ancien
// plan sur toute page autre que abonnement.html.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  ownerTestPlanStatus: vi.fn(),
  ownerTestPlanUpdate: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));

const statusFree = { real_plan: "free", test_plan: null, effective_plan: "free", owner_unlimited_quotas: false, provider: "gemini", model: "gemini-3-flash-preview" };
const statusPremium = { real_plan: "free", test_plan: "premium", effective_plan: "premium", owner_unlimited_quotas: false, provider: "gemini", model: "gemini-3.1-pro-preview" };
const statusUltra = { real_plan: "free", test_plan: "ultra", effective_plan: "ultra", owner_unlimited_quotas: false, provider: "anthropic", model: "claude-sonnet-5" };

async function mountOwnerPanel(url = "/dashboard.html", initialStatus = statusFree) {
  window.history.pushState({}, "", url);
  document.body.innerHTML = "";
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { plan: "free", is_owner: true } });
  mockApi.ownerTestPlanStatus.mockResolvedValue(initialStatus);
  vi.resetModules();
  const { initOwnerTestPanel } = await import("../owner-test-panel.js");
  await initOwnerTestPanel();
  await flushPromises();
}

describe("owner-test-panel.js — synchronisation novamath:account-updated (Chantier 8)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("ne s'active pas sur abonnement.html (déjà couvert par abonnement.js)", async () => {
    await mountOwnerPanel("/abonnement.html");
    expect(document.getElementById("owner-test-toggle")).toBeNull();
    expect(mockApi.ownerTestPlanStatus).not.toHaveBeenCalled();
  });

  it("changement Free -> Premium déclenche novamath:account-updated avec les données fraîches de api.me()", async () => {
    await mountOwnerPanel();
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusPremium);
    mockApi.me.mockResolvedValue({ user: { plan: "free", is_owner: true, features: { chatbot_unlimited: true } } });

    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan="premium"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);

    expect(mockApi.ownerTestPlanUpdate).toHaveBeenCalledWith({ plan: "premium" });
    // api.me() appelé une 2e fois après ownerTestPlanUpdate (1 au montage + 1 après le clic).
    expect(mockApi.me).toHaveBeenCalledTimes(2);
    expect(onUpdate).toHaveBeenCalledTimes(1);
    expect(onUpdate.mock.calls[0][0].detail).toEqual({ plan: "free", is_owner: true, features: { chatbot_unlimited: true } });
  });

  it("changement Premium -> Ultra déclenche l'événement", async () => {
    await mountOwnerPanel();
    mockApi.ownerTestPlanUpdate.mockResolvedValueOnce(statusPremium).mockResolvedValueOnce(statusUltra);
    mockApi.me.mockResolvedValue({ user: { plan: "free", is_owner: true, features: {} } });

    document.querySelector('[data-plan="premium"]').click();
    await flushPromises();

    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan="ultra"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);

    expect(mockApi.ownerTestPlanUpdate).toHaveBeenLastCalledWith({ plan: "ultra" });
    expect(onUpdate).toHaveBeenCalledTimes(1);
  });

  it("changement Ultra -> Free (re-clic = désactive) déclenche l'événement", async () => {
    await mountOwnerPanel("/dashboard.html", statusUltra); // panneau déjà en mode test "ultra"
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusFree);

    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan="ultra"]').click(); // re-clic sur le plan déjà actif = désactive
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);

    expect(mockApi.ownerTestPlanUpdate).toHaveBeenCalledWith({ plan: null });
    expect(onUpdate).toHaveBeenCalledTimes(1);
  });

  it("le bouton Réinitialiser déclenche aussi l'événement", async () => {
    await mountOwnerPanel();
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusFree);

    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-action="reset"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);

    expect(mockApi.ownerTestPlanUpdate).toHaveBeenCalledWith({ plan: null });
    expect(onUpdate).toHaveBeenCalledTimes(1);
  });

  it("n'utilise jamais directement le `status` retourné par ownerTestPlanUpdate comme objet user", async () => {
    // status n'a pas la forme d'un objet `user` (pas de pseudo/avatar) — si le
    // widget le dispatchait tel quel, identity.js recevrait un detail cassé.
    await mountOwnerPanel();
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusPremium);
    mockApi.me.mockResolvedValue({ user: { plan: "free", is_owner: true, pseudo: "Owner", avatar: null, features: {} } });

    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan="premium"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);

    const detail = onUpdate.mock.calls[0][0].detail;
    expect(detail).not.toBe(statusPremium);
    expect(detail.pseudo).toBe("Owner");
  });
});
