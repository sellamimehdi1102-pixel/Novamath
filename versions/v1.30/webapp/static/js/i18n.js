// ── i18n minimal, sans build step — dictionnaires plats + attribut data-i18n ─
// getSettings().language ("fr"|"en") pilote la langue active (SettingsManager,
// persistée côté serveur). applyTranslations() parcourt le DOM et remplace le
// texte de tout élément annoté [data-i18n="clé"] — voir settingsPopup.js et
// les scripts de page pour les points d'appel. Le contenu des exercices
// (énoncés, indices, corrections) n'est JAMAIS concerné : ce module ne touche
// que les libellés d'interface (nav, boutons, titres, messages système).
import { getSettings, onSettingsChange } from "./settingsManager.js";

const DICT = {
  fr: {
    "nav.dashboard": "Dashboard",
    "nav.exercices": "Exercices",
    "nav.cours": "Cours",
    "nav.entrainement": "Entraînement",
    "nav.chatbot": "Chatbot",
    "nav.profil": "Voir le profil",
    "settings.title": "Paramètres",
    "settings.cat.account": "Compte",
    "settings.cat.appearance": "Apparence",
    "settings.cat.training": "Entraînement",
    "settings.cat.learning": "Apprentissage",
    "settings.cat.data": "Données",
    "settings.cat.security": "Confidentialité & Sécurité",
    "settings.cat.language": "Langue",
    "settings.cat.chatbot": "Chatbot",
    "settings.cat.help": "Aide & À propos",
    "exercise.notice_fr_only": "Le contenu des exercices reste en français quelle que soit la langue de l'interface.",
  },
  en: {
    "nav.dashboard": "Dashboard",
    "nav.exercices": "Exercises",
    "nav.cours": "Courses",
    "nav.entrainement": "Practice",
    "nav.chatbot": "Chatbot",
    "nav.profil": "View profile",
    "settings.title": "Settings",
    "settings.cat.account": "Account",
    "settings.cat.appearance": "Appearance",
    "settings.cat.training": "Practice",
    "settings.cat.learning": "Learning",
    "settings.cat.data": "Data",
    "settings.cat.security": "Privacy & Security",
    "settings.cat.language": "Language",
    "settings.cat.chatbot": "Chatbot",
    "settings.cat.help": "Help & About",
    "exercise.notice_fr_only": "Exercise content stays in French regardless of the interface language.",
  },
};

export function currentLanguage() {
  const lang = getSettings()?.language;
  return lang === "en" ? "en" : "fr";
}

export function t(key, fallback) {
  const lang = currentLanguage();
  return DICT[lang]?.[key] ?? DICT.fr[key] ?? fallback ?? key;
}

/** Parcourt `root` et remplace le texte de tout [data-i18n], et l'attribut
 * ciblé par [data-i18n-attr] (ex: placeholder) si présent. */
export function applyTranslations(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const attr = el.getAttribute("data-i18n-attr");
    const value = t(key);
    if (attr) el.setAttribute(attr, value);
    else el.textContent = value;
  });
  document.documentElement.setAttribute("lang", currentLanguage());
}

/** Réapplique automatiquement les traductions dès que la préférence de langue
 * change, sans reload (voir SettingsManager). À appeler une fois par page. */
export function bindLiveTranslations(root = document) {
  applyTranslations(root);
  onSettingsChange((e) => {
    if (e.detail.category === "language" || e.detail.category === "*") applyTranslations(root);
  });
}
