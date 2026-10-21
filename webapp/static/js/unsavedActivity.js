// ── Registre générique d'activité non sauvegardée ──────────────────────────
// Né du besoin suivant : analyticsBeacon.js doit parfois recharger la page
// (seule façon fiable d'arrêter Cloudflare Web Analytics après un retrait de
// consentement, voir ce fichier) — mais ne doit jamais le faire sans prévenir
// si cela ferait perdre une donnée non sauvegardée (ex. un message en cours
// de rédaction dans le chatbot). Plutôt que de faire connaître à
// analyticsBeacon.js les détails de chaque page (chatbot, exercice,
// paramètres...), ce module fournit un point de rendez-vous générique :
// n'importe quel module peut s'enregistrer ici pour déclarer "j'ai parfois
// une activité non sauvegardée", et n'importe quel module peut demander
// "y a-t-il, ACTUELLEMENT, une activité non sauvegardée sur cette page ?"
// sans que les deux aient besoin de se connaître.
//
// Volontairement PAS un mécanisme de sauvegarde (aucune donnée n'est jamais
// écrite ici) : seulement une détection, pour permettre une confirmation
// avant une action destructive (rechargement) — jamais une persistance
// parallèle à celle déjà existante (store.js::saveInProgressSeries, etc.).
const checks = new Map();

/** Enregistre une fonction de détection sous un nom unique. `fn` doit être
 * synchrone et renvoyer un booléen ("y a-t-il une activité non sauvegardée
 * en ce moment précis ?"). Appeler une seconde fois avec le même `name`
 * remplace la fonction précédente (jamais d'accumulation silencieuse si un
 * module se réenregistre, ex. en test). */
export function registerUnsavedActivityCheck(name, fn) {
  checks.set(name, fn);
}

/** Retire une détection précédemment enregistrée (ex. démontage d'un
 * composant). Sans effet si `name` n'est pas enregistré. */
export function unregisterUnsavedActivityCheck(name) {
  checks.delete(name);
}

/** Vrai si AU MOINS une détection enregistrée signale une activité non
 * sauvegardée. Une détection qui lève une exception est ignorée (jamais une
 * erreur dans un module tiers ne doit bloquer entièrement ce mécanisme) et
 * compte comme "rien à signaler" de sa part. */
export function hasUnsavedActivity() {
  for (const fn of checks.values()) {
    try {
      if (fn()) return true;
    } catch {
      // Détection défaillante : ignorée, jamais bloquante pour les autres.
    }
  }
  return false;
}
