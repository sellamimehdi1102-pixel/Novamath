// Collecte de fréquentation Cloudflare Web Analytics — Phase 1 (audit admin,
// 2026-10-2x). Ce module ne fait QUE charger/retirer le script officiel
// Cloudflare selon deux conditions, jamais une seule :
//
// 1. Domaine de PRODUCTION autorisé (jamais localhost, jamais un aperçu de
//    build Vite, jamais l'environnement de test Vitest — tous ont un
//    `location.hostname` différent de PRODUCTION_HOSTNAME).
// 2. Consentement "Statistiques" déjà accordé (catégorie existante de
//    cookieConsent.js, aucune nouvelle bannière/catégorie créée) — par
//    défaut (aucun choix encore fait), le script NE charge PAS : en cas
//    d'incertitude, le consentement préalable est requis, jamais supposé.
//
// Réagit en DIRECT (CustomEvent, voir cookieConsent.js) à un changement de
// consentement fait depuis la bannière OU depuis Paramètres (settings.js) :
// un octroi charge la balise immédiatement, sans attendre un rechargement.
// Un RETRAIT, lui, retire la balise ET force un rechargement contrôlé de la
// page (voir applyConsent() ci-dessous) — un script déjà exécuté ne peut pas
// être arrêté autrement, voir ce commentaire pour le détail.
//
// Aucune donnée personnelle Mathadap n'est jamais transmise à Cloudflare :
// le jeton `data-cf-beacon` n'identifie que la PROPRIÉTÉ "Mathadap" côté
// Cloudflare (valeur publique par design, visible dans le DOM de n'importe
// quel site l'utilisant — ce n'est pas un secret, voir la documentation
// officielle Cloudflare) — jamais un email, un id de compte, un jeton de
// session ni aucun paramètre d'URL applicatif : le script Cloudflare lit
// uniquement location.href/document.referrer tels que fournis par le
// navigateur, ce module ne lui transmet jamais rien explicitement.
//
// Avant d'accepter un retrait de consentement (donc avant le rechargement
// forcé qu'il implique, voir applyConsent() ci-dessous), ce module
// s'enregistre comme garde auprès de cookieConsent.js
// (registerStatisticsWithdrawalGuard) : si une activité non sauvegardée est
// détectée (unsavedActivity.js), l'utilisateur est explicitement prévenu
// avant de perdre quoi que ce soit — voir checkWithdrawalIsSafe() plus bas.
import {
  getCookieConsentChoice,
  COOKIE_CONSENT_CHANGED_EVENT,
  registerStatisticsWithdrawalGuard,
} from "./cookieConsent.js";
import { hasUnsavedActivity } from "./unsavedActivity.js";

// Domaine public exact de production (voir config.APP_BASE_URL côté
// backend, "https://mathadap.com", jamais de variante "www." utilisée dans
// ce projet) — comparaison stricte, jamais un .includes()/.endsWith() qui
// matcherait aussi un sous-domaine ou un domaine de phishing ressemblant.
const PRODUCTION_HOSTNAME = "mathadap.com";

const BEACON_SCRIPT_ID = "cf-web-analytics-beacon";
const BEACON_SRC = "https://static.cloudflareinsights.com/beacon.min.js";
// Jeton Cloudflare de la propriété "Mathadap" — public par design (voir
// docstring ci-dessus), jamais un secret à masquer.
const BEACON_TOKEN = "0d93ead3b2ea4804a41fdff82b7087b8";

function isProductionDomain() {
  return window.location.hostname === PRODUCTION_HOSTNAME;
}

function loadBeacon() {
  if (document.getElementById(BEACON_SCRIPT_ID)) return; // jamais deux fois sur la même page
  const script = document.createElement("script");
  script.id = BEACON_SCRIPT_ID;
  script.type = "module";
  script.src = BEACON_SRC;
  script.setAttribute("data-cf-beacon", JSON.stringify({ token: BEACON_TOKEN }));
  document.head.appendChild(script);
}

