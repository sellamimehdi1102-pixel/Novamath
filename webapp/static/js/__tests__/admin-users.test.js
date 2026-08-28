// ── admin-users.js : module "Utilisateurs" (/admin/users) — CRM en lecture
// seule (recherche, filtres, tri, pagination), branché via admin-shell.js.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_WITH_USERS = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "users", label: "Utilisateurs", icon: "👥", path: "/admin/users", implemented: true },
];

function makeUser(overrides = {}) {
  return {
    id: 1, name: "Alice Dupont", email: "alice@test.novamath.local", avatar: null,
    plan: "free", role: "user", account_status: "active",
    last_login_at: "2026-07-01T10:00:00+00:00", created_at: "2026-01-01T08:00:00+00:00",
    total_time_s: 3600,
    ...overrides,
  };
}

function snapshotFor(items, { page = 1, page_size = 25, total } = {}) {
  const t = total ?? items.length;
  return { items, page, page_size, total: t, total_pages: Math.max(1, Math.ceil(t / page_size)) };
}

let fetchCalls;

function fakeProfileTab(userId) {
  return {
    id: userId, avatar: null, pseudo: `user${userId}`, email: `user${userId}@test.novamath.local`,
    plan: { available: true, value: "free" }, role: { available: true, value: "user" },
    account_status: { available: true, value: "active" },
    created_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
    last_login_at: { available: true, value: "2026-07-01T10:00:00+00:00" },
    total_time_s: { available: true, value: 60 },
    recent_ip: { available: false, value: null, reason: "aucune IP" },
  };
}

function mockFetchWith(navModules, usersSnapshotFn) {
  fetchCalls = [];
  global.fetch = vi.fn((url) => {
    fetchCalls.push(url);
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "sellamimehdi1102@gmail.com", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: navModules }) });
    }
    const profileMatch = url.match(/^\/api\/admin\/users\/(\d+)\/profile$/);
    if (profileMatch) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(fakeProfileTab(Number(profileMatch[1]))) });
    }
    if (url.startsWith("/api/admin/users?")) {
      const snap = usersSnapshotFn(new URL(url, "http://localhost"));
      return Promise.resolve({ ok: true, json: () => Promise.resolve(snap) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(path, navModules, usersSnapshotFn) {
  window.history.pushState({}, "", path);
  document.body.innerHTML = loadPageBody("admin.html");
  mockFetchWith(navModules, usersSnapshotFn);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-users.js — chargement et rendu de base", () => {
  it("affiche les lignes renvoyées par /api/admin/users avec toutes les colonnes attendues", async () => {
    const users = [makeUser()];
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor(users));

    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Utilisateurs");
    const rows = document.querySelectorAll(".admin-users-row");
    expect(rows.length).toBe(1);
    const rowText = rows[0].textContent;
    expect(rowText).toContain("Alice Dupont");
    expect(rowText).toContain("alice@test.novamath.local");
    expect(rowText).toContain("Gratuit");
    expect(rowText).toContain("Utilisateur");
  });

  it("état vide : aucune ligne, message explicite, jamais une table vide silencieuse", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([]));
    expect(document.querySelectorAll(".admin-users-row").length).toBe(0);
    const empty = document.getElementById("admin-users-empty");
    expect(empty.hidden).toBe(false);
    expect(empty.textContent).toBe("Aucune donnée disponible");
  });

  it("gestion des erreurs : bannière visible si l'API échoue, jamais un plantage silencieux", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => { throw new Error("boom"); });
    // fetch lève -> catch côté admin-users.js
    const errorEl = document.getElementById("admin-global-error");
    expect(errorEl.hidden).toBe(false);
  });
});

describe("admin-users.js — recherche instantanée", () => {
  it("la saisie déclenche un fetch avec le paramètre search (debounce)", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser()]);
    });

    const input = document.getElementById("admin-users-search-input");
    input.value = "alice";
    input.dispatchEvent(new Event("input"));

    await new Promise((r) => setTimeout(r, 350));
    await flushPromises();

    expect(lastParams.get("search")).toBe("alice");
  });
});

