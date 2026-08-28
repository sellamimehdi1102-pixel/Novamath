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
    id: 1, created_at: "2026-07-29T08:00:00+00:00",
    admin: { id: 10, name: "Mehdi", role: "super_admin" },
    ip: "127.0.0.1", action: "update_provider", action_label: "Modification d'un fournisseur",
    provider: { id: 1, name: "Gemini Flash" },
    old_values: { priority: 0 }, new_values: { priority: 1 },
    result: "success", error_message: null,
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
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Mehdi", email: "a@b.c", role: "super_admin", avatar: null }) });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: NAV_WITH_JOURNAL }) });
    }
    if (fail.includes(url)) {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    }
    if (url === "/api/admin/journal/filters") return Promise.resolve({ ok: true, json: () => Promise.resolve(filters) });
    if (url.startsWith("/api/admin/journal/export.json")) return Promise.resolve({ ok: true, json: () => Promise.resolve([entry()]) });
    if (url.startsWith("/api/admin/journal")) return Promise.resolve({ ok: true, json: () => Promise.resolve(journal) });
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

  it("échec réseau -> message d'erreur, sans planter la page", async () => {
    await mount({ fail: ["/api/admin/journal?admin_user_id=&action=&date_from=&date_to=&page=1&page_size=25&provider_id=&result=&search="] });
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
    expect(fetchLog.some((u) => u.startsWith("/api/admin/journal?") && !u.includes("action=update_provider"))).toBe(true);
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
