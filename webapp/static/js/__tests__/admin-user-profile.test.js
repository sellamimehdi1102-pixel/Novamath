// Fiche complète d'un utilisateur (/admin/users/:id) — 4 onglets, CHACUN
// chargé au moment de sa première ouverture. "Activité" agrège désormais
// 4 API sous-jacentes (activity/courses/exercises/learning) en un seul
// onglet visible, avec Cours & apprentissage / Exercices en sous-sections
// repliables (.admin-collapse) — ce fichier prouve : le lazy loading réel,
// le cache par onglet (même agrégé), le skeleton, l'état vide, la gestion
// d'erreur/404, et l'absence de données fabriquées (contrat
// {available, value, reason}).
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";
import { loadUserProfile } from "../admin-user-profile.js";

function profilePayload(overrides = {}) {
  return {
    id: 7,
    avatar: null,
    pseudo: "Alice",
    email: "alice@test.novamath.local",
    plan: { available: true, value: "premium" },
    role: { available: true, value: "user" },
    account_status: { available: true, value: "active" },
    created_at: { available: true, value: "2026-01-01T08:00:00+00:00" },
    last_login_at: { available: true, value: "2026-07-01T10:00:00+00:00" },
    total_time_s: { available: true, value: 3600 },
    recent_ip: { available: true, value: { ip: "1.2.3.4", recorded_at: "2026-07-01T10:00:00+00:00" } },
    auth_provider: { available: true, value: "local" },
    two_factor_enabled: { available: true, value: false },
    email_verified: { available: true, value: false },
    ...overrides,
  };
}

// Les 4 API agrégées sous l'onglet "Activité" — plus de catégories
// systématiquement vides (paiements/bugs/erreurs/consultations de
// cours/tentatives d'exercice ont été retirées de l'affichage).
const TAB_PAYLOADS = {
  profile: profilePayload(),
  activity: {
    events: [{ type: "security", label: "Connexion réussie", created_at: "2026-07-01T10:00:00+00:00", meta: null }],
    total_events: 1,
  },
  courses: { chapters: null, chapters_reason: "Aucune progression enregistrée." },
  exercises: {
    total: 0,
    success_rate: null,
    chapters_with_most_errors: null,
    last_exercise: { available: false, value: null, reason: "aucun exercice" },
    time_spent_s: { available: true, value: 0 },
  },
  learning: { notions: null, notions_reason: "Aucune notion consultée." },
  chatbot: {
    conversations_count: 2,
    messages_count: 5,
    last_conversation: { available: true, value: { id: 1, title: "Conv", updated_at: "2026-07-01T10:00:00+00:00" } },
    history: [],
    time_spent_s: { available: false, value: null, reason: "non mesuré" },
    local_responses_count: { available: true, value: 3 },
    llm_responses_count: { available: true, value: 2 },
    engine_breakdown: { available: true, value: { local: 3, llm: 2 } },
    ai_consumption_available: false,
    ai_consumption_empty_message: "Ce compte n'a encore jamais utilisé le chatbot.",
    ai_requests_total: { available: false, value: null, reason: "non disponible" },
    ai_tokens_total: { available: false, value: null, reason: "non disponible" },
    ai_input_tokens: { available: false, value: null, reason: "non disponible" },
    ai_output_tokens: { available: false, value: null, reason: "non disponible" },
    ai_cost: { available: false, value: null, reason: "non disponible" },
    ai_most_used_provider: { available: false, value: null, reason: "non disponible" },
    ai_last_provider: { available: false, value: null, reason: "non disponible" },
    ai_last_model: { available: false, value: null, reason: "non disponible" },
    ai_avg_response_time_ms: { available: false, value: null, reason: "non disponible" },
    ai_last_used_at: { available: false, value: null, reason: "non disponible" },
    ai_real_requests: { available: false, value: null, reason: "non disponible" },
    ai_estimated_requests: { available: false, value: null, reason: "non disponible" },
    ai_real_tokens: { available: false, value: null, reason: "non disponible" },
    ai_estimated_tokens: { available: false, value: null, reason: "non disponible" },
    ai_source_breakdown: { available: false, value: null, reason: "non disponible" },
    ai_call_history: null,
    ai_call_history_reason: "Ce compte n'a encore jamais utilisé le chatbot.",
  },
  subscription: {
    plan: { available: true, value: "premium" },
    stripe_subscription_status: { available: false, value: null, reason: "aucun abonnement" },
    has_stripe_customer: { available: true, value: false },
  },
  support: {
    tickets: [
      {
        id: 1,
        subject: "Le chatbot ne répond plus",
        category: "bug",
        category_label: "Bug",
        priority: "haute",
        status: "open",
        status_label: "Ouvert",
        created_at: "2026-07-01T10:00:00+00:00",
        updated_at: "2026-07-02T09:00:00+00:00",
      },
    ],
    tickets_reason: null,
  },
};

