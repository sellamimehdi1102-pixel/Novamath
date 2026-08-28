// admin-api-keys.js : composant partagé de rendu de la liste des clés API IA
// — utilisé par /admin/ia (admin-ai.js) ET /admin/settings (admin-settings.js),
// qui affichaient auparavant la même donnée (/api/admin/ai/keys) via deux
// implémentations dupliquées (cartes vs tableau). Ce test couvre le module
// directement (sans monter une page complète) : structure, badges d'état,
// respect strict de `allowEdit` (la capacité "Modifier" ne doit JAMAIS
// apparaître quand l'appelant ne la demande pas explicitement — c'était
// auparavant réservé à /admin/settings, jamais /admin/ia).
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderApiKeysTable, keyState } from "../admin-api-keys.js";
import { flushPromises } from "./testUtils.js";

function apiKey(overrides = {}) {
  return {
    id: 42,
    label: "Clé principale",
    provider_key: "gemini",
    model_name: "gemini-3-flash-preview",
    enabled: true,
    in_cooldown: false,
    priority: 0,
    last_used_at: "2026-08-20T10:00:00+00:00",
    request_count: 100,
    failure_count: 5,
    fallback_count: 2,
    avg_response_time_ms: 850,
    last_error: null,
    last_success_at: "2026-08-20T10:00:00+00:00",
    last_failure_at: null,
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-api-keys.js — keyState (dérivation d'état)", () => {
  it("cooldown prime sur tout le reste", () => {
    expect(keyState(apiKey({ in_cooldown: true })).label).toBe("Quota atteint (cooldown)");
  });
  it("désactivée si enabled=false", () => {
    expect(keyState(apiKey({ enabled: false })).label).toBe("Désactivée");
  });
  it("erreur si le dernier échec est plus récent que le dernier succès", () => {
    const state = keyState(apiKey({
      last_error: "boom", last_success_at: "2026-08-20T10:00:00+00:00", last_failure_at: "2026-08-20T11:00:00+00:00",
    }));
    expect(state.label).toBe("Erreur");
  });
  it("active si enabled et pas d'échec plus récent qu'un succès", () => {
    expect(keyState(apiKey()).label).toBe("Active");
  });
});

describe("admin-api-keys.js — renderApiKeysTable", () => {
  it("état vide : affiche le message personnalisé, aucun tableau", () => {
    const container = document.createElement("div");
    renderApiKeysTable(container, [], { emptyMessage: "Rien ici." });
    expect(container.textContent).toContain("Rien ici.");
    expect(container.querySelector("table")).toBeNull();
  });

  it("allowEdit=false (contexte /admin/ia) : jamais de bouton Modifier", () => {
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey()], { onChanged: () => {}, allowEdit: false });
    const buttons = [...container.querySelectorAll("button")].map((b) => b.textContent);
    expect(buttons).not.toContain("Modifier");
    expect(buttons).toContain("Tester");
    expect(buttons).toContain("Désactiver");
    expect(buttons).toContain("Supprimer");
  });

  it("allowEdit=true (contexte /admin/settings) : bouton Modifier présent", () => {
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey()], { onChanged: () => {}, allowEdit: true });
    const buttons = [...container.querySelectorAll("button")].map((b) => b.textContent);
    expect(buttons).toContain("Modifier");
  });

  it("à source de données identique, le rendu (hors bouton Modifier) est identique pour allowEdit=true et false", () => {
    const containerA = document.createElement("div");
    const containerB = document.createElement("div");
    renderApiKeysTable(containerA, [apiKey()], { onChanged: () => {}, allowEdit: false });
    renderApiKeysTable(containerB, [apiKey()], { onChanged: () => {}, allowEdit: true });
    const cellsA = [...containerA.querySelectorAll("td:not(:last-child)")].map((td) => td.textContent);
    const cellsB = [...containerB.querySelectorAll("td:not(:last-child)")].map((td) => td.textContent);
    expect(cellsA).toEqual(cellsB);
  });

  it("affiche une ligne d'erreur additionnelle si last_error est présent", () => {
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey({ last_error: "Clé invalide (401)" })], { onChanged: () => {} });
    expect(container.textContent).toContain("Dernière erreur : Clé invalide (401)");
  });

  it("le bouton Tester appelle POST /api/admin/ai/keys/:id/test puis onChanged", async () => {
    document.cookie = "nm_csrf=test-token";
    const calls = [];
    global.fetch = vi.fn((url, opts) => {
      calls.push({ url, method: opts?.method });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true, latency_ms: 120 }) });
    });
    global.alert = vi.fn();
    const onChanged = vi.fn();
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey()], { onChanged, allowEdit: false });

    const testBtn = [...container.querySelectorAll("button")].find((b) => b.textContent === "Tester");
    testBtn.click();
    await flushPromises();

    expect(calls).toContainEqual({ url: "/api/admin/ai/keys/42/test", method: "POST" });
    expect(onChanged).toHaveBeenCalled();
  });

  it("le bouton Supprimer demande confirmation puis appelle DELETE", async () => {
    document.cookie = "nm_csrf=test-token";
    const calls = [];
    global.fetch = vi.fn((url, opts) => {
      calls.push({ url, method: opts?.method });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
    global.confirm = vi.fn(() => true);
    const onChanged = vi.fn();
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey()], { onChanged, allowEdit: false });

    const deleteBtn = [...container.querySelectorAll("button")].find((b) => b.textContent === "Supprimer");
    deleteBtn.click();
    await flushPromises();

    expect(global.confirm).toHaveBeenCalled();
    expect(calls).toContainEqual({ url: "/api/admin/ai/keys/42", method: "DELETE" });
    expect(onChanged).toHaveBeenCalled();
  });

  it("Supprimer annulé (confirm=false) n'appelle jamais l'API", async () => {
    global.fetch = vi.fn();
    global.confirm = vi.fn(() => false);
    const container = document.createElement("div");
    renderApiKeysTable(container, [apiKey()], { onChanged: () => {}, allowEdit: false });

    const deleteBtn = [...container.querySelectorAll("button")].find((b) => b.textContent === "Supprimer");
    deleteBtn.click();
    await Promise.resolve();

    expect(global.fetch).not.toHaveBeenCalled();
  });
});