describe("admin-users.js — filtres", () => {
  it("changer le filtre abonnement relance la requête avec le bon paramètre et remet la page à 1", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser({ plan: "ultra" })]);
    });

    document.getElementById("admin-users-filter-plan").value = "ultra";
    document.getElementById("admin-users-filter-plan").dispatchEvent(new Event("change"));
    await flushPromises();

    expect(lastParams.get("plan")).toBe("ultra");
    expect(lastParams.get("page")).toBe("1");
  });

  // Chantier Administrateur "Utilisateurs" (Phase 2) : le filtre expose
  // désormais les 3 valeurs réelles de account_status, plus de bucket
  // générique "suspended" qui les confondait toutes les deux.
  it("changer le filtre statut envoie la valeur réelle account_status=pending_parental_consent", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser({ account_status: "pending_parental_consent" })]);
    });

    document.getElementById("admin-users-filter-status").value = "pending_parental_consent";
    document.getElementById("admin-users-filter-status").dispatchEvent(new Event("change"));
    await flushPromises();

    expect(lastParams.get("account_status")).toBe("pending_parental_consent");
  });

  it("changer le filtre statut envoie account_status=parental_consent_refused", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser({ account_status: "parental_consent_refused" })]);
    });

    document.getElementById("admin-users-filter-status").value = "parental_consent_refused";
    document.getElementById("admin-users-filter-status").dispatchEvent(new Event("change"));
    await flushPromises();

    expect(lastParams.get("account_status")).toBe("parental_consent_refused");
  });

  it("l'ancienne option 'Suspendu' n'existe plus dans le filtre statut", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser()]));
    const options = [...document.getElementById("admin-users-filter-status").options].map((o) => o.value);
    expect(options).toEqual(["", "active", "pending_parental_consent", "parental_consent_refused"]);
  });

  it("changer le filtre paiement envoie payment_status=failed et remet la page à 1", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser({ account_status: "active" })]);
    });

    document.getElementById("admin-users-filter-payment").value = "failed";
    document.getElementById("admin-users-filter-payment").dispatchEvent(new Event("change"));
    await flushPromises();

    expect(lastParams.get("payment_status")).toBe("failed");
    expect(lastParams.get("page")).toBe("1");
  });

  it("recherche + statut + paiement peuvent être combinés dans la même requête", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser()]);
    });

    document.getElementById("admin-users-search-input").value = "alice";
    document.getElementById("admin-users-search-input").dispatchEvent(new Event("input"));
    document.getElementById("admin-users-filter-status").value = "active";
    document.getElementById("admin-users-filter-status").dispatchEvent(new Event("change"));
    document.getElementById("admin-users-filter-payment").value = "failed";
    document.getElementById("admin-users-filter-payment").dispatchEvent(new Event("change"));
    await new Promise((r) => setTimeout(r, 350));
    await flushPromises();

    expect(lastParams.get("search")).toBe("alice");
    expect(lastParams.get("account_status")).toBe("active");
    expect(lastParams.get("payment_status")).toBe("failed");
  });
});

describe("admin-users.js — badge de statut dans le tableau", () => {
  it("affiche le badge 'Actif' pour un compte actif", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser({ account_status: "active" })]));
    const row = document.querySelector(".admin-users-row");
    const dot = row.querySelector(".admin-status-dot--ok");
    expect(dot).not.toBeNull();
    expect(dot.textContent).toBe("Actif");
  });

  it("affiche le badge 'En attente de consentement' avec le ton avertissement", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser({ account_status: "pending_parental_consent" })]));
    const row = document.querySelector(".admin-users-row");
    const dot = row.querySelector(".admin-status-dot--warning");
    expect(dot).not.toBeNull();
    expect(dot.textContent).toBe("En attente de consentement");
  });

  it("affiche le badge 'Consentement refusé' avec le ton danger", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser({ account_status: "parental_consent_refused" })]));
    const row = document.querySelector(".admin-users-row");
    const dot = row.querySelector(".admin-status-dot--down");
    expect(dot).not.toBeNull();
    expect(dot.textContent).toBe("Consentement refusé");
  });

  it("la colonne Statut apparaît entre Abonnement et Rôle, les 8 colonnes existantes restent présentes", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser()]));
    const headers = [...document.querySelectorAll(".admin-users-th")].map((th) => th.textContent);
    expect(headers).toEqual([
      "Avatar", "Nom", "Email", "Abonnement", "Statut", "Rôle",
      "Dernière connexion", "Date de création", "Temps passé",
    ]);
  });
});

