// Fiche complète d'un utilisateur (/admin/users/:id) — 4 onglets, CHACUN
// chargé au moment où il est ouvert pour la première fois (lazy loading réel :
// ouvrir la fiche ne déclenche qu'un seul appel réseau, celui de l'onglet
// actif par défaut). L'onglet "Activité" agrège en une fois activité/cours/
// exercices/apprentissage (un appel par API sous-jacente, toutes déclenchées
// ensemble uniquement quand cet onglet est ouvert — toujours zéro appel pour
// les onglets jamais consultés).
// Lecture seule stricte : aucun bouton d'action nulle part dans ce fichier.
import { createCollapseSection, wireCollapsePersistence } from "./admin-collapse.js";
import { statusBadge, priorityBadge } from "./admin-support.js";

const EMPTY_LABEL = "Aucune donnée disponible";

// Chantier Administrateur "Utilisateurs" (Phase 2) : nouvel onglet "Support"
// (avant "Abonnement") — pas de nouveau système de tickets, réutilise
// entièrement support_service.py (voir admin_user_profile_service.get_support).
const TABS = [
  { id: "profile", label: "Informations" },
  { id: "activity", label: "Activité" },
  { id: "chatbot", label: "Chatbot" },
  { id: "support", label: "Support" },
  { id: "subscription", label: "Abonnement" },
];

// Une entrée d'onglet peut agréger plusieurs API existantes (voir
// server.py::_ADMIN_USER_PROFILE_TABS, non modifié) — "Activité" reste une
// seule ouverture d'onglet côté utilisateur, mais combine les anciens onglets
// Cours/Exercices/Apprentissage en sous-sections repliables.
const TAB_ENDPOINTS = {
  profile: ["profile"],
  activity: ["activity", "courses", "exercises", "learning"],
  chatbot: ["chatbot"],
  support: ["support"],
  subscription: ["subscription"],
};

