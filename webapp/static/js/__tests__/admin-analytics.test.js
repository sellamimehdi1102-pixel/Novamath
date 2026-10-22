// admin-analytics.js : Chantier de densité visuelle (2026-10-22). Prouve les
// fusions décidées par l'audit, sans perte de données réelles :
//   - Graphiques "Utilisateurs" (jour/mois/année) fusionnés en UN SEUL
//     graphique + un sélecteur de granularité — les 3 séries restent
//     accessibles, aucun nouvel appel réseau au changement de granularité.
//   - Graphiques "IA" (7 → 4) : "Appels & incidents IA" regroupe calls/
//     fallbacks/errors en un seul graphique multi-séries.
//   - "Top fournisseurs"/"Top coûts" fusionnés en un seul tableau
//     (nom/tokens/coût sur la même ligne).
//   - "Tickets par statut" (camembert) remplacé par une statistique
//     compacte, jamais un bloc graphique de 240px.
//   - Export + Rapports fusionnés en une seule UI (case "conserver dans
//     l'historique"), bouton "Imprimer" retiré.
import { describe, it, expect, vi, afterEach } from "vitest";
import { loadPageBody } from "./testUtils.js";
import { loadAnalytics } from "../admin-analytics.js";

const FILTERS_PAYLOAD = { windows: [{ value: "30j", label: "30 jours" }], default: "30j" };
const WINDOW = { value: "30j", label: "30 jours", since: "2026-09-22T00:00:00+00:00", until: null };

function series(values) {
  return { available: true, value: values };
}

const CHARTS_PAYLOAD = {
  window: WINDOW,
  users: {
    daily: series([{ date: "2026-10-20", value: 3 }]),
    monthly: series([{ date: "2026-10", value: 40 }]),
    yearly: series([{ date: "2026", value: 400 }]),
  },
  chatbot: {
    conversations_per_day: series([{ date: "2026-10-20", value: 5 }]),
    messages_per_day: {
      user: series([{ date: "2026-10-20", value: 8 }]),
      assistant: series([{ date: "2026-10-20", value: 8 }]),
    },
    ai_vs_local_per_day: {
      ai: series([{ date: "2026-10-20", value: 2 }]),
      local: series([{ date: "2026-10-20", value: 6 }]),
    },
  },
  ai: {
    tokens_per_day: series([{ date: "2026-10-20", value: 1000 }]),
    cost_per_day: series([{ date: "2026-10-20", value: 0.5 }]),
    calls_per_day: series([{ date: "2026-10-20", value: 10 }]),
    avg_latency_per_day: series([{ date: "2026-10-20", value: 320 }]),
    success_rate_per_day: series([{ date: "2026-10-20", value: 98.5 }]),
    fallbacks_per_day: series([{ date: "2026-10-20", value: 1 }]),
    errors_per_day: series([{ date: "2026-10-20", value: 0 }]),
  },
  support: {
    tickets_per_day: series([{ date: "2026-10-20", value: 2 }]),
    by_category: series({ Technique: 3, Facturation: 1 }),
    by_status: series({ open: 2, in_progress: 1, closed: 7 }),
  },
};

const RANKINGS_PAYLOAD = {
  window: WINDOW,
  users: {
    top_ai_consumers: series([{ user_id: 1, pseudo: "Alice", total_tokens: 500 }]),
    top_chatbot_users: series([{ user_id: 1, pseudo: "Alice", message_count: 42 }]),
    top_active_reason: "Top utilisateurs actifs / temps passé : voir le module Utilisateurs.",
  },
  ai: {
    top_providers: series([
      { provider_key: "gemini", requests: 10, total_tokens: 800, estimated_cost: 0.12 },
      { provider_key: "claude", requests: 4, total_tokens: 200, estimated_cost: 0.08 },
    ]),
    top_models: series([{ name: "gemini-pro", total_tokens: 800 }]),
    top_engines: series([{ engine: "local", requests: 20 }]),
    top_cost: series([{ name: "gemini-pro", estimated_cost: 0.12 }]),
  },
  support: { top_admins: series([{ admin_name: "Admin1", ticket_count: 3, avg_resolution_seconds: 3600 }]) },
};

let fetchLog;

function mockFetch({ reportsItems = [] } = {}) {
  fetchLog = [];
  global.fetch = vi.fn((url, opts) => {
    fetchLog.push({ url, method: (opts && opts.method) || "GET" });
    if (url === "/api/admin/analytics/filters") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(FILTERS_PAYLOAD) });
    }
    if (url === "/api/admin/analytics/pinned-kpis") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ pinned: [] }) });
    }
    if (url === "/api/admin/analytics/views") {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: [] }) });
    }
    if (url.startsWith("/api/admin/analytics/overview")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ window: WINDOW }) });
    }
    if (url.startsWith("/api/admin/analytics/charts")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(CHARTS_PAYLOAD) });
    }
    if (url.startsWith("/api/admin/analytics/rankings")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(RANKINGS_PAYLOAD) });
    }
    if (url === "/api/admin/analytics/reports" && (!opts || opts.method === undefined)) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ items: reportsItems }) });
    }
    if (url === "/api/admin/analytics/reports" && opts && opts.method === "POST") {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ filename: "rapport_test.pdf" }),
      });
    }
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
  });
}

