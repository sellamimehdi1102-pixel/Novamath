// admin-team-roles.js : chargement des comptes d'équipe assignables
// (support/moderator/admin/super_admin) — factorisé depuis admin-support.js
// et admin-support-ticket.js, qui dupliquaient exactement les mêmes 4
// requêtes en parallèle et la même fusion/déduplication par id.
//
// Audit admin (2026-10-20), point 4 : fetchTeamMembers() signale désormais
// explicitement un rôle en échec (failedRoles) et un rôle tronqué par
// page_size=100 (incompleteRoles, détecté via le vrai `total` renvoyé par
// l'API, jamais une heuristique) — plus aucun échec silencieux.
import { describe, it, expect, vi, afterEach } from "vitest";
import { TEAM_ROLES, fetchTeamMembers } from "../admin-team-roles.js";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-team-roles.js — TEAM_ROLES", () => {
  it("couvre exactement les 4 rôles d'équipe historiques, dans le même ordre", () => {
    expect(TEAM_ROLES).toEqual(["support", "moderator", "admin", "super_admin"]);
  });
});

describe("admin-team-roles.js — fetchTeamMembers", () => {
  it("interroge /api/admin/users une fois par rôle, avec page_size=100", async () => {
    const calls = [];
    global.fetch = vi.fn((url) => {
      calls.push(url);
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) });
    });
    await fetchTeamMembers();
    expect(calls).toEqual([
      "/api/admin/users?role=support&page_size=100",
      "/api/admin/users?role=moderator&page_size=100",
      "/api/admin/users?role=admin&page_size=100",
      "/api/admin/users?role=super_admin&page_size=100",
    ]);
  });

  it("fusionne et déduplique par id à travers les 4 rôles", async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes("role=support"))
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ items: [{ id: 1, name: "Alice" }], total: 1 }),
        });
      if (url.includes("role=admin&"))
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              items: [
                { id: 1, name: "Alice" },
                { id: 2, name: "Bob" },
              ],
              total: 2,
            }),
        });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) });
    });
    const { admins, failedRoles, incompleteRoles } = await fetchTeamMembers();
    expect(admins.size).toBe(2);
    expect(admins.get(1)).toBe("Alice");
    expect(admins.get(2)).toBe("Bob");
    expect(failedRoles).toEqual([]);
    expect(incompleteRoles).toEqual([]);
  });

  it("une réponse non-ok pour un rôle est signalée dans failedRoles, jamais silencieuse", async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes("role=moderator")) return Promise.resolve({ ok: false, status: 500 });
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [{ id: 9, name: "Support" }], total: 1 }),
      });
    });
    const { admins, failedRoles } = await fetchTeamMembers();
    expect(admins.get(9)).toBe("Support");
    expect(failedRoles).toEqual(["moderator"]);
  });

  it("un rôle dont le total dépasse page_size=100 est signalé dans incompleteRoles", async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes("role=admin&")) {
        const items = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, name: `Admin ${i + 1}` }));
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ items, total: 142 }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [], total: 0 }) });
    });
    const { incompleteRoles, admins } = await fetchTeamMembers();
    expect(incompleteRoles).toEqual(["admin"]);
    expect(admins.size).toBe(100);
  });

  it("une panne réseau (fetch rejeté) se propage — chaque appelant garde son propre repli", async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error("network down")));
    await expect(fetchTeamMembers()).rejects.toThrow("network down");
  });
});