describe("admin-users.js — tri par colonne", () => {
  it("cliquer sur l'en-tête 'Nom' trie ascendant puis descendant au second clic", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      return snapshotFor([makeUser()]);
    });

    const nameHeader = [...document.querySelectorAll(".admin-users-th")].find((th) => th.textContent.startsWith("Nom"));
    nameHeader.click();
    await flushPromises();
    expect(lastParams.get("sort_by")).toBe("pseudo");
    expect(lastParams.get("sort_dir")).toBe("asc");

    nameHeader.click();
    await flushPromises();
    expect(lastParams.get("sort_dir")).toBe("desc");
  });
});

describe("admin-users.js — pagination", () => {
  it("affiche les infos de pagination et navigue à la page suivante sans doublon de requête", async () => {
    let lastParams = null;
    await mount("/admin/users", NAV_WITH_USERS, (url) => {
      lastParams = url.searchParams;
      const page = Number(url.searchParams.get("page"));
      return snapshotFor([makeUser({ id: page })], { page, page_size: 1, total: 3 });
    });

    const info = document.querySelector(".admin-users-pagination-info");
    expect(info.textContent).toContain("Page 1 / 3");

    const nextBtn = [...document.querySelectorAll(".admin-users-page-btn")].find((b) => b.textContent === "›");
    nextBtn.click();
    await flushPromises();

    expect(lastParams.get("page")).toBe("2");
    expect(document.querySelector(".admin-users-pagination-info").textContent).toContain("Page 2 / 3");
  });

  it("le bouton précédent est désactivé sur la première page, suivant désactivé sur la dernière", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser()], { page: 1, page_size: 1, total: 1 }));
    const [prevBtn, nextBtn] = document.querySelectorAll(".admin-users-page-btn");
    expect(prevBtn.disabled).toBe(true);
    expect(nextBtn.disabled).toBe(true);
  });
});

describe("admin-users.js — navigation vers le profil (/admin/users/:id)", () => {
  it("cliquer sur une ligne navigue vers /admin/users/:id via pushState (jamais location.href)", async () => {
    await mount("/admin/users", NAV_WITH_USERS, () => snapshotFor([makeUser({ id: 42 })]));
    const pushStateSpy = vi.spyOn(window.history, "pushState");

    document.querySelector(".admin-users-row").click();
    await flushPromises();

    expect(pushStateSpy).toHaveBeenCalledWith(expect.anything(), "", "/admin/users/42");
    expect(window.location.pathname).toBe("/admin/users/42");
    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Profil utilisateur");
    // La fiche complète elle-même (onglets, contenu) est testée dans
    // admin-user-profile.test.js — ce test-ci ne vérifie que le routage.
    await flushPromises();
    expect(document.getElementById("admin-user-profile-tabs")).not.toBeNull();
    expect(document.body.textContent).not.toMatch(/404/);
  });

  it("charger directement /admin/users/42 (rechargement de page) affiche aussi la fiche, jamais 404", async () => {
    await mount("/admin/users/42", NAV_WITH_USERS, () => snapshotFor([]));
    await flushPromises();
    expect(document.getElementById("admin-user-profile-tabs")).not.toBeNull();
    expect(document.body.textContent).not.toMatch(/404/);
  });
});