let fetchLog;

function mockFetch(userId, { failTab = null, overrides = {} } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url) => {
    fetchLog.push(url);
    const match = url.match(new RegExp(`^/api/admin/users/(\\d+)/(\\w+)$`));
    if (!match) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    const [, id, tab] = match;
    if (Number(id) !== userId) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ error: "introuvable" }) });
    }
    if (tab === failTab) {
      return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "boom" }) });
    }
    const payload = overrides[tab] || TAB_PAYLOADS[tab];
    return Promise.resolve({ ok: true, json: () => Promise.resolve(payload) });
  });
}

function mountTemplate() {
  document.body.innerHTML = loadPageBody("admin.html");
  const template = document.getElementById("admin-user-profile-template");
  document.getElementById("admin-content-body").appendChild(template.content.cloneNode(true));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-user-profile.js — lazy loading réel", () => {
  it("n'appelle QUE l'API de l'onglet 'Informations' à l'ouverture, jamais les autres", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    expect(fetchLog).toEqual(["/api/admin/users/7/profile"]);
  });

  it("cliquer sur l'onglet Chatbot déclenche exactement UN nouvel appel, vers cette API précise", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/users/7/profile", "/api/admin/users/7/chatbot"]);
  });

  it("cliquer sur l'onglet Activité déclenche les 4 appels agrégés (activity/courses/exercises/learning)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    expect(fetchLog).toEqual([
      "/api/admin/users/7/profile",
      "/api/admin/users/7/activity",
      "/api/admin/users/7/courses",
      "/api/admin/users/7/exercises",
      "/api/admin/users/7/learning",
    ]);
  });

  it("rouvrir un onglet déjà chargé ne refait AUCUN appel réseau (cache par onglet)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="profile"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/users/7/profile", "/api/admin/users/7/chatbot"]);
  });

  it("rouvrir l'onglet Activité déjà chargé ne refait aucun des 4 appels", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="profile"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    expect(fetchLog).toEqual([
      "/api/admin/users/7/profile",
      "/api/admin/users/7/activity",
      "/api/admin/users/7/courses",
      "/api/admin/users/7/exercises",
      "/api/admin/users/7/learning",
    ]);
  });
});

