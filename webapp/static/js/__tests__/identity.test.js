// ── identity.js : widget d'identité de la sidebar (pseudo + plan) ──────────
// Couvre l'affichage du plan sous le pseudo (BUG FIX — la sidebar restait
// bloquée sur "Free" après un changement d'abonnement quand la page revenait
// du bfcache du navigateur, voir pageshow ci-dessous) et la non-régression
// du reste du widget (nom, avatar, badge invité).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises } from "./testUtils.js";

const mockApi = { me: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));

function mountSidebarUser() {
  document.body.innerHTML = `
    <div class="brand"></div>
    <aside class="sidebar">
      <a href="profil.html" class="sidebar-user" id="sidebar-user">
        <span class="sidebar-user-avatar" id="sidebar-user-avatar"></span>
        <span class="sidebar-user-info">
          <span class="name" id="sidebar-user-name">Élève</span>
          <span class="sub" id="sidebar-user-plan">Free</span>
        </span>
      </a>
    </aside>
  `;
}

async function mountIdentity(user) {
  mountSidebarUser();
  mockApi.me.mockReset();
  mockApi.me.mockResolvedValue({ user });
  vi.resetModules();
  await import("../identity.js");
  await flushPromises();
}

const planText = () => document.getElementById("sidebar-user-plan").textContent;

describe("identity.js — affichage du plan dans la sidebar", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("utilisateur Free : affiche « Free »", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Free");
  });

  it("utilisateur Premium : affiche « Premium »", async () => {
    await mountIdentity({ plan: "premium", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Premium");
  });

  it("utilisateur Ultra : affiche « Ultra »", async () => {
    await mountIdentity({ plan: "ultra", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Ultra");
  });

  it("plan inconnu/absent : se rabat sur « Free » plutôt que planter", async () => {
    await mountIdentity({ plan: undefined, pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Free");
  });

  it("novamath:account-updated (Free -> Premium) met à jour immédiatement l'affichage", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Free");

    window.dispatchEvent(new CustomEvent("novamath:account-updated", {
      detail: { plan: "premium", pseudo: "Léa", is_guest: false },
    }));
    await flushPromises();

    expect(planText()).toBe("Premium");
  });

  it("un ancien « Free » ne reste jamais affiché après un changement de plan", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false });
    window.dispatchEvent(new CustomEvent("novamath:account-updated", {
      detail: { plan: "ultra", pseudo: "Léa", is_guest: false },
    }));
    await flushPromises();
    expect(planText()).not.toBe("Free");
    expect(planText()).toBe("Ultra");
  });

  // BUG FIX : une page restaurée depuis le bfcache du navigateur (navigation
  // arrière/avant) ne réexécute jamais le JS du module — sans ce correctif,
  // la sidebar restait figée sur le plan affiché avant le changement
  // d'abonnement effectué sur une autre page, jusqu'à un rechargement complet.
  it("pageshow avec persisted=true (retour bfcache) rafraîchit le plan affiché", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Free");

    // Le plan a changé entre-temps sur une autre page (ex: abonnement.html) ;
    // rien dans CETTE page ne le sait encore tant que pageshow ne se déclenche pas.
    mockApi.me.mockResolvedValue({ user: { plan: "premium", pseudo: "Léa", is_guest: false } });
    // jsdom n'implémente pas PageTransitionEvent : on simule `persisted` sur
    // un Event générique, exactement ce que le navigateur expose en lecture
    // lors d'une restauration bfcache.
    const evt = new Event("pageshow");
    Object.defineProperty(evt, "persisted", { value: true });
    window.dispatchEvent(evt);
    await flushPromises();

    expect(planText()).toBe("Premium");
  });

  it("pageshow SANS persisted (chargement normal) ne déclenche pas de second fetch", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false });
    const callsBefore = mockApi.me.mock.calls.length;
    const evt = new Event("pageshow");
    Object.defineProperty(evt, "persisted", { value: false });
    window.dispatchEvent(evt);
    await flushPromises();
    expect(mockApi.me.mock.calls.length).toBe(callsBefore);
    expect(planText()).toBe("Free");
  });

  it("nom et avatar restent corrects après une mise à jour de plan (non-régression)", async () => {
    await mountIdentity({ plan: "free", pseudo: "Léa", is_guest: false, avatar: null });
    window.dispatchEvent(new CustomEvent("novamath:account-updated", {
      detail: { plan: "premium", pseudo: "Léa", is_guest: false, avatar: null },
    }));
    await flushPromises();
    expect(document.getElementById("sidebar-user-name").textContent).toBe("Léa");
    expect(planText()).toBe("Premium");
  });
});

// ── Mode test Owner : la sidebar doit suivre le plan EFFECTIF simulé (voir
// owner_test_plan_service.py::effective_plan), jamais le plan réel/Stripe
// (`plan`), sans quoi le panneau "🧪 Mode test Owner" reste sans effet visible
// dans la sidebar — c'est précisément le bug corrigé ici.
describe("identity.js — plan effectif (Mode test Owner)", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("compte normal : effective_plan identique à plan, aucun changement d'affichage", async () => {
    await mountIdentity({ plan: "free", effective_plan: "free", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Free");
  });

  it("Owner sans simulation : effective_plan (Ultra par défaut) prime sur le plan réel Free", async () => {
    await mountIdentity({ plan: "free", effective_plan: "ultra", pseudo: "Owner", is_guest: false });
    expect(planText()).toBe("Ultra");
  });

  it("Owner avec simulation Premium active : affiche « Premium » alors que le plan réel est Free", async () => {
    await mountIdentity({ plan: "free", effective_plan: "premium", pseudo: "Owner", is_guest: false });
    expect(planText()).toBe("Premium");
  });

  it("changement de plan de test via novamath:account-updated met à jour la sidebar", async () => {
    await mountIdentity({ plan: "free", effective_plan: "free", pseudo: "Owner", is_guest: false });
    expect(planText()).toBe("Free");

    window.dispatchEvent(new CustomEvent("novamath:account-updated", {
      detail: { plan: "free", effective_plan: "ultra", pseudo: "Owner", is_guest: false },
    }));
    await flushPromises();

    expect(planText()).toBe("Ultra");
  });

  it("aucun champ effective_plan (ancienne réponse API) : se rabat sur plan, non-régression", async () => {
    await mountIdentity({ plan: "premium", pseudo: "Léa", is_guest: false });
    expect(planText()).toBe("Premium");
  });
});
