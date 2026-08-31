// ── auth.js : modales connexion/inscription/2FA/mot de passe oublié ────────
// Intégration DOM : auth.js manipule directement des ids précis dès son
// import (voir ensureAuthModalsMounted) — on charge donc le VRAI corps de
// index.html (loadPageBody) puis on importe le module dynamiquement une fois
// le DOM en place, avec api.js mocké (jamais de vrai réseau).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";

// Dupliqué en connaissance de cause (voir customExercise.test.js pour le même
// choix) : un import statique de curriculumSelector.js ici évaluerait ce
// module (donc son `import { api } from "./api.js"` mocké ci-dessous) AVANT
// que `const mockApi` n'existe encore (imports ES toujours hoistés avant le
// reste du corps du fichier) — `Cannot access 'mockApi' before
// initialization`. curriculumSelector.js n'est de toute façon jamais mocké
// dans ce fichier (localStorage réel utilisé tel quel).
const CLASS_LEVEL_KEY = "novamath:class_level";

const mockApi = {
  me: vi.fn(),
  register: vi.fn(),
  login: vi.fn(),
  enterGuest: vi.fn(),
  verify2FA: vi.fn(),
  recover2FA: vi.fn(),
  forgotPassword: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));

// `url` : window.location persiste entre tests d'un même fichier (un seul
// jsdom par fichier) — toujours la réassigner explicitement ici (même
// convention que abonnement.test.js::mountAbonnement) pour qu'un `?next=`
// posé par un test ne reste jamais collé au test suivant.
async function mountAuth({ meResolves = null, url = "/index.html" } = {}) {
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("index.html");
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockImplementation(() =>
    meResolves ? Promise.resolve({ user: meResolves }) : Promise.reject(new Error("401")),
  );
  vi.resetModules();
  await import("../auth.js");
  await flushPromises();
}

const $ = (id) => document.getElementById(id);

describe("auth.js — ouverture des modales", () => {
  beforeEach(async () => {
    await mountAuth();
  });

  it("clic sur .js-open-signup ouvre la modale d'inscription", () => {
    document.querySelector(".js-open-signup").click();
    expect($("signup-modal-overlay").hidden).toBe(false);
  });

  it("clic sur .js-open-login ouvre la modale de connexion", () => {
    document.querySelector(".js-open-login").click();
    expect($("login-modal-overlay").hidden).toBe(false);
  });

  it("clic sur .js-open-legal ouvre la modale des mentions légales", () => {
    document.querySelector(".js-open-legal").click();
    expect($("legal-modal-overlay").hidden).toBe(false);
  });

  it("le clic sur l'overlay lui-même ferme la modale ouverte", () => {
    document.querySelector(".js-open-login").click();
    $("login-modal-overlay").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect($("login-modal-overlay").hidden).toBe(true);
  });
});

describe("auth.js — bascule affichage du mot de passe", () => {
  beforeEach(async () => {
    await mountAuth();
  });

  it("le bouton .password-toggle bascule type=password <-> text", () => {
    const btn = document.querySelector('.password-toggle[data-target="signup-password"]');
    const input = $("signup-password");
    expect(input.type).toBe("password");
    btn.click();
    expect(input.type).toBe("text");
    btn.click();
    expect(input.type).toBe("password");
  });
});

describe("auth.js — indicateur de force du mot de passe", () => {
  beforeEach(async () => {
    await mountAuth();
  });

  it("affiche 'Faible' pour un mot de passe court", () => {
    $("signup-password").value = "a";
    $("signup-password").dispatchEvent(new Event("input"));
    expect($("signup-strength-label").textContent).toBe("Faible");
  });

  it("affiche 'Très fort' pour un mot de passe qui respecte toutes les règles", () => {
    $("signup-password").value = "Abcdef1!gh";
    $("signup-password").dispatchEvent(new Event("input"));
    expect($("signup-strength-label").textContent).toBe("Très fort");
  });

  it("masque l'indicateur si le champ est vidé", () => {
    $("signup-password").value = "x";
    $("signup-password").dispatchEvent(new Event("input"));
    $("signup-password").value = "";
    $("signup-password").dispatchEvent(new Event("input"));
    expect($("signup-strength").hidden).toBe(true);
  });
});