describe("admin-user-profile.js — rendu de base et absence de données fabriquées", () => {
  it("affiche l'en-tête (pseudo/email/badges) et les champs de l'onglet Informations", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    expect(document.getElementById("admin-user-profile-head").textContent).toContain("Alice");
    expect(document.getElementById("admin-user-profile-head").textContent).toContain("alice@test.novamath.local");
    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("1.2.3.4");
    // Champs structurellement toujours vides (classe, prénom/nom) retirés
    // de l'affichage — plus de placeholder permanent dans l'onglet Informations.
    expect(panelText).not.toContain("Classe");
    expect(panelText).not.toContain("Prénom");
  });

  // Audit utilité/densité (2026-10-22) : pseudo/email/rôle/état du compte
  // sont des doublons EXACTS avec l'en-tête (renderHeader, toujours visible)
  // — retirés de la grille de l'onglet Informations, jamais masqués de
  // l'en-tête lui-même.
  it("onglet Informations : pseudo/email/rôle/état du compte ne sont plus répétés dans la grille, seulement dans l'en-tête", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    const headText = document.getElementById("admin-user-profile-head").textContent;
    expect(headText).toContain("Alice");
    expect(headText).toContain("alice@test.novamath.local");
    expect(headText).toContain("Utilisateur");
    expect(headText).toContain("Actif");

    const fieldLabels = [...document.querySelectorAll("#admin-user-profile-panel .admin-field-label")].map(
      (n) => n.textContent,
    );
    expect(fieldLabels).not.toContain("Pseudo");
    expect(fieldLabels).not.toContain("Adresse email");
    expect(fieldLabels).not.toContain("Rôle");
    expect(fieldLabels).not.toContain("État du compte");
    // Les champs non dupliqués restent bien présents.
    expect(fieldLabels).toContain("Date de création");
    expect(fieldLabels).toContain("Méthode de connexion");
  });

  it("onglet Activité : timeline visible, plus de catégories systématiquement vides listées", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Connexion réussie");
    expect(panelText).not.toContain("Catégories sans donnée disponible");
  });

  it("onglet Activité : sous-section repliable 'Cours & apprentissage' contient la raison exacte de l'absence de progression", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    const panel = document.getElementById("admin-user-profile-panel");
    expect(panel.querySelectorAll(".admin-collapse").length).toBe(2);
    expect(panel.textContent).toContain("Cours & apprentissage");
    expect(panel.textContent).toContain("Aucune progression enregistrée.");
    expect(panel.textContent).toContain("Aucune notion consultée.");
  });

  it("sous-section Exercices sans historique : jamais un taux de réussite fabriqué, et 'Notions difficiles' a disparu", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Aucune donnée disponible");
    expect(panelText).not.toMatch(/\b0%/);
    expect(panelText).not.toContain("Notions difficiles");
  });

  it("onglet Chatbot : Consommation IA est repliée dans un .admin-collapse, l'activité chatbot reste visible en clair", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    const panel = document.getElementById("admin-user-profile-panel");
    expect(panel.textContent).toContain("Activité chatbot");
    expect(panel.textContent).toContain("Conversations");
    const collapse = panel.querySelector(".admin-collapse");
    expect(collapse).not.toBeNull();
    expect(collapse.textContent).toContain("Consommation IA");
  });

  // Audit utilité/densité (2026-10-22) : les 10 cartes de "Consommation IA"
  // sont désormais regroupées en 3 blocs visuels (aucune carte supprimée).
  it("onglet Chatbot : Consommation IA regroupe ses cartes en 3 blocs Volume / Coût & fournisseur / Performance", async () => {
    mockFetch(7, {
      overrides: {
        chatbot: {
          ...TAB_PAYLOADS.chatbot,
          ai_consumption_available: true,
          ai_requests_total: { available: true, value: 10 },
          ai_tokens_total: { available: true, value: 1000 },
          ai_input_tokens: { available: true, value: 600 },
          ai_output_tokens: { available: true, value: 400 },
          ai_cost: { available: true, value: 0.01 },
          ai_most_used_provider: { available: true, value: "gemini" },
          ai_last_provider: { available: true, value: "gemini" },
          ai_last_model: { available: true, value: "gemini-pro" },
          ai_avg_response_time_ms: { available: true, value: 500 },
          ai_last_used_at: { available: true, value: "2026-07-01T10:00:00+00:00" },
        },
      },
    });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    const collapse = document.querySelector("#admin-user-profile-panel .admin-collapse");
    const groupTitles = [...collapse.querySelectorAll(".admin-section-title")].map((n) => n.textContent);
    expect(groupTitles).toEqual(["Volume", "Coût & fournisseur", "Performance"]);
    // Toutes les données restent présentes, juste réorganisées.
    expect(collapse.textContent).toContain("gemini-pro");
    expect(collapse.textContent).toContain("500 ms");
  });

  // Audit utilité/densité (2026-10-22) : repliée par défaut, comme
  // "Consommation IA" l'est déjà — aucune donnée perdue.
  it("onglet Chatbot : 'Historique des conversations' est repliable et fermée par défaut", async () => {
    mockFetch(7, {
      overrides: {
        chatbot: {
          ...TAB_PAYLOADS.chatbot,
          history: [{ title: "Conv récente", updated_at: "2026-07-01T10:00:00+00:00" }],
        },
      },
    });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    const panel = document.getElementById("admin-user-profile-panel");
    const collapses = [...panel.querySelectorAll(".admin-collapse")];
    const historyCollapse = collapses.find((c) => c.textContent.includes("Historique des conversations"));
    expect(historyCollapse).not.toBeUndefined();
    expect(historyCollapse.hasAttribute("open")).toBe(false);
    expect(historyCollapse.textContent).toContain("Conv récente");
  });

  // Audit utilité/densité (2026-10-22) : les 2 libellés de répartition
  // (conversations vs coût/tokens) doivent être visuellement distincts pour
  // ne jamais être confondus.
  it("onglet Chatbot : les libellés de répartition distinguent conversations et coût/tokens", async () => {
    mockFetch(7, {
      overrides: {
        chatbot: {
          ...TAB_PAYLOADS.chatbot,
          engine_breakdown: { available: true, value: { local: 3, gemini: 2 } },
          ai_consumption_available: true,
          ai_source_breakdown: {
            available: true,
            value: { gemini: { requests: 2, tokens: 500, cost: 0.01 } },
          },
        },
      },
    });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Répartition des réponses (conversations)");
    expect(panelText).toContain("Répartition des requêtes IA (coût/tokens)");
    expect(panelText).not.toContain("Répartition Local / Gemini / Claude");
    expect(panelText).not.toContain("Répartition par moteur");
  });

  it("onglet Abonnement : renouvellement/expiration/historique des paiements/date d'achat ont tous disparu (placeholders toujours vides)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="subscription"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).not.toContain("Date d'achat");
    expect(panelText).not.toContain("Renouvellement");
    expect(panelText).not.toContain("Expiration");
    expect(panelText).not.toContain("Historique des paiements");
  });

  it("l'onglet Statistiques n'existe plus", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    expect(document.querySelector('.admin-tab-btn[data-tab="statistics"]')).toBeNull();
  });
});

