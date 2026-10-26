// admin-settings.js : module "Paramètres" (/admin/settings, SUPER_ADMIN).
// Couvre en particulier :
// - la non-régression du bug corrigé dans ce chantier (backups.disk_total_bytes
//   indisponible plutôt qu'un KeyError côté backend — voir
//   webapp/tests/test_settings_service.py pour la preuve backend, ce test-ci
//   prouve que le frontend rend correctement ce contrat) ;
// - Finalisation du nettoyage admin (2026-10-22) : la gestion des clés API
//   est centralisée dans /admin/ia — cette page ne garde plus qu'un lien
//   compact "Clés API → /admin/ia" (voir admin-ai.test.js pour la gestion
//   complète, désormais seule source : allowEdit=true là-bas) ;
// - Audit admin (2026-10-22) : la section "IA" de Paramètres pointe désormais
//   vers /admin/ia au lieu de dupliquer la liste des fournisseurs (le backend
//   ne renvoie plus `ai.provider_order`, voir settings_service.py::ai_config) ;
// - Audit admin (2026-10-22) : la carte "Espace disque utilisé" (pourcentage +
//   barre de progression, structurellement morte car disk_total_bytes n'est
//   plus jamais disponible) a été retirée du bloc Sauvegardes.
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
    fallback_enabled: {
      enforced: true,
      enforced_reason: null,
      key: "ai_fallback_enabled",
      source: "database",
      type: "bool",
      updated_at: "2026-08-25T17:52:22.349002+00:00",
      value: true,
    },
    max_response_tokens_default: {
      enforced: true,
      enforced_reason: null,
      key: "ai_max_response_tokens_default",
      max: 4096,
      min: 128,
      source: "database",
      type: "int",
      updated_at: "2026-08-25T17:52:22.336574+00:00",
      value: 1024,
    },
    temperature_default: {
      enforced: true,
      enforced_reason: null,
      key: "ai_temperature_default",
      max: 1.0,
      min: 0.0,
      source: "database",
      type: "float",
      updated_at: "2026-08-25T17:52:22.328505+00:00",
      value: 0.6,
    },
  },
  api_keys: [
    {
      avg_response_time_ms: 14,
      created_at: "2026-07-30T14:35:41.957651+00:00",
      enabled: false,
      failure_count: 51,
      fallback_count: 51,
      id: 6,
      in_cooldown: false,
      label: "x",
      last_error: "Clé API Gemini invalide ou expirée.",
      last_failure_at: "2026-08-22T12:38:51.481514+00:00",
      last_success_at: null,
      last_used_at: "2026-08-22T12:38:51.481514+00:00",
      model_name: "gemini-3-flash-preview",
      priority: 0,
      provider_key: "gemini",
      quota_exceeded_until: "2026-08-23T12:38:51.479166+00:00",
      request_count: 51,
    },
  ],
  backups: {
    disk_total_bytes: {
      available: false,
      reason:
        "Cette donnée n'est plus calculée par system_health_service.storage_info() (retirée comme non actionnable lors du nettoyage de la page Santé).",
      value: null,
    },
    disk_used_bytes: { available: true, value: 464548782080 },
    items: [
      {
        created_at: "2026-07-30T21:59:42.407430+00:00",
        filename: "novamath_backup_20260730_215942_407430.sqlite3",
        path: "C:\\backups\\novamath_backup_20260730_215942_407430.sqlite3",
        size_bytes: 26722304,
      },
    ],
    last_backup: {
      available: true,
      value: {
        created_at: "2026-07-30T21:59:42.407430+00:00",
        filename: "novamath_backup_20260730_215942_407430.sqlite3",
        path: "C:\\backups\\novamath_backup_20260730_215942_407430.sqlite3",
        size_bytes: 26722304,
      },
    },
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
    configured: true,
    encryption: { available: true, value: "STARTTLS" },
    env_controlled: true,
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
    configured: true,
    webhook_configured: true,
  },
};

