// ── admin-journal.js : module "Journal" (/admin/journal) — historique en
// lecture seule des actions du module Administration IA (recherche, filtres,
// pagination, export CSV/JSON, détail anciennes/nouvelles valeurs).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_JOURNAL = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "journal", label: "Journal", icon: "📜", path: "/admin/journal", implemented: true },
];

function entry(overrides = {}) {
  return {
    id: 1,
    created_at: "2026-07-29T08:00:00+00:00",
    admin: { id: 10, name: "Mehdi", role: "super_admin" },
    ip: "127.0.0.1",
    action: "update_provider",
    action_label: "Modification d'un fournisseur",
    provider: { id: 1, name: "Gemini Flash" },
    old_values: { priority: 0 },
    new_values: { priority: 1 },
    result: "success",
    error_message: null,
    ...overrides,
  };
}

const FILTERS_PAYLOAD = {
  admins: [{ id: 10, name: "Mehdi" }],
  providers: [{ id: 1, name: "Gemini Flash" }],
  actions: [{ value: "update_provider", label: "Modification d'un fournisseur" }],
};

function journalPayload(overrides = {}) {
  return { items: [entry()], page: 1, page_size: 25, total: 1, total_pages: 1, ...overrides };
}

let fetchLog;

function mockFetchWith({ journal = journalPayload(), filters = FILTERS_PAYLOAD, fail = [] } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url) => {
    fetchLog.push(url);
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_JOURNAL }) });
    }
    if (fail.includes(url)) {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    }
    if (url === "/api/admin/journal/filters")
      return Promise.resolve({ ok: true, json: () => Promise.resolve(filters) });
    if (url.startsWith("/api/admin/journal/export.json"))
      return Promise.resolve({ ok: true, json: () => Promise.resolve([entry()]) });
    if (url.startsWith("/api/admin/journal"))
      return Promise.resolve({ ok: true, json: () => Promise.resolve(journal) });
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(options) {
  window.history.pushState({}, "", "/admin/journal");
  document.body.innerHTML = loadPageBody("admin.html");
  mockFetchWith(options);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-journal.js — chargement et rendu", () => {
  it("affiche les colonnes attendues avec les données réelles d'un événement", async () => {
    await mount();
    const tbody = document.getElementById("admin-journal-tbody");
    expect(tbody.textContent).toContain("Mehdi");
    expect(tbody.textContent).toContain("super_admin");
    expect(tbody.textContent).toContain("127.0.0.1");
    expect(tbody.textContent).toContain("Modification d'un fournisseur");
    expect(tbody.textContent).toContain("Gemini Flash");
    expect(tbody.textContent).toContain("Succès");
  });

  it("aucun événement -> état vide", async () => {
    await mount({ journal: journalPayload({ items: [], total: 0, total_pages: 1 }) });
    expect(document.getElementById("admin-journal-empty").hidden).toBe(false);
  });

  // Audit utilité/densité (2026-10-22) : "Aucune donnée disponible" était
  // trompeur (laisse croire à une absence de données plutôt qu'à des
  // filtres trop restrictifs).
  it("état vide : le texte contextuel remplace 'Aucune donnée disponible'", async () => {
    await mount({ journal: journalPayload({ items: [], total: 0, total_pages: 1 }) });
    expect(document.getElementById("admin-journal-empty").textContent).toBe(
      "Aucun événement ne correspond à ces critères.",
    );
  });

  // Renommage (chantier de simplification du panneau admin) : "Journal
  // d'activité IA" ne reflétait plus que les actions du module IA, alors que
  // ce journal couvre aussi Abonnements/Analytics/Sauvegardes/Finance (voir
  // admin_ai_log_service.ACTIONS). Le nom de navigation ("Journal", voir
  // admin_nav_service.py) était déjà générique et reste inchangé.
  it("le titre de la page est 'Journal d'administration' (plus 'Journal d'activité IA')", async () => {
    await mount();
    const heading = document.querySelector("#admin-content-body h1");
    expect(heading.textContent).toBe("Journal d'administration");
  });

  it("échec réseau -> message d'erreur, sans planter la page", async () => {
    await mount({
      fail: [
        "/api/admin/journal?admin_user_id=&action=&date_from=&date_to=&page=1&page_size=25&provider_id=&result=&search=",
      ],
    });
    // Le message générique s'affiche dès que le fetch échoue (peu importe la query exacte construite).
    await flushPromises();
    expect(document.getElementById("admin-global-error")).not.toBeNull();
  });
});