function mountTemplate() {
  document.body.innerHTML = loadPageBody("admin.html");
  const template = document.getElementById("admin-analytics-template");
  document.getElementById("admin-content-body").appendChild(template.content.cloneNode(true));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin-analytics.js", () => {
  it("fusionne les 3 graphiques Utilisateurs en un seul, piloté par un sélecteur de granularité", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const container = document.getElementById("admin-analytics-users-charts");
    // Un seul graphique (un seul canvas), pas 3.
    expect(container.querySelectorAll("canvas").length).toBe(1);

    const select = document.getElementById("admin-analytics-users-granularity-select");
    expect([...select.options].map((o) => o.value)).toEqual(["daily", "monthly", "yearly"]);
    expect(select.value).toBe("daily");
  });

  it("changer la granularité redessine le graphique Utilisateurs sans nouvel appel réseau", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const callsBeforeSwitch = fetchLog.length;
    const select = document.getElementById("admin-analytics-users-granularity-select");
    select.value = "yearly";
    select.dispatchEvent(new Event("change"));

    expect(fetchLog.length).toBe(callsBeforeSwitch); // aucun fetch supplémentaire
    const container = document.getElementById("admin-analytics-users-charts");
    expect(container.querySelectorAll("canvas").length).toBe(1);
    expect(container.textContent).toContain("Croissance annuelle");
  });

  it("fusionne les 7 graphiques IA en 4, avec un graphique combiné 'Appels & incidents IA'", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const container = document.getElementById("admin-analytics-ai-charts");
    // 4 boîtes de graphique : tokens, coût, performance (latence+succès), incidents.
    expect(container.querySelectorAll(".admin-health-chart-box").length).toBe(4);
    expect(container.textContent).toContain("Appels & incidents IA");
    expect(container.textContent).toContain("Performance");
  });

  it("fusionne 'Top fournisseurs' et 'Top coûts' en un seul tableau (nom, tokens, coût)", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const container = document.getElementById("admin-analytics-ai-rankings");
    const tables = container.querySelectorAll("table");
    expect(tables.length).toBe(1);
    expect(container.textContent).toContain("gemini");
    expect(container.textContent).toContain("800"); // tokens
    expect(container.textContent).toContain("0.1200"); // coût (toFixed(4))
    // Jamais un second classement "Top coûts" distinct pour les mêmes lignes.
    expect(container.textContent).not.toContain("Top coûts");
  });

  it("remplace le camembert 'Tickets par statut' par une statistique compacte, sans réserver 240px", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const container = document.getElementById("admin-analytics-support-charts");
    const compact = container.querySelector(".admin-analytics-status-compact");
    expect(compact).not.toBeNull();
    expect(compact.classList.contains("admin-health-chart-box")).toBe(false);
    expect(compact.textContent).toContain("Ouverts : 2");
    expect(compact.textContent).toContain("En cours : 1");
    expect(compact.textContent).toContain("Fermés : 7");
    expect(compact.querySelector("canvas")).toBeNull();
  });

  it("raccourcit la note sous 'Top utilisateurs du chatbot' à une phrase courte", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const container = document.getElementById("admin-analytics-chatbot-rankings");
    expect(container.textContent).toContain("voir le module Utilisateurs");
    expect(container.textContent).not.toContain("réutilisés tels quels");
  });

  it("le bouton Imprimer a été retiré du template", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    expect(document.getElementById("admin-analytics-print-btn")).toBeNull();
  });

  it("Export + Rapports fusionnés : décoché, le bouton déclenche un export ponctuel (lien de téléchargement)", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const keepCheckbox = document.getElementById("admin-analytics-export-keep-checkbox");
    const reportTypeField = document.getElementById("admin-analytics-export-report-type-field");
    const submitBtn = document.getElementById("admin-analytics-export-submit-btn");
    expect(keepCheckbox.checked).toBe(false);
    expect(reportTypeField.hidden).toBe(true);
    expect(submitBtn.textContent).toBe("Exporter");

    const form = document.getElementById("admin-analytics-export-form");
    let clickedHref = null;
    const originalClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      clickedHref = this.href;
    };
    try {
      form.dispatchEvent(new Event("submit", { cancelable: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    } finally {
      HTMLAnchorElement.prototype.click = originalClick;
    }
    expect(clickedHref).toContain("/api/admin/analytics/export/pdf");
    // Aucune requête POST vers /reports pour un export ponctuel.
    expect(fetchLog.some((f) => f.url === "/api/admin/analytics/reports" && f.method === "POST")).toBe(false);
  });

  it("Export + Rapports fusionnés : cochée, révèle la période du rapport et génère un rapport persisté", async () => {
    mockFetch();
    mountTemplate();
    await loadAnalytics();

    const keepCheckbox = document.getElementById("admin-analytics-export-keep-checkbox");
    const reportTypeField = document.getElementById("admin-analytics-export-report-type-field");
    const submitBtn = document.getElementById("admin-analytics-export-submit-btn");

    keepCheckbox.checked = true;
    keepCheckbox.dispatchEvent(new Event("change"));
    expect(reportTypeField.hidden).toBe(false);
    expect(submitBtn.textContent).toBe("Générer le rapport");

    const form = document.getElementById("admin-analytics-export-form");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchLog.some((f) => f.url === "/api/admin/analytics/reports" && f.method === "POST")).toBe(true);
  });

  it("l'historique affiche à la fois les exports ponctuels et les rapports persistés (même tableau)", async () => {
    mockFetch({
      reportsItems: [
        {
          created_at: "2026-10-20T10:00:00Z",
          action: "analytics_export_pdf",
          result: "success",
          new_values: { format: "pdf" },
        },
        {
          created_at: "2026-10-19T10:00:00Z",
          action: "analytics_report",
          result: "success",
          new_values: { filename: "rapport.pdf", format: "pdf", report_type: "mensuel" },
        },
      ],
    });
    mountTemplate();
    await loadAnalytics();

    const tbody = document.getElementById("admin-analytics-reports-tbody");
    expect(tbody.querySelectorAll("tr").length).toBe(2);
  });
});