describe("auth.js — validation et soumission du formulaire d'inscription", () => {
  beforeEach(async () => {
    // Point de départ déterministe : aucune classe choisie dans ce jsdom
    // partagé entre tests du fichier, sauf si un test la pose lui-même.
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountAuth();
  });

  it("bloque la soumission et affiche les erreurs si les champs sont vides", async () => {
    $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect(mockApi.register).not.toHaveBeenCalled();
    expect($("signup-error-email").hidden).toBe(false);
  });

  it("refuse une adresse non-Gmail", async () => {
    $("signup-email").value = "test@yahoo.com";
    $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect($("signup-error-email").hidden).toBe(false);
    expect(mockApi.register).not.toHaveBeenCalled();
  });

  it("soumet avec succès quand tous les champs sont valides (classe déjà choisie : va droit au dashboard)", async () => {
    // Simule une classe déjà choisie explicitement dans ce navigateur (Phase 5) :
    // ce test vérifie le chemin d'inscription "classique", pas le détour
    // d'onboarding — voir le describe dédié ci-dessous pour ce cas.
    localStorage.setItem(CLASS_LEVEL_KEY, "seconde");
    mockApi.register.mockResolvedValue({});
    $("signup-email").value = "eleve@gmail.com";
    $("signup-username").value = "eleve_2026";
    $("signup-pseudo").value = "Eleve";
    $("signup-birth-date").value = "2000-01-01";
    $("signup-password").value = "Abcdef1!gh";
    $("signup-password-confirm").value = "Abcdef1!gh";
    $("signup-accept-terms").checked = true;
    $("signup-accept-privacy").checked = true;

    await withMockedLocation(async () => {
      $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(mockApi.register).toHaveBeenCalledWith(
        expect.objectContaining({ email: "eleve@gmail.com", username: "eleve_2026" }),
      );
      expect(window.location.href).toBe("/dashboard.html");
    });
  });

  it("affiche l'erreur serveur sur le champ ciblé par err.field", async () => {
    const err = new Error("Nom déjà pris.");
    err.field = "username";
    mockApi.register.mockRejectedValue(err);
    $("signup-email").value = "eleve@gmail.com";
    $("signup-username").value = "eleve_2026";
    $("signup-pseudo").value = "Eleve";
    $("signup-birth-date").value = "2000-01-01";
    $("signup-password").value = "Abcdef1!gh";
    $("signup-password-confirm").value = "Abcdef1!gh";
    $("signup-accept-terms").checked = true;
    $("signup-accept-privacy").checked = true;
    $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect($("signup-error-username").hidden).toBe(false);
    expect($("signup-error-username").textContent).toBe("Nom déjà pris.");
  });
});

// ── Phase 5 (onboarding) : détour par choisir-classe.html après une
// INSCRIPTION quand aucune classe n'a jamais été choisie explicitement dans
// ce navigateur (curriculumSelector.js::hasExplicitClassLevel). ────────────
describe("auth.js — inscription : détour onboarding vers choisir-classe.html", () => {
  function fillValidSignupForm($) {
    $("signup-email").value = "eleve@gmail.com";
    $("signup-username").value = "eleve_2026";
    $("signup-pseudo").value = "Eleve";
    $("signup-birth-date").value = "2000-01-01";
    $("signup-password").value = "Abcdef1!gh";
    $("signup-password-confirm").value = "Abcdef1!gh";
    $("signup-accept-terms").checked = true;
    $("signup-accept-privacy").checked = true;
  }

  it("aucune classe choisie, pas de ?next= : redirige vers choisir-classe.html?next=dashboard.html", async () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountAuth();
    mockApi.register.mockResolvedValue({});
    fillValidSignupForm($);

    await withMockedLocation(async () => {
      $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(window.location.href).toBe("/choisir-classe.html?next=dashboard.html");
    });
  });

  it("aucune classe choisie, ?next=chapitres.html : le paramètre est repropagé", async () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountAuth({ url: "/index.html?next=chapitres.html" });
    mockApi.register.mockResolvedValue({});
    fillValidSignupForm($);

    await withMockedLocation(async () => {
      $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(window.location.href).toBe("/choisir-classe.html?next=chapitres.html");
    });
  });

  it("?next= externe/invalide : jamais propagé, retombe sur dashboard.html (pas d'open redirect)", async () => {
    localStorage.removeItem(CLASS_LEVEL_KEY);
    await mountAuth({ url: "/index.html?next=https://evil.example.com" });
    mockApi.register.mockResolvedValue({});
    fillValidSignupForm($);

    await withMockedLocation(async () => {
      $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(window.location.href).toBe("/choisir-classe.html?next=dashboard.html");
    });
  });

  it("classe déjà choisie explicitement : aucun détour, va droit à la destination", async () => {
    localStorage.setItem(CLASS_LEVEL_KEY, "premiere");
    await mountAuth({ url: "/index.html?next=chapitres.html" });
    mockApi.register.mockResolvedValue({});
    fillValidSignupForm($);

    await withMockedLocation(async () => {
      $("signup-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(window.location.href).toBe("/chapitres.html");
    });
  });
});

