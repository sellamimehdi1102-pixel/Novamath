// Chargement des comptes d'équipe assignables (support/moderator/admin/
// super_admin) — factorisé depuis admin-support.js (filtre "Assigné" du
// tableau) et admin-support-ticket.js (dropdown d'assignation de la fiche),
// qui dupliquaient exactement les mêmes 4 requêtes en parallèle et la même
// fusion/déduplication par id. Même comportement qu'avant : même rôles, même
// endpoint, même page_size, mêmes permissions (déjà tranchées côté backend
// par /api/admin/users), même gestion d'erreur silencieuse (Map vide si une
// requête échoue).
export const TEAM_ROLES = ["support", "moderator", "admin", "super_admin"];

/** Renvoie une Map<id, name> des comptes d'équipe (union des 4 rôles,
 * dédupliquée). Peut lever une exception sur une panne réseau — laissée à
 * chaque appelant, qui garde son propre try/catch et son propre message de
 * repli (les deux pages affichaient un texte différent en cas d'échec avant
 * ce chantier ; ce module ne doit pas uniformiser silencieusement ça). */
export async function fetchTeamMembers() {
  const responses = await Promise.all(
    TEAM_ROLES.map((role) => fetch(`/api/admin/users?role=${role}&page_size=100`, { credentials: "same-origin" })),
  );
  const payloads = await Promise.all(responses.map((r) => (r.ok ? r.json() : { items: [] })));
  const admins = new Map();
  payloads.forEach((p) => (p.items || []).forEach((u) => admins.set(u.id, u.name)));
  return admins;
}