function removeBeacon() {
  // Retire la balise pour qu'aucun NOUVEAU chargement n'ait lieu sur cette
  // page, et pour repartir d'un état propre si le consentement est ensuite
  // ré-accordé (loadBeacon() pourra alors réinjecter la balise). Renvoie
  // `true` si une balise a réellement été retirée : voir applyConsent()
  // ci-dessous, c'est ce qui distingue un retrait qui doit déclencher un
  // rechargement (le script tournait déjà) d'un retrait qui ne change rien
  // (le script n'avait jamais été chargé sur cette page).
  const existing = document.getElementById(BEACON_SCRIPT_ID);
  if (!existing) return false;
  existing.remove();
  return true;
}

// Retirer la balise <script> n'arrête PAS le code déjà en cours d'exécution :
// une fois chargé, beacon.min.js enregistre ses propres écouteurs
// (visibilitychange, pagehide, et une surcharge de history.pushState/
// replaceState pour détecter les changements de route d'une SPA) afin
// d'envoyer d'autres évènements plus tard sur la même page — retirer le noeud
// DOM ne défait aucun de ces écouteurs/surcharges déjà en place (vérifié :
// Cloudflare ne documente aucune API publique d'arrêt/désinscription pour
// Web Analytics). La seule garantie fiable contre un nouvel envoi après un
// retrait de consentement est donc de repartir d'un contexte JavaScript
// totalement neuf : un rechargement de la page. Le choix retiré est déjà en
// localStorage AVANT ce rechargement (voir cookieConsent.js::storeConsent,
// appelé avant la diffusion de l'évènement lu ici) donc il n'est jamais
// perdu — au prochain chargement, applyConsent() relit ce choix et ne
// réinjecte pas la balise.
function applyConsent(choice) {
  if (!isProductionDomain()) return; // jamais en dev/preview/CI, quel que soit le consentement
  if (choice && choice.statistics) {
    loadBeacon();
  } else if (removeBeacon()) {
    // Uniquement si la balise était réellement présente : un retrait de
    // consentement alors que le script n'avait jamais été chargé (ex.
    // consentement déjà refusé, ou chargement initial de la page) ne
    // déclenche jamais de rechargement — sinon chaque chargement de page
    // avec consentement refusé boucle sur lui-même (bug de boucle de
    // rechargement infinie, à éviter absolument).
    window.location.reload();
  }
}

applyConsent(getCookieConsentChoice());

window.addEventListener(COOKIE_CONSENT_CHANGED_EVENT, (event) => {
  applyConsent(event.detail);
});

// Garde appelée par cookieConsent.js::storeConsent AVANT tout retrait du
// consentement "statistiques" (donc avant que l'évènement ci-dessus ne soit
// jamais diffusé pour ce retrait) — voir registerStatisticsWithdrawalGuard.
// Renvoie `true` pour laisser le retrait avoir lieu (et donc, juste après,
// le rechargement ci-dessus), `false` pour l'annuler entièrement (le
// consentement reste alors inchangé, aucun effet de bord).
function checkWithdrawalIsSafe() {
  // Rien à perdre si aucun rechargement ne serait de toute façon déclenché :
  // hors production (voir applyConsent), ou balise jamais chargée sur cette
  // page (consentement déjà refusé, ou jamais encore accordé ici).
  if (!isProductionDomain() || !document.getElementById(BEACON_SCRIPT_ID)) return true;
  if (!hasUnsavedActivity()) return true;
  return window.confirm(
    "Retirer ton consentement aux cookies statistiques nécessite de recharger la page. " +
      "Une activité en cours (par exemple un message en cours de rédaction) serait perdue. " +
      "Continuer et recharger maintenant ?",
  );
}

registerStatisticsWithdrawalGuard(checkWithdrawalIsSafe);