describe("auth.js — connexion", () => {
  beforeEach(async () => {
    await mountAuth();
  });

  it("affiche une erreur globale si email/mot de passe sont vides", async () => {
    $("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect(mockApi.login).not.toHaveBeenCalled();
    expect($("login-error-global").hidden).toBe(false);
  });

  it("redirige vers /dashboard.html après une connexion réussie sans 2FA", async () => {
    mockApi.login.mockResolvedValue({});
    $("login-email").value = "eleve@gmail.com";
    $("login-password").value = "motdepasse";
    await withMockedLocation(async () => {
      $("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(window.location.href).toBe("/dashboard.html");
    });
  });

  it("ouvre le défi 2FA si le serveur répond two_factor_required", async () => {
    mockApi.login.mockResolvedValue({ two_factor_required: true, challenge_token: "tok123" });
    $("login-email").value = "eleve@gmail.com";
    $("login-password").value = "motdepasse";
    $("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect($("login-2fa-modal-overlay").hidden).toBe(false);
    expect($("login-2fa-form").dataset.challengeToken).toBe("tok123");
  });

  it("affiche l'erreur serveur en cas d'échec de connexion", async () => {
    mockApi.login.mockRejectedValue(new Error("Identifiants invalides."));
    $("login-email").value = "eleve@gmail.com";
    $("login-password").value = "faux";
    $("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect($("login-error-global").textContent).toBe("Identifiants invalides.");
  });
});

describe("auth.js — challenge 2FA (étape 2 de connexion)", () => {
  beforeEach(async () => {
    await mountAuth();
    mockApi.login.mockResolvedValue({ two_factor_required: true, challenge_token: "tok123" });
    $("login-email").value = "eleve@gmail.com";
    $("login-password").value = "motdepasse";
    $("login-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
  });

  it("bascule vers le mode recovery code au clic sur le lien dédié", () => {
    $("btn-2fa-toggle-recovery").click();
    expect($("login-2fa-recovery-row").hidden).toBe(false);
    expect($("login-2fa-code-row").hidden).toBe(true);
  });

  it("soumet le code TOTP via api.verify2FA et redirige", async () => {
    mockApi.verify2FA.mockResolvedValue({});
    $("login-2fa-code").value = "123456";
    await withMockedLocation(async () => {
      $("login-2fa-form").dispatchEvent(new Event("submit", { cancelable: true }));
      await flushPromises();
      expect(mockApi.verify2FA).toHaveBeenCalledWith("tok123", "123456");
      expect(window.location.href).toBe("/dashboard.html");
    });
  });

  it("soumet un recovery code via api.recover2FA en mode recovery", async () => {
    mockApi.recover2FA.mockResolvedValue({});
    $("btn-2fa-toggle-recovery").click();
    $("login-2fa-recovery-code").value = "recovery-code-x";
    $("login-2fa-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect(mockApi.recover2FA).toHaveBeenCalledWith("tok123", "recovery-code-x");
  });

  it("affiche une erreur si le code est invalide", async () => {
    mockApi.verify2FA.mockRejectedValue(new Error("Code invalide."));
    $("login-2fa-code").value = "000000";
    $("login-2fa-form").dispatchEvent(new Event("submit", { cancelable: true }));
    await flushPromises();
    expect($("login-2fa-error-global").hidden).toBe(false);
  });
});

// Les tests "mode invité" vivent dans auth-guest.test.js (fichier séparé) :
// auth.js câble .js-start-guest via délégation sur `document`
// (document.addEventListener("click", ...)) — un listener qui persiste tant
// que `document` existe. Comme ce fichier réimporte dynamiquement auth.js à
// CHAQUE test (`vi.resetModules()`, nécessaire pour rejouer ensureAuthModalsMounted
// sur un DOM neuf), les listeners de tous les tests précédents restent actifs
// en même temps sur le même `document` partagé au sein d'un fichier. Vitest
// isole chaque FICHIER de test dans son propre jsdom : séparer ces 2 tests
// dans leur propre fichier leur garantit un `document` vierge, sans quoi le
// test "compte déjà connecté" verrait aussi se déclencher les listeners
// (périmés mais toujours actifs) laissés par tous les tests précédents de ce
// fichier-ci.

describe("auth.js — mot de passe oublié", () => {
  beforeEach(async () => {
    await mountAuth();
    document.querySelector(".js-open-forgot").click();
  });

  it("refuse une adresse non-Gmail sans appeler l'API", async () => {
    $("forgot-email").value = "test@yahoo.com";
    $("btn-forgot-submit").click();
    await flushPromises();
    expect(mockApi.forgotPassword).not.toHaveBeenCalled();
    expect($("forgot-error").hidden).toBe(false);
  });

  it("affiche le message de succès renvoyé par le serveur", async () => {
    mockApi.forgotPassword.mockResolvedValue({ message: "Email envoyé." });
    $("forgot-email").value = "eleve@gmail.com";
    $("btn-forgot-submit").click();
    await flushPromises();
    expect($("forgot-result").hidden).toBe(false);
    expect($("forgot-result").innerHTML).toContain("Email envoyé.");
  });
});