function mockFetchWith({ overview = OVERVIEW_PAYLOAD, failOverview = false } = {}) {
  global.fetch = vi.fn((url, _options = {}) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_SETTINGS }) });
    }
    if (url === "/api/admin/settings/overview") {
      if (failOverview)
        return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
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

describe("admin-settings.js — clés API centralisées dans /admin/ia (finalisation du nettoyage admin, 2026-10-22)", () => {
  it("ne construit plus aucun formulaire de création ni tableau de clés ici — uniquement un lien vers /admin/ia", async () => {
    await mount("/admin/settings");
    expect(document.getElementById("admin-settings-keys")).toBeNull();
    expect(document.getElementById("admin-settings-new-key-btn")).toBeNull();
    expect(document.getElementById("admin-settings-new-key-form")).toBeNull();
    const aiSection = document.querySelector('[data-collapse-id="settings-ai"]');
    const link = aiSection.querySelector('a[href="/admin/ia"]');
    expect(link).not.toBeNull();
    expect(aiSection.textContent).toContain("Clés API");
  });
});

// Audit admin (2026-10-20) : avant ce chantier, le frontend déduisait "clé
// configurée" de `stripe.mode.available` — un état "etat_inconnu" (clé
// présente, préfixe non reconnu) était alors affiché EXACTEMENT comme
// "non_configure" (aucune clé). Les 4 tests ci-dessous couvrent les 4 états
// réels, désormais distincts dans le libellé "Mode" affiché.
describe("admin-settings.js — mode Stripe (4 états distincts, jamais fusionnés)", () => {
  function overviewWithStripe(stripeOverride) {
    return { ...OVERVIEW_PAYLOAD, stripe: { ...OVERVIEW_PAYLOAD.stripe, ...stripeOverride } };
  }

  it("mode TEST : badge 'TEST' + avertissement explicite 'aucun paiement réel'", async () => {
    await mount("/admin/settings", {
      overview: overviewWithStripe({ mode: { available: true, value: "test" }, configured: true }),
    });
    const stripeEl = document.getElementById("admin-settings-stripe");
    expect(stripeEl.textContent).toContain("TEST");
    expect(stripeEl.textContent).toMatch(/aucun paiement réel/);
    expect(stripeEl.textContent).toContain("Clés Stripe configurées");
    expect(stripeEl.textContent).toMatch(/Oui/);
  });

  it("mode PRODUCTION : badge 'PRODUCTION', aucun avertissement", async () => {
    await mount("/admin/settings", {
      overview: overviewWithStripe({ mode: { available: true, value: "production" }, configured: true }),
    });
    const stripeEl = document.getElementById("admin-settings-stripe");
    expect(stripeEl.textContent).toContain("PRODUCTION");
    expect(stripeEl.textContent).not.toMatch(/aucun paiement réel/);
  });

  it("mode NON CONFIGURÉ : badge explicite, 'Clés configurées' = Non", async () => {
    await mount("/admin/settings", {
      overview: overviewWithStripe({ mode: { available: true, value: "non_configure" }, configured: false }),
    });
    const stripeEl = document.getElementById("admin-settings-stripe");
    expect(stripeEl.textContent).toContain("NON CONFIGURÉ");
    expect(stripeEl.textContent).toMatch(/Non/);
  });

  it("mode ÉTAT INCONNU : jamais confondu avec NON CONFIGURÉ — 'Clés configurées' reste Oui", async () => {
    await mount("/admin/settings", {
      overview: overviewWithStripe({ mode: { available: true, value: "etat_inconnu" }, configured: true }),
    });
    const stripeEl = document.getElementById("admin-settings-stripe");
    expect(stripeEl.textContent).toContain("ÉTAT INCONNU");
    expect(stripeEl.textContent).not.toContain("NON CONFIGURÉ");
    expect(stripeEl.textContent).toMatch(/préfixe Stripe connu/);
    expect(stripeEl.textContent).toContain("Clés Stripe configurées");
  });
});

// Audit admin (2026-10-22) : la liste à plat des fournisseurs IA (nom/
// priorité/badge Actif-Secours) n'exposait elle-même aucune action — elle a
// été remplacée par un simple lien vers /admin/ia, où la gestion complète
// (CRUD/priorités/clés) vit réellement. `ai.provider_order` n'est plus
// renvoyé par le backend (voir settings_service.py::ai_config) : ce bloc
// vérifie que le frontend ne tente plus de le lire.
describe("admin-settings.js — section IA de Paramètres : lien vers /admin/ia au lieu de dupliquer la liste", () => {
  it("affiche un lien vers /admin/ia, jamais la liste à plat des fournisseurs", async () => {
    await mount("/admin/settings");
    const infoEl = document.getElementById("admin-settings-ai-info");
    const link = infoEl.querySelector("a[href='/admin/ia']");
    expect(link).not.toBeNull();
    // L'ancien rendu affichait un badge "Actif"/"Secours" par fournisseur :
    // plus aucune trace de cette liste à plat ici.
    expect(infoEl.querySelector(".admin-provider-list")).toBeNull();
  });

  it("ne lève aucune erreur même si le backend ne renvoie plus provider_order", async () => {
    await mount("/admin/settings");
    expect(document.getElementById("admin-global-error").hidden).toBe(true);
  });
});

// Audit admin (2026-10-22) : la carte "Espace disque utilisé" (pourcentage +
// barre de progression) dépendait de backups.disk_total_bytes, qui n'est
// plus jamais disponible (voir settings_service.py::backups_info et
// system_health_service.py::storage_info) — la branche qui calculait le
// pourcentage n'était donc plus jamais exécutée. Retirée proprement plutôt
// que recalculée : ce bloc vérifie qu'elle n'apparaît plus.
describe("admin-settings.js — carte 'Espace disque utilisé' retirée (structurellement morte)", () => {
  it("n'affiche plus de carte 'Espace disque utilisé' ni de barre de progression dans Sauvegardes", async () => {
    await mount("/admin/settings");
    const statsEl = document.getElementById("admin-settings-backups-stats");
    expect(statsEl.textContent).not.toMatch(/Espace disque utilisé/);
    expect(statsEl.querySelector(".admin-progress-bar")).toBeNull();
  });

  it("conserve la taille totale des sauvegardes (donnée réellement disponible)", async () => {
    await mount("/admin/settings");
    const statsEl = document.getElementById("admin-settings-backups-stats");
    expect(statsEl.textContent).toMatch(/Taille totale des sauvegardes/);
  });
});

// Audit admin (2026-10-22), point 1 (Paramètres) : le système de favoris
// (étoile par catégorie + filtre + localStorage) est entièrement supprimé —
// disproportionné pour seulement 4 catégories. La recherche texte reste
// seule. "IA & Clés API" est ouverte par défaut, les 3 autres repliées.
describe("admin-settings.js — suppression complète du système de favoris", () => {
  it("aucune étoile de favori, aucun bouton de filtre favoris, aucune clé localStorage dédiée", async () => {
    await mount("/admin/settings");
    expect(document.querySelector(".admin-fav-star")).toBeNull();
    expect(document.getElementById("admin-settings-fav-filter-btn")).toBeNull();
    expect(document.querySelector(".admin-settings-fav-filter")).toBeNull();
    const localStorageSpy = vi.spyOn(window.localStorage, "setItem");
    document.getElementById("admin-settings-search-input").value = "stripe";
    document.getElementById("admin-settings-search-input").dispatchEvent(new Event("input"));
    expect(localStorageSpy).not.toHaveBeenCalledWith(expect.stringContaining("favorites"), expect.anything());
  });

  it("la recherche texte reste fonctionnelle sans les favoris", async () => {
    await mount("/admin/settings");
    const searchInput = document.getElementById("admin-settings-search-input");
    searchInput.value = "stripe";
    searchInput.dispatchEvent(new Event("input"));
    const sections = [...document.querySelectorAll(".admin-collapse[data-collapse-id]")];
    const smtpSection = sections.find((s) => s.dataset.collapseId === "settings-smtp");
    const backupsSection = sections.find((s) => s.dataset.collapseId === "settings-backups");
    expect(smtpSection.hidden).toBe(false);
    expect(backupsSection.hidden).toBe(true);
  });

  it("répartition du repli par défaut : 'IA & Clés API' ouverte, les 3 autres catégories fermées", async () => {
    await mount("/admin/settings");
    const details = [...document.querySelectorAll(".admin-collapse[data-collapse-id]")];
    const byId = Object.fromEntries(details.map((d) => [d.dataset.collapseId, d]));
    expect(byId["settings-ai"].open).toBe(true);
    expect(byId["settings-smtp"].open).toBe(false);
    expect(byId["settings-backups"].open).toBe(false);
    expect(byId["settings-security"].open).toBe(false);
  });
});

// Audit admin (2026-10-22), point 2 (Paramètres) : Sécurité (5 cartes) +
// Logs (2 champs) fusionnés en UNE SEULE carte "Sécurité & Logs" avec 7
// lignes clé/valeur, sans sous-titres séparés. Toutes ces données restent en
// lecture seule (aucune route d'écriture — vérifié dans settings_service.py).
describe("admin-settings.js — fusion Sécurité (5 cartes) + Logs (2 champs) en 1 carte à 7 lignes", () => {
  it("une seule carte 'Sécurité & Logs' avec les 7 informations, sans sous-titres h3", async () => {
    await mount("/admin/settings");
    const securityEl = document.getElementById("admin-settings-security");
    const cards = securityEl.querySelectorAll(".admin-card");
    expect(cards.length).toBe(1);
    expect(securityEl.querySelector("h3")).toBeNull();
    const text = securityEl.textContent;
    expect(text).toContain("2FA administrateurs");
    expect(text).toContain("CSP");
    expect(text).toContain("Durée des sessions");
    expect(text).toContain("Tentatives de connexion");
    expect(text).toContain("HSTS");
    expect(text).toContain("Niveau de log");
    expect(text).toContain("Sentry");
    // Valeurs réelles toujours présentes (rien perdu dans la fusion).
    expect(text).toMatch(/0 \/ 10/);
    expect(text).toContain("INFO");
  });
});

// Audit admin (2026-10-22), point 3 (Paramètres) : Stripe (3 lignes) fusionné
// dans LA MÊME carte que SMTP plutôt que 2 sous-sections avec des titres h3
// séparés — les bandeaux d'avertissement critiques (mode TEST / état
// inconnu) restent clairement visibles, jamais noyés dans la fusion.
describe("admin-settings.js — fusion Stripe + SMTP dans la même carte, sans h3 séparés", () => {
  it("SMTP et Stripe sont dans la même carte 'Email & Paiements', sans sous-titres h3", async () => {
    await mount("/admin/settings");
    const integrationsEl = document.getElementById("admin-settings-integrations");
    const smtpBlock = document.getElementById("admin-settings-smtp");
    const stripeBlock = document.getElementById("admin-settings-stripe");
    expect(smtpBlock).not.toBeNull();
    expect(stripeBlock).not.toBeNull();
    const smtpCard = smtpBlock.closest(".admin-card");
    const stripeCard = stripeBlock.closest(".admin-card");
    expect(smtpCard).toBe(stripeCard);
    expect(smtpCard.querySelector("h3")).toBeNull();
    expect(integrationsEl.textContent).toContain("smtp-relay.brevo.com");
    expect(integrationsEl.textContent).toContain("TEST");
  });

  it("le bandeau d'avertissement mode TEST reste visible après la fusion", async () => {
    await mount("/admin/settings", {
      overview: {
        ...OVERVIEW_PAYLOAD,
        stripe: { ...OVERVIEW_PAYLOAD.stripe, mode: { available: true, value: "test" } },
      },
    });
    const warning = document.querySelector("#admin-settings-stripe .admin-form-hint--warning");
    expect(warning).not.toBeNull();
    expect(warning.textContent).toMatch(/aucun paiement réel/);
  });
});