// Chantier Administrateur "Utilisateurs" (Phase 2) : méthode de connexion,
// 2FA, email vérifié (onglet Informations enrichi).
describe("admin-user-profile.js — onglet Informations enrichi (auth_provider/2FA/email vérifié)", () => {
  it("affiche la méthode de connexion, la 2FA désactivée et l'email non vérifié pour un compte local", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Local (email + mot de passe)");
    expect(panelText).toContain("Désactivée");
    expect(panelText).toContain("Non vérifié");
  });

  it("affiche Google, la 2FA activée et l'email vérifié pour un compte OAuth avec 2FA", async () => {
    mockFetch(7, {
      overrides: {
        profile: profilePayload({
          auth_provider: { available: true, value: "google" },
          two_factor_enabled: { available: true, value: true },
          email_verified: { available: true, value: true },
        }),
      },
    });
    mountTemplate();
    await loadUserProfile(7);

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Google");
    expect(panelText).toContain("Activée");
    expect(panelText).toContain("Vérifié");
  });

  it("un fournisseur inconnu retombe sur un fallback propre (valeur brute), jamais un libellé inventé", async () => {
    mockFetch(7, {
      overrides: {
        profile: profilePayload({
          auth_provider: { available: true, value: "microsoft" },
        }),
      },
    });
    mountTemplate();
    await loadUserProfile(7);

    expect(document.getElementById("admin-user-profile-panel").textContent).toContain("microsoft");
  });
});

// Chantier Administrateur "Utilisateurs" (Phase 2) : nouvel onglet Support,
// strictement informatif (réutilise support_service.py, aucune action).
describe("admin-user-profile.js — onglet Support", () => {
  it("est chargé en lazy loading, comme les autres onglets (un seul appel réseau à l'ouverture)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/users/7/profile", "/api/admin/users/7/support"]);
  });

  it("affiche le sujet, la catégorie, la priorité, le statut et les dates d'un ticket réel", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Le chatbot ne répond plus");
    expect(panelText).toContain("Bug");
    expect(panelText).toContain("Ouvert");
  });

  it("état vide : aucun ticket affiche un message explicite, jamais un tableau vide silencieux", async () => {
    mockFetch(7, {
      overrides: { support: { tickets: null, tickets_reason: "Aucun ticket support n'a été créé par ce compte." } },
    });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();

    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(panelText).toContain("Aucun ticket support n'a été créé par ce compte.");
    expect(document.querySelector("#admin-user-profile-panel table")).toBeNull();
  });

  it("aucun bouton d'action (répondre/fermer/assigner) n'est présent dans cet onglet", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();

    expect(document.querySelectorAll("#admin-user-profile-panel button").length).toBe(0);
  });

  it("rouvrir l'onglet Support déjà chargé ne refait aucun appel réseau (cache par onglet)", async () => {
    mockFetch(7);
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="profile"]').click();
    await flushPromises();
    document.querySelector('.admin-tab-btn[data-tab="support"]').click();
    await flushPromises();

    expect(fetchLog).toEqual(["/api/admin/users/7/profile", "/api/admin/users/7/support"]);
  });
});

// Unification Chantier Administrateur "Utilisateurs" (Phase 2 bis) :
// mêmes libellés EXACTS pour account_status que la liste Utilisateurs
// (admin-users.js::ACCOUNT_STATUS_LABELS) — jamais un second wording pour
// la même valeur ("pending_parental_consent"/"parental_consent_refused").
describe("admin-user-profile.js — libellés account_status unifiés avec la liste Utilisateurs", () => {
  // Audit utilité/densité (2026-10-22) : "État du compte" a été retiré de
  // l'onglet Informations (doublon exact avec l'en-tête) — ce test vérifie
  // désormais le libellé dans l'en-tête, seul endroit où il est affiché,
  // et confirme explicitement que le panneau ne le répète plus.
  it("affiche 'En attente de consentement' (et non 'Consentement parental en attente') dans l'en-tête, jamais répété dans l'onglet Informations", async () => {
    mockFetch(7, {
      overrides: {
        profile: profilePayload({ account_status: { available: true, value: "pending_parental_consent" } }),
      },
    });
    mountTemplate();
    await loadUserProfile(7);

    const headText = document.getElementById("admin-user-profile-head").textContent;
    const panelText = document.getElementById("admin-user-profile-panel").textContent;
    expect(headText).toContain("En attente de consentement");
    expect(headText).not.toContain("Consentement parental en attente");
    expect(panelText).not.toContain("En attente de consentement");
    expect(panelText).not.toContain("Consentement parental en attente");
  });

  it("affiche 'Consentement refusé' (et non 'Consentement parental refusé') dans l'en-tête", async () => {
    mockFetch(7, {
      overrides: {
        profile: profilePayload({ account_status: { available: true, value: "parental_consent_refused" } }),
      },
    });
    mountTemplate();
    await loadUserProfile(7);

    const headText = document.getElementById("admin-user-profile-head").textContent;
    expect(headText).toContain("Consentement refusé");
    expect(headText).not.toContain("Consentement parental refusé");
  });
});

