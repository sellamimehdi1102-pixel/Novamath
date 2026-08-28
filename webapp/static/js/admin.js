// Point d'entrée de toute page /admin/* — initialise le shell (sidebar,
// header, navigation interne). Aucune vérification de permission ici : le
// serveur a déjà tranché (login_required_page + requires_role sur chaque
// route Flask /admin/*) avant même que ce fichier ne se charge.
import { initAdminShell } from "./admin-shell.js";

initAdminShell();
