// admin-health.js : renommage "Disponibilité" → "Disponibilité IA" et
// "Historique des incidents" → "Incidents IA" (audit admin 2026-10-20) —
// vérifié au préalable que les deux métriques sont EXCLUSIVEMENT liées à
// l'IA côté backend (system_health_service.py::availability()/
// list_incidents(), voir leurs docstrings) avant de renommer. Aucune clé
// JSON renommée : seuls les libellés affichés changent.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const NAV_WITH_HEALTH = [
  { id: "health", label: "Santé système", icon: "🩺", path: "/admin/health", implemented: true },
];

const NA = { available: false, value: null, reason: "test" };

const OVERVIEW_PAYLOAD = {
  overview: { global_status: "ok", degraded_count: 0, down_count: 0, checked_at: "2026-10-20T10:00:00+00:00" },
  services: [
    {
      id: "sqlite",
      name: "Base SQLite",
      state: "ok",
      latency_ms: { available: true, value: 1 },
      last_success: NA,
      last_failure: NA,
      version: NA,
    },
    { id: "stripe", name: "Stripe", state: "ok", latency_ms: NA, last_success: NA, last_failure: NA, version: NA },
    { id: "smtp", name: "SMTP", state: "ok", latency_ms: NA, last_success: NA, last_failure: NA, version: NA },
  ],
  availability: { "24h": NA, "7j": NA, "30j": NA },
  database: { state: { available: true, value: "ok" }, introspection: NA, last_backup: NA },
  storage: { uploads_bytes: NA, database_bytes: NA, disk_free_bytes: NA, disk_used_bytes: NA },
  server: {
    cpu_percent: NA,
    ram_percent: NA,
    uptime_seconds: 10,
    process_started_at: "2026-10-20T09:00:00+00:00",
    avg_api_response_time_ms: NA,
  },
  alerts: [],
};

const INCIDENTS_PAYLOAD = { items: [] };

function mockFetchWith(overviewOverrides = {}) {
  const overviewPayload = { ...OVERVIEW_PAYLOAD, ...overviewOverrides };
  global.fetch = vi.fn((url) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_HEALTH }) });
    }
    if (url === "/api/admin/system-health/overview") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(overviewPayload) });
    }
    if (url.startsWith("/api/admin/system-health/incidents")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(INCIDENTS_PAYLOAD) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(overviewOverrides) {
  window.history.pushState({}, "", "/admin/health");
  document.body.innerHTML = loadPageBody("admin.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockFetchWith(overviewOverrides);
  vi.resetModules();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-health.js — renommage Disponibilité IA / Incidents IA", () => {
  it("affiche 'Disponibilité IA', jamais le libellé ambigu 'Disponibilité' seul", async () => {
    await mount();
    const body = document.getElementById("admin-content-body");
    expect(body.textContent).toContain("Disponibilité IA");
  });

  it("affiche 'Incidents IA', jamais 'Historique des incidents'", async () => {
    await mount();
    const body = document.getElementById("admin-content-body");
    expect(body.textContent).toContain("Incidents IA");
    expect(body.textContent).not.toContain("Historique des incidents");
  });
});

describe("admin-health.js — fusion des cartes Disponibilité IA (Chantier Santé, 2026-10-22)", () => {
  it("les 3 fenêtres indisponibles : UN SEUL message groupé, pas 3 cartes répétant la même raison", async () => {
    await mount(); // OVERVIEW_PAYLOAD par défaut : les 3 fenêtres sont NA (available: false)
    const container = document.getElementById("admin-health-availability");
    expect(container.querySelectorAll(".admin-card").length).toBe(1);
    expect(container.textContent).toContain("Données insuffisantes sur toutes les fenêtres (24h/7j/30j).");
    expect(container.textContent).not.toContain("24 heures");
    expect(container.textContent).not.toContain("7 jours");
    expect(container.textContent).not.toContain("30 jours");
  });

  it("au moins une fenêtre a une vraie donnée : les 3 cartes habituelles reviennent", async () => {
    await mount({
      availability: {
        "24h": { available: false, value: null, reason: "test" },
        "7j": { available: true, value: 98.5 },
        "30j": { available: false, value: null, reason: "test" },
      },
    });
    const container = document.getElementById("admin-health-availability");
    expect(container.querySelectorAll(".admin-card").length).toBe(3);
    expect(container.textContent).toContain("24 heures");
    expect(container.textContent).toContain("7 jours");
    expect(container.textContent).toContain("30 jours");
    expect(container.textContent).toContain("98.5%");
  });
});
