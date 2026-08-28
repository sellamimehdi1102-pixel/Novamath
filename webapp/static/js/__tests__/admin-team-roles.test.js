// admin-team-roles.js : chargement des comptes d'équipe assignables
// (support/moderator/admin/super_admin) — factorisé depuis admin-support.js
// et admin-support-ticket.js, qui dupliquaient exactement les mêmes 4
// requêtes en parallèle et la même fusion/déduplication par id.
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
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) });
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
      if (url.includes("role=support")) return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ id: 1, name: "Alice" }] }) });
      if (url.includes("role=admin&")) return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ id: 1, name: "Alice" }, { id: 2, name: "Bob" }] }) });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) });
    });
    const admins = await fetchTeamMembers();
    expect(admins.size).toBe(2);
    expect(admins.get(1)).toBe("Alice");
    expect(admins.get(2)).toBe("Bob");
  });

  it("une réponse non-ok pour un rôle est traitée comme une liste vide pour ce rôle (pas d'exception)", async () => {
    global.fetch = vi.fn((url) => {
      if (url.includes("role=moderator")) return Promise.resolve({ ok: false, status: 500 });
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [{ id: 9, name: "Support" }] }) });
    });
    const admins = await fetchTeamMembers();
    expect(admins.get(9)).toBe("Support");
  });

  it("une panne réseau (fetch rejeté) se propage — chaque appelant garde son propre repli", async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error("network down")));
    await expect(fetchTeamMembers()).rejects.toThrow("network down");
  });
});
