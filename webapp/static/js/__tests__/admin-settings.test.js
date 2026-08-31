// admin-settings.js : module "Paramètres" (/admin/settings, SUPER_ADMIN).
// Couvre en particulier :
// - la non-régression du bug corrigé dans ce chantier (backups.disk_total_bytes
//   indisponible plutôt qu'un KeyError côté backend — voir
//   webapp/tests/test_settings_service.py pour la preuve backend, ce test-ci
//   prouve que le frontend rend correctement ce contrat) ;
// - que la section Clés API utilise bien le composant partagé
//   admin-api-keys.js (allowEdit=true, comme avant ce chantier) — jamais une
//   implémentation locale dupliquée.
//
// Le payload ci-dessous est une capture RÉELLE de GET /api/admin/settings/overview
// (test_client Flask, compte super_admin réel) — jamais une forme devinée.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_SETTINGS = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "settings", label: "Paramètres", icon: "⚙️", path: "/admin/settings", implemented: true },
];

const OVERVIEW_PAYLOAD = {
  ai: {
    fallback_enabled: { enforced: true, enforced_reason: null, key: "ai_fallback_enabled", source: "database", type: "bool", updated_at: "2026-08-25T17:52:22.349002+00:00", value: true },
    max_response_tokens_default: { enforced: true, enforced_reason: null, key: "ai_max_response_tokens_default", max: 4096, min: 128, source: "database", type: "int", updated_at: "2026-08-25T17:52:22.336574+00:00", value: 1024 },
    provider_order: { available: true, value: [
      { enabled: true, id: 1, model_name: "gemini-3-flash-preview", name: "Gemini Flash", priority: 0, provider_key: "gemini" },
    ] },
    temperature_default: { enforced: true, enforced_reason: null, key: "ai_temperature_default", max: 1.0, min: 0.0, source: "database", type: "float", updated_at: "2026-08-25T17:52:22.328505+00:00", value: 0.6 },
  },
  api_keys: [
    {
      avg_response_time_ms: 14, created_at: "2026-07-30T14:35:41.957651+00:00", enabled: false,
      failure_count: 51, fallback_count: 51, id: 6, in_cooldown: false, label: "x",
      last_error: "Clé API Gemini invalide ou expirée.", last_failure_at: "2026-08-22T12:38:51.481514+00:00",
      last_success_at: null, last_used_at: "2026-08-22T12:38:51.481514+00:00",
      model_name: "gemini-3-flash-preview", priority: 0, provider_key: "gemini",
      quota_exceeded_until: "2026-08-23T12:38:51.479166+00:00", request_count: 51,
    },
  ],
  backups: {
    disk_total_bytes: { available: false, reason: "Cette donnée n'est plus calculée par system_health_service.storage_info() (retirée comme non actionnable lors du nettoyage de la page Santé).", value: null },
    disk_used_bytes: { available: true, value: 464548782080 },
    items: [
      { created_at: "2026-07-30T21:59:42.407430+00:00", filename: "novamath_backup_20260730_215942_407430.sqlite3", path: "C:\\backups\\novamath_backup_20260730_215942_407430.sqlite3", size_bytes: 26722304 },
    ],
    last_backup: { available: true, value: { created_at: "2026-07-30T21:59:42.407430+00:00", filename: "novamath_backup_20260730_215942_407430.sqlite3", path: "C:\\backups\\novamath_backup_20260730_215942_407430.sqlite3", size_bytes: 26722304 } },
    last_backup_successful: { available: true, value: true },
    last_error: { available: false, reason: "Aucun échec enregistré.", value: null },
    last_error_at: { available: false, reason: "Aucun échec enregistré.", value: null },
    total_size_bytes: 26722304,
  },
  logs: {
    level: { available: true, value: "INFO" },
    level_env_controlled_reason: "Piloté par la variable d'environnement LOG_LEVEL.",
    sentry_enabled: { available: true, value: false },
  },
  security: {
    csp: { available: true, value: { enabled: true, report_only: false } },
    hsts_enabled: { available: true, value: false },
    login_attempts: { available: true, value: { lockout_minutes: 15, max_attempts: 5 } },
    session_durations: { available: true, value: { default_days: 1, guest_days: 1, remember_me_days: 30 } },
    two_factor_admins: { available: true, value: { enabled: 0, total: 10 } },
  },
  smtp: {
    configured: true, encryption: { available: true, value: "STARTTLS" }, env_controlled: true,
    env_controlled_reason: "Piloté par variables d'environnement.",
    from_address: { available: true, value: "Mathadap <novamath.contact@gmail.com>" },
    host: { available: true, value: "smtp-relay.brevo.com" },
    last_test_at: { available: true, value: "2026-08-25T17:52:22.901580+00:00" },
    last_test_error: { available: true, value: "SMTP non configuré (EMAIL_SMTP_HOST absente)." },
    last_test_ok: { available: true, value: false },
    port: { available: true, value: 587 },
    username: { available: true, value: "b28933001@smtp-brevo.com" },
  },
  stripe: {
    env_controlled_reason: "Piloté par variables d'environnement.",
    mode: { available: true, value: "test" },
    webhook_configured: true,
  },
};

function mockFetchWith({ overview = OVERVIEW_PAYLOAD, failOverview = false } = {}) {
  global.fetch = vi.fn((url, options = {}) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_SETTINGS }) });
    }
    if (url === "/api/admin/settings/overview") {
      if (failOverview) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
      return Promise.resolve({ ok: true, json: () => Promise.resolve(overview) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(path, options) {
  window.history.pushState({}, "", path);
  document.body.innerHTML = loadPageBody("admin.html");
  document.cookie = "nm_csrf=test-csrf-token";
  mockFetchWith(options);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "nm_csrf=; expires=Thu, 01 Jan 1970 00:00:00 UTC";
});

describe("admin-settings.js — non-régression du bug disk_total_bytes (500)", () => {
  it("la page se charge sans erreur avec disk_total_bytes indisponible", async () => {
    await mount("/admin/settings");
    expect(document.getElementById("admin-global-error").hidden).toBe(true);
    expect(document.body.textContent).not.toMatch(/Impossible de charger les paramètres/);
  });

  it("une vraie panne de /api/admin/settings/overview (autre cause) affiche l'erreur normalement", async () => {
    await mount("/admin/settings", { failOverview: true });
    expect(document.getElementById("admin-global-error").hidden).toBe(false);
  });
});

describe("admin-settings.js — clés API via le composant partagé admin-api-keys.js", () => {
  it("affiche la clé avec le bouton Modifier (allowEdit=true, comme avant ce chantier)", async () => {
    await mount("/admin/settings");
    const keysContainer = document.getElementById("admin-settings-keys");
    expect(keysContainer.textContent).toContain("gemini-3-flash-preview");
    const buttons = [...keysContainer.querySelectorAll("button")].map((b) => b.textContent);
    expect(buttons).toContain("Modifier");
    expect(buttons).toContain("Tester");
    expect(buttons).toContain("Supprimer");
  });

  it("aucune table statique dupliquée dans le HTML — le composant construit tout dynamiquement", async () => {
    await mount("/admin/settings");
    expect(document.getElementById("admin-settings-keys-tbody")).toBeNull();
    expect(document.getElementById("admin-settings-keys-table")).toBeNull();
    expect(document.querySelector("#admin-settings-keys table")).not.toBeNull();
  });
});
