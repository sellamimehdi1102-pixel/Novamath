// ── admin-shell.js : sidebar + header + navigation interne du shell Admin ──
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockLoadDashboard = vi.fn().mockResolvedValue(undefined);
vi.mock("../admin-dashboard.js", () => ({ loadDashboard: mockLoadDashboard }));

const NAV_ALL = [
  { id: "dashboard", label: "Dashboard", icon: "🏠", path: "/admin", implemented: true },
  { id: "users", label: "Utilisateurs", icon: "👥", path: "/admin/users", implemented: false },
  { id: "ai", label: "IA", icon: "🤖", path: "/admin/ia", implemented: false },
  { id: "analytics", label: "Analytics", icon: "📊", path: "/admin/analytics", implemented: true },
  { id: "support", label: "Support", icon: "🛠", path: "/admin/support", implemented: true },
  { id: "settings", label: "Paramètres", icon: "⚙", path: "/admin/settings", implemented: true },
  { id: "journal", label: "Journal", icon: "📜", path: "/admin/journal", implemented: false },
  // Module fictif, absent de admin-shell.js (aucune branche ne le reconnaît) —
  // tous les modules RÉELS sont désormais implémentés (voir admin_nav_service.py) ;
  // cette entrée sert uniquement à exercer le mécanisme générique "module non
  // développé" (placeholder "disponible prochainement"), sans dépendre d'un
  // vrai module qui finirait, lui aussi, par être développé un jour.
  { id: "reports", label: "Rapports", icon: "📈", path: "/admin/reports", implemented: false },
];

const NAV_SUPPORT_ONLY = NAV_ALL.filter((m) =>
  ["dashboard", "users", "analytics", "support"].includes(m.id),
);

function mockFetchWith(navModules) {
  global.fetch = vi.fn((url) => {
    if (url === "/api/admin/me") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ name: "Mehdi", email: "sellamimehdi1102@gmail.com", role: "super_admin", avatar: null }),
      });
    }
    if (url === "/api/admin/nav") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ modules: navModules }) });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "not found" }) });
  });
}

async function mount(path, navModules) {
  window.history.pushState({}, "", path);
  document.body.innerHTML = loadPageBody("admin.html");
  mockFetchWith(navModules);
  vi.resetModules();
  mockLoadDashboard.mockClear();
  const { initAdminShell } = await import("../admin-shell.js");
  await initAdminShell();
  await flushPromises();
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-shell.js — construction du menu selon les permissions reçues du backend", () => {
  it("n'affiche que les modules renvoyés par /api/admin/nav (SUPPORT)", async () => {
    await mount("/admin", NAV_SUPPORT_ONLY);
    const links = [...document.querySelectorAll(".admin-sidebar-link")];
    expect(links.map((l) => l.dataset.path)).toEqual([
      "/admin", "/admin/users", "/admin/analytics", "/admin/support",
    ]);
    // Jamais "Paramètres"/"IA"/"Journal" dans le DOM : le frontend n'a reçu
    // aucune information sur ces modules, il ne peut donc pas les afficher.
    expect(document.body.textContent).not.toContain("Paramètres");
    expect(document.body.textContent).not.toContain("Journal");
  });

  it("affiche les 8 modules pour un rôle qui les voit tous (SUPER_ADMIN)", async () => {
    await mount("/admin", NAV_ALL);
    const links = document.querySelectorAll(".admin-sidebar-link");
    expect(links.length).toBe(8);
  });
});

describe("admin-shell.js — navigation interne (sans rechargement de page)", () => {
  it("affiche le Dashboard (module implémenté) et appelle loadDashboard()", async () => {
    await mount("/admin", NAV_ALL);
    expect(mockLoadDashboard).toHaveBeenCalledTimes(1);
    expect(document.getElementById("admin-cards")).not.toBeNull();
    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Dashboard");
  });

  it("un clic sur un lien du menu change le contenu SANS recharger la page (pushState, pas location.href)", async () => {
    await mount("/admin", NAV_ALL);
    const pushStateSpy = vi.spyOn(window.history, "pushState");

    // Tous les modules RÉELS sont désormais implémentés (voir
    // admin-users.test.js/admin-support.test.js/admin-settings.test.js/
    // admin-analytics.test.js pour leur propre comportement) — ce test
    // générique utilise le module fictif "reports" (voir NAV_ALL) pour
    // vérifier le mécanisme de routage lui-même, indépendamment de tout
    // module réel qui finirait par être développé.
    document.querySelector('.admin-sidebar-link[data-path="/admin/reports"]').click();
    await flushPromises();

    expect(pushStateSpy).toHaveBeenCalledWith(expect.anything(), "", "/admin/reports");
    expect(window.location.pathname).toBe("/admin/reports");
    expect(document.querySelector(".admin-breadcrumb-item--current").textContent).toBe("Rapports");
    expect(document.getElementById("admin-content-body").textContent).toContain(
      "Cette fonctionnalité sera disponible prochainement.",
    );
    // Aucune trace de 404 : le module s'affiche normalement, juste non développé.
    expect(document.body.textContent).not.toMatch(/404/);
  });

  it("marque le bon lien actif après navigation", async () => {
    await mount("/admin", NAV_ALL);
    document.querySelector('.admin-sidebar-link[data-path="/admin/reports"]').click();
    await flushPromises();
    const active = document.querySelector(".admin-sidebar-link.is-active");
    expect(active.dataset.path).toBe("/admin/reports");
  });

  it("affiche un module non implémenté différent avec le bon libellé (Rapports)", async () => {
    await mount("/admin", NAV_ALL);
    document.querySelector('.admin-sidebar-link[data-path="/admin/reports"]').click();
    await flushPromises();
    expect(document.getElementById("admin-content-body").textContent).toContain("Rapports");
    expect(document.getElementById("admin-content-body").textContent).toContain(
      "Cette fonctionnalité sera disponible prochainement.",
    );
  });

  it("répond au bouton précédent du navigateur (popstate) sans nouvelle requête pushState", async () => {
    await mount("/admin", NAV_ALL);
    document.querySelector('.admin-sidebar-link[data-path="/admin/journal"]').click();
    await flushPromises();

    // Simule un retour navigateur vers /admin (popstate), comme après pushState + back().
    window.history.pushState({}, "", "/admin");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await flushPromises();

    expect(document.getElementById("admin-cards")).not.toBeNull();
    expect(document.querySelector(".admin-sidebar-link.is-active").dataset.path).toBe("/admin");
  });

  it("un chemin initial correspondant à un module inconnu du menu ne casse rien (aucun rendu, aucune exception)", async () => {
    await expect(mount("/admin/chemin-jamais-declare", NAV_ALL)).resolves.not.toThrow();
  });
});

describe("admin-shell.js — tiroir mobile", () => {
  it("ouvre/ferme le tiroir sidebar au clic sur le déclencheur/l'overlay", async () => {
    await mount("/admin", NAV_ALL);
    document.getElementById("admin-sidebar-toggle").click();
    expect(document.getElementById("admin-sidebar").classList.contains("is-open")).toBe(true);
    expect(document.getElementById("admin-sidebar-overlay").hidden).toBe(false);

    document.getElementById("admin-sidebar-overlay").click();
    expect(document.getElementById("admin-sidebar").classList.contains("is-open")).toBe(false);
  });
});