// Clarification explicite (Chantier Administrateur "Utilisateurs", Phase 2
// bis) : les statistiques "Consommation IA" de cette fiche ne portent QUE
// sur l'utilisateur sélectionné, jamais une vue globale de la plateforme.
describe("admin-user-profile.js — clarification 'Consommation IA' par utilisateur uniquement", () => {
  it("le hint de la section Consommation IA précise explicitement qu'elle ne porte que sur cet utilisateur", async () => {
    mockFetch(7, {
      overrides: {
        chatbot: {
          ...TAB_PAYLOADS.chatbot,
          ai_consumption_available: true,
          ai_requests_total: { available: true, value: 10 },
          ai_tokens_total: { available: true, value: 1000 },
          ai_input_tokens: { available: true, value: 600 },
          ai_output_tokens: { available: true, value: 400 },
          ai_cost: { available: true, value: 0.01 },
          ai_most_used_provider: { available: true, value: "gemini" },
          ai_last_provider: { available: true, value: "gemini" },
          ai_last_model: { available: true, value: "gemini-pro" },
          ai_avg_response_time_ms: { available: true, value: 500 },
          ai_last_used_at: { available: true, value: "2026-07-01T10:00:00+00:00" },
        },
      },
    });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="chatbot"]').click();
    await flushPromises();

    // Audit utilité/densité (2026-10-22) : le texte explicatif permanent est
    // remplacé par une icône "i"/tooltip sur le titre — l'information reste
    // accessible via l'attribut title, plus dans le textContent visible.
    const collapse = document.querySelector("#admin-user-profile-panel .admin-collapse");
    const infoIcon = collapse.querySelector(".admin-collapse-hint .admin-info-icon");
    expect(infoIcon).not.toBeNull();
    expect(infoIcon.getAttribute("title")).toContain("Uniquement pour cet utilisateur");
    expect(infoIcon.getAttribute("title")).toContain("pas une vue globale");
  });
});

describe("admin-user-profile.js — gestion des erreurs", () => {
  it("un onglet en échec réseau affiche un message d'erreur, jamais un plantage silencieux", async () => {
    mockFetch(7, { failTab: "activity" });
    mountTemplate();
    await loadUserProfile(7);
    document.querySelector('.admin-tab-btn[data-tab="activity"]').click();
    await flushPromises();

    expect(document.getElementById("admin-user-profile-panel").textContent).toContain(
      "Impossible de charger cet onglet",
    );
  });

  it("utilisateur introuvable (404) affiche un message explicite", async () => {
    mockFetch(999);
    mountTemplate();
    await loadUserProfile(7); // 7 !== 999 -> toutes les requêtes émulent un 404

    expect(document.getElementById("admin-user-profile-panel").textContent).toContain("introuvable");
  });
});

describe("admin-user-profile.js — skeleton loading", () => {
  it("affiche un skeleton pendant le chargement d'un nouvel onglet", async () => {
    let resolveFetch;
    global.fetch = vi.fn((url) => {
      if (url === "/api/admin/users/7/profile") {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TAB_PAYLOADS.profile) });
      }
      return new Promise((resolve) => {
        resolveFetch = () => resolve({ ok: true, json: () => Promise.resolve(TAB_PAYLOADS.subscription) });
      });
    });
    mountTemplate();
    await loadUserProfile(7);

    document.querySelector('.admin-tab-btn[data-tab="subscription"]').click();
    await Promise.resolve();
    expect(document.querySelectorAll(".admin-tab-skeleton-row").length).toBeGreaterThan(0);

    resolveFetch();
    await flushPromises();
    expect(document.querySelectorAll(".admin-tab-skeleton-row").length).toBe(0);
  });
});
