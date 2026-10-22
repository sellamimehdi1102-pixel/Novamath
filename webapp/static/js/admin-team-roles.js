// Chargement des comptes d'équipe assignables (support/moderator/admin/
// super_admin) — factorisé depuis admin-support.js (filtre "Assigné" du
// tableau) et admin-support-ticket.js (dropdown d'assignation de la fiche),
// qui dupliquaient exactement les mêmes 4 requêtes en parallèle et la même
// fusion/déduplication par id.
//
// Audit admin (2026-10-20), point 4 : avant ce chantier, une réponse HTTP en
// échec (ex: 500) pour UN SEUL des 4 rôles était remplacée silencieusement
// par une liste vide, fusionnée avec les 3 autres sans aucun signal — un
// admin pouvait croire qu'un rôle entier n'avait aucun membre alors que
// l'appel avait simplement échoué. `fetchTeamMembers()` renvoie désormais
// `{ admins, failedRoles, incompleteRoles }` : les échecs HTTP et la
// troncature par `page_size=100` (détectée via `total` déjà renvoyé par
// GET /api/admin/users, jamais une heuristique) sont toujours signalés à
// l'appelant, qui décide de l'affichage (texte d'erreur + bouton Réessayer).
export const TEAM_ROLES = ["support", "moderator", "admin", "super_admin"];
const PAGE_SIZE = 100;

/** Renvoie { admins: Map<id, name>, failedRoles: string[], incompleteRoles:
 * string[] }. Une panne RÉSEAU (fetch rejeté, pas juste un statut HTTP en
 * échec) continue de se propager comme une exception — laissée à chaque
 * appelant, qui garde son propre try/catch et son propre message de repli
 * (comportement inchangé, voir la docstring historique de ce module). */
export async function fetchTeamMembers() {
  const responses = await Promise.all(
    TEAM_ROLES.map((role) =>
      fetch(`/api/admin/users?role=${role}&page_size=${PAGE_SIZE}`, { credentials: "same-origin" }),
    ),
  );
  const admins = new Map();
  const failedRoles = [];
  const incompleteRoles = [];

  await Promise.all(
    responses.map(async (r, i) => {
      const role = TEAM_ROLES[i];
      if (!r.ok) {
        failedRoles.push(role);
        return;
      }
      const payload = await r.json().catch(() => null);
      if (!payload || !Array.isArray(payload.items)) {
        failedRoles.push(role);
        return;
      }
      payload.items.forEach((u) => admins.set(u.id, u.name));
      if (typeof payload.total === "number" && payload.total > payload.items.length) {
        incompleteRoles.push(role);
      }
    }),
  );

  return { admins, failedRoles, incompleteRoles };
}

const TEAM_ROLE_LABELS = { support: "Support", moderator: "Modérateur", admin: "Admin", super_admin: "Super admin" };

/** Message explicite à afficher à l'admin (jamais un échec silencieux),
 * ou null si tout s'est chargé correctement et complètement. Factorisé ici
 * pour que les deux appelants (admin-support.js/admin-support-ticket.js)
 * affichent exactement le même texte. */
export function describeTeamLoadIssues(failedRoles, incompleteRoles) {
  const parts = [];
  if (failedRoles.length > 0) {
    const labels = failedRoles.map((r) => TEAM_ROLE_LABELS[r] || r).join(", ");
    parts.push(`Liste incomplète : le chargement a échoué pour ${labels}.`);
  }
  if (incompleteRoles.length > 0) {
    const labels = incompleteRoles.map((r) => TEAM_ROLE_LABELS[r] || r).join(", ");
    parts.push(`Plus de ${PAGE_SIZE} comptes existent pour ${labels} : seuls les ${PAGE_SIZE} premiers sont proposés.`);
  }
  return parts.length > 0 ? parts.join(" ") : null;
}