describe("admin-journal.js — filtres et recherche", () => {
  it("peuple les filtres administrateur/fournisseur/action depuis /api/admin/journal/filters", async () => {
    await mount();
    const adminSelect = document.getElementById("admin-journal-filter-admin");
    const providerSelect = document.getElementById("admin-journal-filter-provider");
    const actionSelect = document.getElementById("admin-journal-filter-action");
    expect([...adminSelect.options].some((o) => o.textContent === "Mehdi")).toBe(true);
    expect([...providerSelect.options].some((o) => o.textContent === "Gemini Flash")).toBe(true);
    expect([...actionSelect.options].some((o) => o.textContent === "Modification d'un fournisseur")).toBe(true);
  });

  it("changer le filtre action relance une requête filtrée et réinitialise la page", async () => {
    await mount();
    fetchLog = [];
    document.getElementById("admin-journal-filter-action").value = "update_provider";
    document.getElementById("admin-journal-filter-action").dispatchEvent(new Event("change"));
    await flushPromises();
    expect(fetchLog.some((u) => u.includes("action=update_provider") && u.includes("page=1"))).toBe(true);
  });

  it("changer les dates depuis/jusqu'au relance une requête avec date_from/date_to", async () => {
    await mount();
    fetchLog = [];
    const from = document.getElementById("admin-journal-filter-date-from");
    from.value = "2026-07-01";
    from.dispatchEvent(new Event("change"));
    await flushPromises();
    expect(fetchLog.some((u) => u.includes("date_from=2026-07-01"))).toBe(true);
  });

  it("la recherche texte est débouncée puis envoyée en query", async () => {
    await mount();
    fetchLog = [];
    const input = document.getElementById("admin-journal-search-input");
    input.value = "Gemini";
    input.dispatchEvent(new Event("input"));

    await new Promise((r) => setTimeout(r, 350));
    await flushPromises();

    expect(fetchLog.some((u) => u.includes("search=Gemini"))).toBe(true);
  });
});

// Audit admin (2026-10-20), point 4 : un échec de /api/admin/journal/filters
// doit être signalé explicitement (jamais un catch vide silencieux), tout
// en laissant la liste principale du journal consultable.
describe("admin-journal.js — échec des filtres (jamais silencieux)", () => {
  it("affiche un avertissement explicite et garde la liste principale consultable", async () => {
    await mount({ fail: ["/api/admin/journal/filters"] });
    const warningEl = document.getElementById("admin-journal-filters-warning");
    expect(warningEl.hidden).toBe(false);
    expect(warningEl.textContent).toMatch(/filtres.*n'ont pas pu être chargés/i);
    // La table principale reste chargée malgré l'échec des filtres.
    expect(document.getElementById("admin-journal-tbody").textContent).toContain("Mehdi");
  });

  it("le bouton Réessayer relance le chargement des filtres et masque l'avertissement en cas de succès", async () => {
    let shouldFail = true;
    global.fetch = vi.fn((url) => {
      if (url === "/api/admin/me") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }),
        });
      }
      if (url === "/api/admin/nav") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_JOURNAL }) });
      }
      if (url === "/api/admin/journal/filters") {
        if (shouldFail)
          return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
        return Promise.resolve({ ok: true, json: () => Promise.resolve(FILTERS_PAYLOAD) });
      }
      if (url.startsWith("/api/admin/journal")) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(journalPayload()) });
      }
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
    });
    window.history.pushState({}, "", "/admin/journal");
    document.body.innerHTML = loadPageBody("admin.html");
    vi.resetModules();
    mockLoadDashboard.mockClear();
    const { initAdminShell } = await import("../admin-shell.js");
    await initAdminShell();
    await flushPromises();

    const warningEl = document.getElementById("admin-journal-filters-warning");
    expect(warningEl.hidden).toBe(false);

    shouldFail = false;
    document.getElementById("admin-journal-filters-retry").click();
    await flushPromises();

    expect(warningEl.hidden).toBe(true);
    const adminSelect = document.getElementById("admin-journal-filter-admin");
    expect([...adminSelect.options].some((o) => o.textContent === "Mehdi")).toBe(true);
  });
});

