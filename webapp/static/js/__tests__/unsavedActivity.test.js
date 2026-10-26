// ── unsavedActivity.js : registre générique de détection d'activité non ────
// sauvegardée (né du besoin d'analyticsBeacon.js de ne jamais recharger la
// page sans prévenir si cela ferait perdre un brouillon en cours). Module
// pur, sans DOM ni dépendance — testé directement.
import { describe, it, expect, beforeEach } from "vitest";
import {
  registerUnsavedActivityCheck,
  unregisterUnsavedActivityCheck,
  hasUnsavedActivity,
} from "../unsavedActivity.js";

beforeEach(() => {
  // Le registre est un état module-level partagé entre tous les tests de ce
  // fichier (pas de vi.resetModules() ici, inutile pour un module sans effet
  // de bord au chargement) — on le remet à plat explicitement.
  unregisterUnsavedActivityCheck("a");
  unregisterUnsavedActivityCheck("b");
});

describe("unsavedActivity.js", () => {
  it("renvoie false quand aucune détection n'est enregistrée", () => {
    expect(hasUnsavedActivity()).toBe(false);
  });

  it("renvoie true si une détection enregistrée signale une activité en cours", () => {
    registerUnsavedActivityCheck("a", () => true);
    expect(hasUnsavedActivity()).toBe(true);
  });

  it("renvoie false si toutes les détections enregistrées signalent une absence d'activité", () => {
    registerUnsavedActivityCheck("a", () => false);
    registerUnsavedActivityCheck("b", () => false);
    expect(hasUnsavedActivity()).toBe(false);
  });

  it("renvoie true si AU MOINS une détection parmi plusieurs le signale", () => {
    registerUnsavedActivityCheck("a", () => false);
    registerUnsavedActivityCheck("b", () => true);
    expect(hasUnsavedActivity()).toBe(true);
  });

  it("une détection qui lève une exception est ignorée, jamais bloquante pour les autres", () => {
    registerUnsavedActivityCheck("a", () => {
      throw new Error("détection défaillante");
    });
    registerUnsavedActivityCheck("b", () => true);
    expect(hasUnsavedActivity()).toBe(true);
  });

  it("une détection qui lève une exception, seule enregistrée, compte comme 'rien à signaler'", () => {
    registerUnsavedActivityCheck("a", () => {
      throw new Error("détection défaillante");
    });
    expect(hasUnsavedActivity()).toBe(false);
  });

  it("enregistrer deux fois le même nom remplace la détection précédente (jamais d'accumulation)", () => {
    registerUnsavedActivityCheck("a", () => true);
    registerUnsavedActivityCheck("a", () => false);
    expect(hasUnsavedActivity()).toBe(false);
  });

  it("unregisterUnsavedActivityCheck retire une détection précédemment enregistrée", () => {
    registerUnsavedActivityCheck("a", () => true);
    unregisterUnsavedActivityCheck("a");
    expect(hasUnsavedActivity()).toBe(false);
  });

  it("unregisterUnsavedActivityCheck est sans effet si le nom n'est pas enregistré", () => {
    expect(() => unregisterUnsavedActivityCheck("jamais-enregistre")).not.toThrow();
    expect(hasUnsavedActivity()).toBe(false);
  });
});