const PLAN_LABELS = { free: "Gratuit", premium: "Premium", ultra: "Ultra" };
const ROLE_LABELS = {
  user: "Utilisateur", support: "Support", moderator: "Modérateur",
  admin: "Admin", super_admin: "Super admin",
};
const ACCOUNT_STATUS_LABELS = {
  active: "Actif", pending_parental_consent: "Consentement parental en attente",
  parental_consent_refused: "Consentement parental refusé",
};
// auth_provider réel (users.auth_provider) — seul "google" est un
// fournisseur OAuth réellement configuré aujourd'hui (voir auth.py::
// OAUTH_PROVIDERS) ; toute autre valeur retombe sur un fallback propre
// plutôt qu'un libellé inventé.
const AUTH_PROVIDER_LABELS = { local: "Local (email + mot de passe)", guest: "Invité", google: "Google" };
function authProviderLabel(provider) {
  return AUTH_PROVIDER_LABELS[provider] || provider;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDateTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatTimestampMs(ms) {
  if (!ms) return null;
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatDuration(seconds) {
  const s = Math.round(seconds || 0);
  if (s < 60) return `${s} s`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return remMinutes ? `${hours} h ${remMinutes} min` : `${hours} h`;
}

// ── Bloc générique champ label/valeur, honore le contrat {available,value,reason} ──
function fieldRow(label, metric, formatter = (v) => v) {
  const row = el("div", "admin-field");
  row.appendChild(el("span", "admin-field-label", label));
  if (!metric || !metric.available) {
    row.appendChild(el("span", "admin-field-value admin-field-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) row.appendChild(el("span", "admin-field-reason", metric.reason));
  } else {
    row.appendChild(el("span", "admin-field-value", formatter(metric.value)));
  }
  return row;
}

function badge(text, modifier) {
  return el("span", `admin-badge admin-badge--${modifier}`, text);
}

function emptyState(message) {
  return el("p", "admin-empty", message || EMPTY_LABEL);
}

// ── Sous-section repliable (composant transverse admin-collapse.js) : les
// rendus existants produisent des noeuds DOM (via el()), alors que
// createCollapseSection attend une chaîne HTML — on sérialise le noeud une
// fois construit, sans dupliquer la logique de rendu. ──────────────────────
function nodeToHtml(node) {
  const container = document.createElement("div");
  container.appendChild(node);
  return container.innerHTML;
}

function collapseSection({ id, title, hint, open = false, bodyNode }) {
  const html = createCollapseSection({ id, title, hint, open, bodyHtml: nodeToHtml(bodyNode) });
  const container = document.createElement("div");
  container.innerHTML = html.trim();
  return container.firstElementChild;
}

// ── En-tête de la fiche (identité) ───────────────────────────────────────
function renderHeader(profile) {
  const head = document.getElementById("admin-user-profile-head");
  head.innerHTML = "";

  const avatarWrap = el("span", "admin-avatar admin-avatar--lg");
  if (profile.avatar) {
    const img = document.createElement("img");
    img.src = profile.avatar;
    img.alt = "";
    avatarWrap.appendChild(img);
  } else {
    avatarWrap.textContent = (profile.pseudo || "?").trim().charAt(0).toUpperCase();
  }
  head.appendChild(avatarWrap);

  const meta = el("div", "admin-user-profile-meta");
  meta.appendChild(el("h1", "admin-user-profile-name", profile.pseudo));
  meta.appendChild(el("p", "admin-user-profile-email", profile.email));
  const badges = el("div", "admin-user-profile-badges");
  badges.appendChild(badge(PLAN_LABELS[profile.plan.value] || profile.plan.value, profile.plan.value));
  badges.appendChild(badge(ROLE_LABELS[profile.role.value] || profile.role.value, "role"));
  const statusOk = profile.account_status.value === "active";
  badges.appendChild(el("span", `admin-status-dot admin-status-dot--${statusOk ? "ok" : "down"}`,
    ACCOUNT_STATUS_LABELS[profile.account_status.value] || profile.account_status.value));
  meta.appendChild(badges);
  head.appendChild(meta);
}

// ── 1. Informations ──────────────────────────────────────────────────────
function renderProfileTab(data) {
  const grid = el("div", "admin-fields-grid");
  grid.appendChild(fieldRow("Pseudo", { available: true, value: data.pseudo }));
  grid.appendChild(fieldRow("Adresse email", { available: true, value: data.email }));
  grid.appendChild(fieldRow("Rôle", data.role, (v) => ROLE_LABELS[v] || v));
  grid.appendChild(fieldRow("État du compte", data.account_status, (v) => ACCOUNT_STATUS_LABELS[v] || v));
  grid.appendChild(fieldRow("Date de création", data.created_at, formatDateTime));
  grid.appendChild(fieldRow("Dernière connexion", data.last_login_at, formatDateTime));
  grid.appendChild(fieldRow("Temps passé", data.total_time_s, formatDuration));
  grid.appendChild(fieldRow("Adresse IP récente", data.recent_ip,
    (v) => `${v.ip} (${formatDateTime(v.recorded_at)})`));
  grid.appendChild(fieldRow("Méthode de connexion", data.auth_provider, authProviderLabel));
  grid.appendChild(fieldRow("Authentification à deux facteurs (2FA)", data.two_factor_enabled,
    (v) => (v ? "Activée" : "Désactivée")));
  grid.appendChild(fieldRow("Email vérifié", data.email_verified, (v) => (v ? "Vérifié" : "Non vérifié")));
  return grid;
}

// ── 2. Activité (timeline + sous-sections repliables Cours & apprentissage
// et Exercices) ───────────────────────────────────────────────────────────
const ACTIVITY_ICONS = { security: "🔐", conversation: "💬", review: "⭐" };

// ── Cours & apprentissage (fusion des anciens onglets "Cours" et
// "Apprentissage", même source data/user_course_progress) ─────────────────
function renderCoursesLearningBody(courses, learning) {
  const wrap = el("div", "admin-courses-tab");

  wrap.appendChild(el("h3", "admin-section-title", "Cours"));
  if (!courses.chapters) {
    wrap.appendChild(emptyState(courses.chapters_reason));
  } else {
    const grid = el("div", "admin-cards");
    courses.chapters.forEach((c) => {
      const card = el("article", "admin-card");
      card.appendChild(el("div", "admin-card-label", `${c.chapter_id} (${c.class_level})`));
      card.appendChild(el("div", "admin-card-value", `${c.progress_pct}%`));
      const bar = el("div", "admin-progress-bar");
      const fill = el("div", "admin-progress-bar-fill");
      fill.style.width = `${c.progress_pct}%`;
      bar.appendChild(fill);
      card.appendChild(bar);
      card.appendChild(el("div", "admin-card-sub", `${c.notions_done}/${c.notions_total} notions · dernière mise à jour : ${formatTimestampMs(c.last_updated_at) || EMPTY_LABEL}`));
      grid.appendChild(card);
    });
    wrap.appendChild(grid);
  }

  wrap.appendChild(el("h3", "admin-section-title", "Notions étudiées"));
  if (!learning.notions) {
    wrap.appendChild(emptyState(learning.notions_reason));
    return wrap;
  }

  const table = el("table", "admin-users-table admin-learning-table");
  const theadRow = el("tr");
  ["Chapitre", "Notion", "Classe", "Statut", "Date"].forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
  const thead = document.createElement("thead");
  thead.appendChild(theadRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  learning.notions.forEach((n) => {
    const tr = el("tr", "admin-users-row");
    tr.appendChild(el("td", "admin-users-td", n.chapter_id));
    tr.appendChild(el("td", "admin-users-td", n.notion_id));
    tr.appendChild(el("td", "admin-users-td", n.class_level));
    tr.appendChild(el("td", "admin-users-td", n.status || EMPTY_LABEL));
    tr.appendChild(el("td", "admin-users-td", formatTimestampMs(n.updated_at) || EMPTY_LABEL));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  const wrapTable = el("div", "admin-users-table-wrap");
  wrapTable.appendChild(table);
  wrap.appendChild(wrapTable);
  return wrap;
}

// ── Exercices (ex-onglet "Exercices", "Notions difficiles" retiré — champ
// toujours vide, voir admin_user_profile_service.get_exercises) ───────────
function renderExercisesBody(data) {
  const wrap = el("div", "admin-exercises-tab");
  const cards = el("div", "admin-cards");

  const totalCard = el("article", "admin-card");
  totalCard.appendChild(el("div", "admin-card-label", "Exercices réalisés"));
  totalCard.appendChild(el("div", "admin-card-value", String(data.total)));
  cards.appendChild(totalCard);

  const successCard = el("article", "admin-card");
  successCard.appendChild(el("div", "admin-card-label", "Taux de réussite"));
  successCard.appendChild(el("div", data.success_rate === null ? "admin-card-value--empty" : "admin-card-value",
    data.success_rate === null ? EMPTY_LABEL : `${data.success_rate}%`));
  cards.appendChild(successCard);

  const timeCard = el("article", "admin-card");
  timeCard.appendChild(el("div", "admin-card-label", "Temps passé"));
  timeCard.appendChild(el("div", "admin-card-value", formatDuration(data.time_spent_s.value)));
  cards.appendChild(timeCard);
  wrap.appendChild(cards);

  const fields = el("div", "admin-fields-grid");
  if (data.last_exercise.available) {
    const v = data.last_exercise.value;
    fields.appendChild(fieldRow("Dernier exercice", { available: true, value: v },
      (val) => `${val.chapter || EMPTY_LABEL} · ${val.correct ? "réussi" : "échoué"} · ${formatDuration(val.duration_s)} · ${formatTimestampMs(val.date) || EMPTY_LABEL}`));
  } else {
    fields.appendChild(fieldRow("Dernier exercice", data.last_exercise));
  }
  wrap.appendChild(fields);

  if (data.chapters_with_most_errors) {
    const section = el("div", "admin-unavailable-note");
    section.appendChild(el("h3", "admin-unavailable-note-title", "Chapitres avec le plus d'erreurs"));
    const list = el("ul", "admin-unavailable-list");
    data.chapters_with_most_errors.forEach((c) => {
      list.appendChild(el("li", "admin-unavailable-item", `${c.chapter} — ${c.errors} erreur(s)`));
    });
    section.appendChild(list);
    wrap.appendChild(section);
  }
  return wrap;
}

function renderActivityTab(data) {
  const wrap = el("div", "admin-activity-tab");
  const activity = data.activity;

  if (activity.events.length === 0) {
    wrap.appendChild(emptyState("Aucun événement enregistré pour ce compte."));
  } else {
    const timeline = el("ol", "admin-timeline");
    activity.events.forEach((event) => {
      const item = el("li", "admin-timeline-item");
      item.appendChild(el("span", "admin-timeline-icon", ACTIVITY_ICONS[event.type] || "•"));
      const body = el("div", "admin-timeline-body");
      body.appendChild(el("span", "admin-timeline-label", event.label));
      body.appendChild(el("span", "admin-timeline-date", formatDateTime(event.created_at) || EMPTY_LABEL));
      item.appendChild(body);
      timeline.appendChild(item);
    });
    wrap.appendChild(timeline);
  }

  wrap.appendChild(collapseSection({
    id: "user-profile-courses-learning",
    title: "Cours & apprentissage",
    hint: "Progression par chapitre et notions étudiées",
    bodyNode: renderCoursesLearningBody(data.courses, data.learning),
  }));

  wrap.appendChild(collapseSection({
    id: "user-profile-exercises",
    title: "Exercices",
    hint: "Total, taux de réussite, chapitres à erreurs",
    bodyNode: renderExercisesBody(data.exercises),
  }));

  wireCollapsePersistence(wrap);
  return wrap;
}

// ── 3. Chatbot ────────────────────────────────────────────────────────────
function formatCost(usd) {
  return `${new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(usd)} $`;
}

function formatMs(ms) {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

// Carte générique {available,value,reason} — même contrat que le Dashboard
// Administrateur (admin-dashboard.js), réutilisé ici pour les statistiques
// IA PAR UTILISATEUR (voir admin_user_profile_service.get_chatbot(), calculées
// exclusivement à partir de ai_request_logs, jamais de ai_provider_usage).
function metricCard(label, metric, formatter = (v) => v) {
  const card = el("article", "admin-card");
  card.appendChild(el("div", "admin-card-label", label));
  if (!metric || !metric.available) {
    card.appendChild(el("div", "admin-card-value admin-card-value--empty", EMPTY_LABEL));
    if (metric && metric.reason) card.appendChild(el("div", "admin-card-sub", metric.reason));
  } else {
    card.appendChild(el("div", "admin-card-value", formatter(metric.value)));
  }
  return card;
}

// Libellés d'affichage des buckets de engine_breakdown (voir
// db.chatbot_engine_breakdown_for_user) — "local" regroupe tous les moteurs
// pédagogiques locaux, "uncategorized" les messages écrits avant ce
// chantier (jamais reclassés par supposition), tout le reste est un
// provider LLM réel ("gemini"/"anthropic"/...).
const ENGINE_BUCKET_LABELS = {
  local: "Moteur local",
  uncategorized: "Non catégorisé (avant instrumentation)",
  gemini: "Gemini",
  anthropic: "Claude (Anthropic)",
  cache: "Cache IA",
  clarification: "Clarification",
};

function engineBucketLabel(bucket) {
  return ENGINE_BUCKET_LABELS[bucket] || bucket;
}

// ── Consommation IA (repliée par défaut : allège l'affichage, doublon
// partiel avec le module IA global — mais conservée par utilisateur) ──────
function renderAiConsumptionBody(data) {
  const wrap = el("div", "admin-ai-consumption-body");
  if (!data.ai_consumption_available) {
    wrap.appendChild(emptyState(data.ai_consumption_empty_message));
    return wrap;
  }

  const aiCards = el("div", "admin-cards");
  aiCards.appendChild(metricCard("Requêtes IA (total)", data.ai_requests_total));
  aiCards.appendChild(metricCard("Tokens totaux", data.ai_tokens_total));
  aiCards.appendChild(metricCard("Tokens entrée (input)", data.ai_input_tokens));
  aiCards.appendChild(metricCard("Tokens sortie (output)", data.ai_output_tokens));
  aiCards.appendChild(metricCard("Coût IA (réel, Gemini/Claude uniquement)", data.ai_cost, formatCost));
  aiCards.appendChild(metricCard("Fournisseur le plus utilisé", data.ai_most_used_provider));
  aiCards.appendChild(metricCard("Dernier fournisseur utilisé", data.ai_last_provider));
  aiCards.appendChild(metricCard("Dernier modèle utilisé", data.ai_last_model));
  aiCards.appendChild(metricCard("Temps moyen de réponse", data.ai_avg_response_time_ms, formatMs));
  aiCards.appendChild(metricCard("Dernière utilisation", data.ai_last_used_at, formatDateTime));
  wrap.appendChild(aiCards);

  // Transparence réel/estimé : jamais confondre un vrai comptage
  // Gemini/Claude avec une estimation heuristique du moteur local.
  if (data.ai_real_requests.available && data.ai_estimated_requests.available) {
    const note = el("div", "admin-unavailable-note");
    note.appendChild(el("h3", "admin-unavailable-note-title", "Réel vs estimé"));
    const list = el("ul", "admin-unavailable-list");
    list.appendChild(el("li", "admin-unavailable-item",
      `${data.ai_real_requests.value} requête(s) réelle(s) (Gemini/Claude) — ${data.ai_real_tokens.value} tokens réels`));
    list.appendChild(el("li", "admin-unavailable-item",
      `${data.ai_estimated_requests.value} requête(s) moteur local/cache/clarification — ${data.ai_estimated_tokens.value} tokens estimés (aucun coût réel)`));
    note.appendChild(list);
    wrap.appendChild(note);
  }

  if (data.ai_source_breakdown.available) {
    const entries = Object.entries(data.ai_source_breakdown.value);
    if (entries.length) {
      const section = el("div", "admin-unavailable-note");
      section.appendChild(el("h3", "admin-unavailable-note-title", "Répartition par moteur"));
      const list = el("ul", "admin-unavailable-list");
      entries.forEach(([bucket, v]) => {
        list.appendChild(el("li", "admin-unavailable-item",
          `${engineBucketLabel(bucket)} — ${v.requests} requête(s), ${v.tokens} tokens, ${formatCost(v.cost)}`));
      });
      section.appendChild(list);
      wrap.appendChild(section);
    }
  }

  // ── Historique des appels IA (ai_request_logs, distinct de l'historique
  // des conversations, resté visible hors de cette sous-section) ──────────
  const aiHistorySection = el("div", "admin-unavailable-note");
  aiHistorySection.appendChild(el("h3", "admin-unavailable-note-title", "Historique des appels IA"));
  if (!data.ai_call_history) {
    aiHistorySection.appendChild(emptyState(data.ai_call_history_reason));
  } else {
    const table = el("table", "admin-users-table admin-learning-table");
    const theadRow = el("tr");
    ["Moteur", "Fournisseur", "Modèle", "Tokens (in/out)", "Coût", "Durée", "Résultat", "Date"]
      .forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
    const thead = document.createElement("thead");
    thead.appendChild(theadRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    data.ai_call_history.forEach((call) => {
      const tr = el("tr", "admin-users-row");
      const engineLabel = call.estimated ? `${call.engine || call.provider} (estimé)` : (call.engine || "llm");
      tr.appendChild(el("td", "admin-users-td", engineLabel));
      tr.appendChild(el("td", "admin-users-td", call.provider));
      tr.appendChild(el("td", "admin-users-td", call.model));
      tr.appendChild(el("td", "admin-users-td", `${call.input_tokens} / ${call.output_tokens}`));
      tr.appendChild(el("td", "admin-users-td", call.estimated ? "—" : formatCost(call.estimated_cost)));
      tr.appendChild(el("td", "admin-users-td", formatMs(call.response_time_ms)));
      const resultLabel = call.success ? (call.fallback ? "Succès (fallback)" : "Succès") : "Échec";
      tr.appendChild(el("td", "admin-users-td", resultLabel));
      tr.appendChild(el("td", "admin-users-td", formatDateTime(call.created_at)));
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    aiHistorySection.appendChild(table);
  }
  wrap.appendChild(aiHistorySection);

  return wrap;
}

function renderChatbotTab(data) {
  const wrap = el("div", "admin-chatbot-tab");

  // ── Activité chatbot : toujours alimentée depuis conversations/messages,
  // jamais depuis ai_request_logs — reflète l'usage réel même si tout a été
  // répondu par le moteur local. ───────────────────────────────────────────
  wrap.appendChild(el("h3", "admin-section-title", "Activité chatbot"));
  const cards = el("div", "admin-cards");
  [
    ["Conversations", data.conversations_count],
    ["Messages", data.messages_count],
  ].forEach(([label, value]) => {
    const card = el("article", "admin-card");
    card.appendChild(el("div", "admin-card-label", label));
    card.appendChild(el("div", "admin-card-value", String(value)));
    cards.appendChild(card);
  });
  cards.appendChild(metricCard("Réponses locales", data.local_responses_count));
  cards.appendChild(metricCard("Réponses LLM", data.llm_responses_count));
  wrap.appendChild(cards);

  const fields = el("div", "admin-fields-grid");
  fields.appendChild(fieldRow("Dernière conversation", data.last_conversation,
    (v) => `${v.title} (${formatDateTime(v.updated_at)})`));
  fields.appendChild(fieldRow("Temps passé", data.time_spent_s, formatDuration));
  wrap.appendChild(fields);

  if (data.engine_breakdown.available) {
    const breakdown = data.engine_breakdown.value;
    const entries = Object.entries(breakdown).filter(([, n]) => n > 0);
    if (entries.length) {
      const section = el("div", "admin-unavailable-note");
      section.appendChild(el("h3", "admin-unavailable-note-title", "Répartition Local / Gemini / Claude"));
      const list = el("ul", "admin-unavailable-list");
      entries.forEach(([bucket, n]) => {
        list.appendChild(el("li", "admin-unavailable-item", `${engineBucketLabel(bucket)} — ${n} réponse(s)`));
      });
      section.appendChild(list);
      wrap.appendChild(section);
    }
  }

  if (data.history.length) {
    const section = el("div", "admin-unavailable-note");
    section.appendChild(el("h3", "admin-unavailable-note-title", "Historique des conversations"));
    const list = el("ul", "admin-unavailable-list");
    data.history.forEach((c) => {
      list.appendChild(el("li", "admin-unavailable-item", `${c.title} — ${formatDateTime(c.updated_at)}`));
    });
    section.appendChild(list);
    wrap.appendChild(section);
  }

  // ── Consommation IA repliée : allège l'affichage principal, doublon
  // partiel avec le module IA global (admin-ai.js) — vue par utilisateur
  // volontairement conservée, juste moins proéminente. ────────────────────
  wrap.appendChild(collapseSection({
    id: "user-profile-ai-consumption",
    title: "Consommation IA",
    hint: "Requêtes, tokens, coût, fournisseur, historique des appels",
    bodyNode: renderAiConsumptionBody(data),
  }));

  wireCollapsePersistence(wrap);
  return wrap;
}

// ── 4. Support (tickets créés par ce compte, strictement informatif) ──────
function renderSupportTab(data) {
  if (!data.tickets) {
    return emptyState(data.tickets_reason || "Aucun ticket support");
  }

  const table = el("table", "admin-users-table admin-learning-table");
  const theadRow = el("tr");
  ["Sujet", "Catégorie", "Priorité", "Statut", "Créé le", "Mis à jour le"]
    .forEach((label) => theadRow.appendChild(el("th", "admin-users-th", label)));
  const thead = document.createElement("thead");
  thead.appendChild(theadRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  data.tickets.forEach((t) => {
    const tr = el("tr", "admin-users-row");
    tr.appendChild(el("td", "admin-users-td", t.subject));
    tr.appendChild(el("td", "admin-users-td", t.category_label));
    const priorityTd = el("td", "admin-users-td");
    priorityTd.appendChild(priorityBadge(t.priority));
    tr.appendChild(priorityTd);
    const statusTd = el("td", "admin-users-td");
    statusTd.appendChild(statusBadge(t.status));
    tr.appendChild(statusTd);
    tr.appendChild(el("td", "admin-users-td", formatDateTime(t.created_at) || EMPTY_LABEL));
    tr.appendChild(el("td", "admin-users-td", formatDateTime(t.updated_at) || EMPTY_LABEL));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  const wrapTable = el("div", "admin-users-table-wrap");
  wrapTable.appendChild(table);
  return wrapTable;
}

// ── 5. Abonnement ─────────────────────────────────────────────────────────
function renderSubscriptionTab(data) {
  const grid = el("div", "admin-fields-grid");
  grid.appendChild(fieldRow("Plan actuel", data.plan, (v) => PLAN_LABELS[v] || v));
  grid.appendChild(fieldRow("Statut Stripe", data.stripe_subscription_status));
  grid.appendChild(fieldRow("Compte de facturation Stripe", data.has_stripe_customer, (v) => (v ? "Oui" : "Non")));
  return grid;
}

const TAB_RENDERERS = {
  profile: renderProfileTab,
  activity: renderActivityTab,
  chatbot: renderChatbotTab,
  support: renderSupportTab,
  subscription: renderSubscriptionTab,
};

function renderSkeletonPanel(panel) {
  panel.innerHTML = "";
  for (let i = 0; i < 4; i += 1) {
    const bar = el("div", "admin-skeleton admin-tab-skeleton-row");
    panel.appendChild(bar);
  }
}

export async function loadUserProfile(userId) {
  const tabsNav = document.getElementById("admin-user-profile-tabs");
  const panel = document.getElementById("admin-user-profile-panel");
  const cache = new Map(); // un seul appel réseau par onglet, même si on y revient
  let activeTab = "profile";
  let headerRendered = false;

  function renderTabsNav() {
    tabsNav.innerHTML = "";
    TABS.forEach((tab) => {
      const btn = el("button", "admin-tab-btn", tab.label);
      btn.type = "button";
      btn.dataset.tab = tab.id;
      if (tab.id === activeTab) btn.classList.add("is-active");
      btn.addEventListener("click", () => switchTab(tab.id));
      tabsNav.appendChild(btn);
    });
  }

  // Un onglet peut agréger plusieurs API (voir TAB_ENDPOINTS) — toutes
  // déclenchées ensemble, une seule fois, uniquement à l'ouverture de
  // l'onglet qui en a besoin.
  async function fetchTabData(tabId) {
    const endpoints = TAB_ENDPOINTS[tabId];
    const responses = await Promise.all(
      endpoints.map((ep) => fetch(`/api/admin/users/${userId}/${ep}`, { credentials: "same-origin" }))
    );
    if (responses.some((res) => res.status === 404)) {
      return { notFound: true };
    }
    const payloads = await Promise.all(responses.map((res) => res.json().catch(() => ({}))));
    const failedIndex = responses.findIndex((res) => !res.ok);
    if (failedIndex !== -1) {
      throw new Error(payloads[failedIndex].error || `Erreur API (${responses[failedIndex].status})`);
    }
    if (endpoints.length === 1) return payloads[0];
    const combined = {};
    endpoints.forEach((ep, i) => { combined[ep] = payloads[i]; });
    return combined;
  }

  async function switchTab(tabId) {
    activeTab = tabId;
    renderTabsNav();

    if (cache.has(tabId)) {
      renderTabContent(tabId, cache.get(tabId));
      return;
    }

    renderSkeletonPanel(panel);
    try {
      const payload = await fetchTabData(tabId);
      if (payload.notFound) {
        panel.innerHTML = "";
        panel.appendChild(emptyState("Cet utilisateur est introuvable."));
        return;
      }
      cache.set(tabId, payload);
      if (tabId === "profile" && !headerRendered) {
        renderHeader(payload);
        headerRendered = true;
      }
      renderTabContent(tabId, payload);
    } catch {
      panel.innerHTML = "";
      const errorBox = el("p", "admin-empty admin-card-error", "Impossible de charger cet onglet. Réessaie dans un instant.");
      panel.appendChild(errorBox);
    }
  }

  function renderTabContent(tabId, data) {
    panel.innerHTML = "";
    panel.appendChild(TAB_RENDERERS[tabId](data));
  }

  renderTabsNav();
  await switchTab(activeTab);
}