describe("admin-journal.js — pagination", () => {
  it("affiche le total et désactive 'précédent' sur la première page", async () => {
    await mount({ journal: journalPayload({ total: 40, total_pages: 2 }) });
    const pagination = document.getElementById("admin-journal-pagination");
    expect(pagination.textContent).toContain("Page 1 / 2");
    expect(pagination.textContent).toContain("40");
    expect(pagination.querySelectorAll("button")[0].disabled).toBe(true);
  });

  it("clic sur page suivante relance une requête avec page=2", async () => {
    await mount({ journal: journalPayload({ total: 40, total_pages: 2 }) });
    fetchLog = [];
    const nextBtn = document.getElementById("admin-journal-pagination").querySelectorAll("button")[1];
    nextBtn.click();
    await flushPromises();
    expect(fetchLog.some((u) => u.includes("page=2"))).toBe(true);
  });
});

describe("admin-journal.js — détail d'un événement", () => {
  it("cliquer sur une ligne ouvre la modale avec anciennes/nouvelles valeurs", async () => {
    await mount();
    document.querySelector("#admin-journal-tbody tr.admin-users-row").click();
    await flushPromises();
    const modal = document.getElementById("admin-journal-detail-modal");
    expect(modal.hidden).toBe(false);
    expect(modal.textContent).toContain('"priority": 0');
    expect(modal.textContent).toContain('"priority": 1');
  });
});

describe("admin-journal.js — export", () => {
  it("bouton Exporter CSV redirige vers /api/admin/journal/export.csv avec les filtres courants", async () => {
    await mount();
    const originalLocation = window.location;
    const fakeLocation = { ...originalLocation, href: "" };
    Object.defineProperty(window, "location", { value: fakeLocation, writable: true, configurable: true });

    document.getElementById("admin-journal-export-csv").click();
    expect(fakeLocation.href).toContain("/api/admin/journal/export.csv");

    Object.defineProperty(window, "location", { value: originalLocation, writable: true, configurable: true });
  });

  it("bouton Exporter JSON déclenche un appel à /api/admin/journal/export.json", async () => {
    await mount();
    fetchLog = [];
    const createObjectURL = vi.fn(() => "blob:fake");
    const revokeObjectURL = vi.fn();
    global.URL.createObjectURL = createObjectURL;
    global.URL.revokeObjectURL = revokeObjectURL;
    document.getElementById("admin-journal-export-json").click();
    await flushPromises();
    expect(fetchLog.some((u) => u.startsWith("/api/admin/journal/export.json"))).toBe(true);
    expect(createObjectURL).toHaveBeenCalled();
  });

  // Renommage du module (plus seulement "IA") : le fichier téléchargé ne doit
  // plus porter l'ancien nom "journal-ia.json".
  it("le fichier JSON téléchargé s'appelle 'journal-admin.json' (plus 'journal-ia.json')", async () => {
    await mount();
    fetchLog = [];
    global.URL.createObjectURL = vi.fn(() => "blob:fake");
    global.URL.revokeObjectURL = vi.fn();
    const realCreateElement = document.createElement.bind(document);
    let anchor;
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag) => {
      const node = realCreateElement(tag);
      if (tag === "a") anchor = node;
      return node;
    });

    document.getElementById("admin-journal-export-json").click();
    await flushPromises();

    expect(anchor.download).toBe("journal-admin.json");
    createElementSpy.mockRestore();
  });

  // Chantier de simplification (audit utilité/densité, 2026-10-22) : les 2
  // boutons "Exporter CSV"/"Exporter JSON" sont fusionnés en un seul contrôle
  // (menu déroulant) — ce bloc vérifie le comportement du menu lui-même, les
  // 2 tests ci-dessus vérifient déjà que les 2 mécanismes d'export marchent
  // toujours (ils n'ont pas besoin que le menu soit ouvert pour cliquer).
  describe("menu déroulant unique", () => {
    it("le menu est fermé par défaut et s'ouvre au clic sur 'Exporter'", async () => {
      await mount();
      const menu = document.getElementById("admin-journal-export-menu");
      expect(menu.hidden).toBe(true);

      document.getElementById("admin-journal-export-toggle").click();
      expect(menu.hidden).toBe(false);
    });

    it("cliquer en dehors du menu le referme", async () => {
      await mount();
      const menu = document.getElementById("admin-journal-export-menu");
      document.getElementById("admin-journal-export-toggle").click();
      expect(menu.hidden).toBe(false);

      document.body.click();
      expect(menu.hidden).toBe(true);
    });

    it("le menu contient toujours les 2 options CSV et JSON", async () => {
      await mount();
      document.getElementById("admin-journal-export-toggle").click();
      const menu = document.getElementById("admin-journal-export-menu");
      expect(menu.textContent).toContain("CSV");
      expect(menu.textContent).toContain("JSON");
      expect(document.querySelectorAll("#admin-journal-export-menu button").length).toBe(2);
    });
  });
});

describe("admin-journal.js — regroupement par jour", () => {
  it("insère un en-tête de section par date distincte, dans l'ordre des lignes", async () => {
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const items = [
      entry({ id: 1, created_at: today.toISOString() }),
      entry({ id: 2, created_at: today.toISOString() }),
      entry({ id: 3, created_at: yesterday.toISOString() }),
    ];
    await mount({ journal: journalPayload({ items, total: 3, total_pages: 1 }) });

    const tbody = document.getElementById("admin-journal-tbody");
    const dayHeaders = tbody.querySelectorAll(".admin-journal-day-row");
    expect(dayHeaders.length).toBe(2);
    expect(dayHeaders[0].textContent).toContain("Aujourd'hui");
    expect(dayHeaders[1].textContent).toContain("Hier");

    const dataRows = tbody.querySelectorAll("tr.admin-users-row");
    expect(dataRows.length).toBe(3);
  });
});

describe("admin-journal.js — badges par type d'action", () => {
  it("affiche un badge coloré distinct selon la famille de l'action", async () => {
    const items = [
      entry({ id: 1, action: "create_provider", action_label: "Création d'un fournisseur" }),
      entry({ id: 2, action: "delete_provider", action_label: "Suppression d'un fournisseur" }),
    ];
    await mount({ journal: journalPayload({ items, total: 2, total_pages: 1 }) });

    const tbody = document.getElementById("admin-journal-tbody");
    expect(tbody.querySelector(".admin-badge--premium")).not.toBeNull();
    expect(tbody.querySelector(".admin-badge--error")).not.toBeNull();
    expect(tbody.textContent).toContain("Création");
    expect(tbody.textContent).toContain("Suppression");
  });
});

describe("admin-journal.js — chips de filtres actifs", () => {
  it("affiche un chip par filtre actif et un bouton de réinitialisation globale", async () => {
    await mount();
    document.getElementById("admin-journal-filter-action").value = "update_provider";
    document.getElementById("admin-journal-filter-action").dispatchEvent(new Event("change"));
    await flushPromises();

    const chipsEl = document.getElementById("admin-journal-filter-chips");
    expect(chipsEl.hidden).toBe(false);
    expect(chipsEl.querySelectorAll(".admin-filter-chip").length).toBe(1);
    expect(chipsEl.textContent).toContain("Modification d'un fournisseur");
    expect(chipsEl.querySelector(".admin-filter-chips-reset")).not.toBeNull();
  });

  it("retirer un chip individuel réinitialise ce filtre et relance une requête", async () => {
    await mount();
    document.getElementById("admin-journal-filter-action").value = "update_provider";
    document.getElementById("admin-journal-filter-action").dispatchEvent(new Event("change"));
    await flushPromises();

    fetchLog = [];
    document.querySelector("#admin-journal-filter-chips .admin-filter-chip-remove").click();
    await flushPromises();

    expect(document.getElementById("admin-journal-filter-action").value).toBe("");
    expect(fetchLog.some((u) => u.startsWith("/api/admin/journal?") && !u.includes("action=update_provider"))).toBe(
      true,
    );
    expect(document.getElementById("admin-journal-filter-chips").hidden).toBe(true);
  });

  it("le bouton de réinitialisation globale efface tous les filtres actifs", async () => {
    await mount();
    document.getElementById("admin-journal-filter-action").value = "update_provider";
    document.getElementById("admin-journal-filter-action").dispatchEvent(new Event("change"));
    const dateFrom = document.getElementById("admin-journal-filter-date-from");
    dateFrom.value = "2026-07-01";
    dateFrom.dispatchEvent(new Event("change"));
    await flushPromises();

    document.querySelector("#admin-journal-filter-chips .admin-filter-chips-reset").click();
    await flushPromises();

    expect(document.getElementById("admin-journal-filter-action").value).toBe("");
    expect(document.getElementById("admin-journal-filter-date-from").value).toBe("");
    expect(document.getElementById("admin-journal-filter-chips").hidden).toBe(true);
  });
});
