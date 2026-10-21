// Bannière de consentement cookies (RGPD) — SEC-04. Importée depuis auth.js
// (chargé sur toutes les pages) pour n'avoir qu'une seule source de vérité,
// jamais une copie de balise <script> par page HTML. Le choix est conservé en
// localStorage (fonctionne pour un visiteur anonyme, avant tout compte) et,
// si un compte est connecté, également synchronisé côté serveur (voir
// consent_service.py) pour rester modifiable depuis Paramètres.
import { api } from "./api.js";

const STORAGE_KEY = "nm_cookie_consent";
const CONSENT_VERSION = "1";

function readStoredConsent() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && parsed.version === CONSENT_VERSION ? parsed : null;
  } catch {
    return null;
  }
}

// Nom de l'événement DOM diffusé à CHAQUE changement de consentement, qu'il
// vienne de la bannière (ce fichier) ou de la page Paramètres (settings.js,
// qui appelle setCookieConsentChoice ci-dessous plutôt que de dupliquer sa
// propre écriture localStorage — un seul point d'écriture, jamais deux
// sources qui pourraient diverger). Permet à un module comme
// analyticsBeacon.js de réagir immédiatement à un retrait de consentement
// SANS rechargement de page, plutôt que de ne relire ce choix qu'au prochain
// chargement de script.
const CONSENT_CHANGED_EVENT = "mathadap:cookie-consent-changed";

// Garde optionnelle appelée AVANT tout retrait du consentement "statistiques"
// (voir storeConsent ci-dessous) — enregistrée par analyticsBeacon.js (seul
// module aujourd'hui dont le retrait de consentement a une conséquence qui
// justifie de prévenir l'utilisateur : un rechargement de page, voir ce
// fichier). Un seul emplacement (pas une liste) : volontairement, il n'existe
// qu'UN SEUL retrait possible du consentement statistiques dans ce projet
// (rechargement Cloudflare) — inutile d'anticiper plusieurs gardes
// concurrentes pour un besoin qui n'existe pas encore. `null` = aucune garde
// (comportement inchangé, retrait toujours accepté).
let withdrawalGuard = null;

/** Enregistre `fn` comme garde appelée synchrone avant tout retrait du
 * consentement "statistiques" (passage de accordé à refusé). `fn` doit
 * renvoyer `true` pour laisser le retrait avoir lieu, `false` pour l'annuler
 * (le consentement reste alors inchangé — ni écrit en localStorage, ni
 * envoyé au serveur, ni diffusé). Un appel ultérieur remplace la garde
 * précédente (jamais d'accumulation). */
export function registerStatisticsWithdrawalGuard(fn) {
  withdrawalGuard = fn;
}

/** Renvoie `true` si le choix a bien été enregistré, `false` si une garde a
 * annulé le retrait (voir registerStatisticsWithdrawalGuard ci-dessus) — dans
 * ce second cas, AUCUN effet de bord n'a eu lieu : ni localStorage, ni appel
 * serveur, ni évènement diffusé, le consentement précédent reste pleinement
 * en vigueur. */
function storeConsent(statistics, marketing) {
  if (!statistics && withdrawalGuard && !withdrawalGuard()) {
    return false;
  }
  const payload = { statistics, marketing, version: CONSENT_VERSION, decided_at: new Date().toISOString() };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  // Best-effort : un visiteur anonyme n'a pas de session, la requête échoue
  // silencieusement (401) sans jamais bloquer le bandeau côté client.
  api.setCookieConsent(statistics, marketing).catch(() => {});
  window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics, marketing } }));
  return true;
}

// La bannière est en position:fixed (voir .cookie-banner, base.css) et ne
// fait donc partie d'aucun flux de page : sans réservation d'espace, elle
// se pose par-dessus la dernière carte visible dès que le contenu de la
// page s'arrête à peu près à sa hauteur (mobile, page courte) — bug
// confirmé (ex. carte "Exercice sur mesure" sur exercice.html à 435×919,
// 480×900, 568×900 ; reproductible sur n'importe quelle page dans les
// mêmes conditions, le défaut n'a rien de spécifique à cette carte).
//
// Deux corrections combinées :
// 1. padding-bottom (via variable CSS) pour que la page laisse toujours la
//    place nécessaire une fois défilée jusqu'en bas.
// 2. un ajustement du défilement initial, pour que le contenu déjà visible
//    À L'ÉCRAN au chargement ne se retrouve jamais sous le bandeau — un
//    ResizeObserver recalcule cet ajustement à chaque fois que la hauteur
//    réelle de la page change, car certaines cartes (ex. "Exercice sur
//    mesure", customExercise.js) se chargent de façon asynchrone : leur
//    hauteur finale n'est pas encore connue au moment où le bandeau se
//    monte, un calcul figé une seule fois au montage sous-estime alors le
//    recouvrement réel (bug confirmé : 15px du texte encore caché à
//    480×900 avec un ajustement figé).
// Distingue un défilement réel de l'utilisateur de nos propres ajustements
// par comparaison directe de position (pas un flag temporisé) : un flag
// remis à zéro sur un rAF/timeout peut se réinitialiser AVANT que l'event
// "scroll" déclenché par notre propre window.scrollBy ne soit livré par le
// navigateur (ordre non garanti), ce qui marquait alors à tort certains
// ajustements comme un geste utilisateur — bug confirmé (échec intermittent
// à 320×568, où le ResizeObserver ne pouvait plus se corriger ensuite).
let userHasScrolled = false;
let lastProgrammaticY = null;
window.addEventListener(
  "scroll",
  () => {
    if (lastProgrammaticY !== null && Math.abs(window.scrollY - lastProgrammaticY) < 1) return;
    userHasScrolled = true;
  },
  { passive: true },
);

function syncBannerSpace(el) {
  const bannerRect = el.getBoundingClientRect();
  // +32px = même écart que le bottom:16px du bandeau (base.css), reproduit
  // en haut pour un espacement symétrique — pas une valeur arbitraire.
  const extra = Math.ceil(bannerRect.height) + 32;
  document.body.style.setProperty("--cookie-banner-space", `${extra}px`);
  document.body.classList.add("has-cookie-banner");

  if (userHasScrolled) return; // on ne touche jamais au défilement choisi par l'utilisateur

  // Hauteur réelle du contenu, sans compter le padding-bottom qu'on vient
  // nous-mêmes d'ajouter (sinon il fausserait la mesure de recouvrement).
  const rawContentHeight = document.documentElement.scrollHeight - extra;

  // Ce correctif ne concerne QUE les pages "courtes" (contenu tenant déjà
  // entièrement dans le viewport, sans aucun défilement possible AVANT que
  // le padding-bottom ci-dessus n'en crée un) — c'est le seul cas où du
  // contenu déjà visible à l'écran peut se retrouver masqué sans qu'aucun
  // geste de l'utilisateur ne permette de le révéler (voir repro en tête de
  // fichier). Sur une page plus longue que le viewport, le padding-bottom
  // réserve déjà la place nécessaire pour qu'un défilement NATUREL jusqu'en
  // bas révèle tout le contenu au-dessus du bandeau — sans ce garde-fou,
  // chaque recalcul du ResizeObserver (déclenché par le chargement
  // asynchrone du contenu réel d'une page comme dashboard.html, bien plus
  // haute que le viewport) comparait à tort la hauteur TOTALE du document à
  // la position du bandeau (limitée, elle, au viewport) et forçait un
  // défilement massif et non sollicité dès le premier chargement — bug
  // confirmé : sur dashboard.html, la sidebar (position:sticky, voir
  // base.css) sort alors de sa zone d'ancrage et semble "collée" tout en
  // bas de la page au lieu de rester visible en haut, puisque le viewport
  // se retrouve défilé bien au-delà de ce que .app-shell peut encore
  // ancrer. Spécifique au rail desktop (position:sticky) : le drawer
  // mobile (position:fixed + transform, voir responsive.css) n'est jamais
  // concerné, quel que soit le défilement de la page.
  if (rawContentHeight > window.innerHeight) return;

  const overlap = rawContentHeight - window.scrollY - bannerRect.top;
  if (overlap > 0) {
    window.scrollBy(0, overlap);
    lastProgrammaticY = window.scrollY;
  }
}

function reserveSpaceForBanner(el) {
  syncBannerSpace(el);
  // ResizeObserver est absent de l'environnement de test (jsdom) : la
  // réservation d'espace au montage (syncBannerSpace ci-dessus) reste
  // fonctionnelle sans lui, seul le recalcul sur croissance asynchrone du
  // contenu (ex. carte chargée après coup) ne s'applique pas.
  if (!el.__resizeObserver && typeof ResizeObserver !== "undefined") {
    el.__resizeObserver = new ResizeObserver(() => syncBannerSpace(el));
    el.__resizeObserver.observe(document.body);
  }
}

function releaseSpaceForBanner(el) {
  el.__resizeObserver?.disconnect();
  document.body.classList.remove("has-cookie-banner");
  document.body.style.removeProperty("--cookie-banner-space");
}

function mountBanner() {
  if (document.getElementById("cookie-consent-banner")) return;
  const el = document.createElement("div");
  el.id = "cookie-consent-banner";
  el.className = "card cookie-banner";
  el.innerHTML = `
    <p>
      Mathadap utilise des cookies nécessaires au fonctionnement du site, ainsi que
      (avec ton accord) des cookies de mesure d'audience et marketing.
      <button type="button" class="link-inline" id="cookie-banner-customize-link">Personnaliser</button>
    </p>
    <div class="cookie-banner-categories" id="cookie-banner-categories" hidden>
      <label class="cookie-banner-category"><input type="checkbox" checked disabled> Nécessaires (toujours actifs)</label>
      <label class="cookie-banner-category"><input type="checkbox" id="cookie-banner-statistics"> Statistiques</label>
      <label class="cookie-banner-category"><input type="checkbox" id="cookie-banner-marketing"> Marketing</label>
    </div>
    <div class="cookie-banner-actions">
      <button type="button" class="btn btn-secondary btn-sm" id="cookie-banner-reject-all">Tout refuser</button>
      <button type="button" class="btn btn-secondary btn-sm" id="cookie-banner-save" hidden>Enregistrer mes choix</button>
      <button type="button" class="btn btn-primary btn-sm" id="cookie-banner-accept-all">Tout accepter</button>
    </div>
  `;
  document.body.appendChild(el);
  reserveSpaceForBanner(el);

  const close = () => {
    el.remove();
    releaseSpaceForBanner(el);
  };

  document.getElementById("cookie-banner-customize-link").addEventListener("click", () => {
    document.getElementById("cookie-banner-categories").hidden = false;
    document.getElementById("cookie-banner-save").hidden = false;
    // Le bandeau grandit (catégories + bouton "Enregistrer" révélés) :
    // recalcule l'espace réservé sur sa nouvelle hauteur réelle.
    reserveSpaceForBanner(el);
  });
  // `close()` uniquement si storeConsent() a réellement écrit le choix — une
  // garde (voir registerStatisticsWithdrawalGuard) peut annuler un retrait
  // de consentement "statistiques" (activité non sauvegardée en cours,
  // réponse déclinée par l'utilisateur) : le bandeau reste alors ouvert,
  // AUCUN choix n'est changé, l'utilisateur peut réessayer ou renoncer.
  document.getElementById("cookie-banner-accept-all").addEventListener("click", () => {
    if (storeConsent(true, true)) close();
  });
  document.getElementById("cookie-banner-reject-all").addEventListener("click", () => {
    if (storeConsent(false, false)) close();
  });
  document.getElementById("cookie-banner-save").addEventListener("click", () => {
    if (
      storeConsent(
        document.getElementById("cookie-banner-statistics").checked,
        document.getElementById("cookie-banner-marketing").checked,
      )
    ) {
      close();
    }
  });
}

// Ne s'affiche jamais si un choix (à jour) est déjà enregistré — c'est la
// règle centrale du consentement cookies RGPD.
if (!readStoredConsent()) {
  mountBanner();
}

export function getCookieConsentChoice() {
  return readStoredConsent();
}

// Point d'écriture UNIQUE du consentement (bannière ci-dessus ET page
// Paramètres, voir settings.js) — avant ce chantier, settings.js appelait
// directement api.setCookieConsent() sans jamais mettre à jour le
// localStorage lu par ce module, donc un retrait de consentement fait
// depuis Paramètres restait invisible pour tout script gated sur ce choix
// (ex: analyticsBeacon.js) tant que la page n'était pas rechargée ET que la
// bannière ne se réaffichait pas (ce qu'elle ne fait jamais si un choix,
// même périmé, est déjà stocké). Audit admin (2026-10-2x), intégration
// Cloudflare Web Analytics.
//
// Renvoie `true` si le choix a bien été écrit, `false` si une garde l'a
// annulé (voir registerStatisticsWithdrawalGuard/storeConsent) — settings.js
// utilise cette valeur pour rétablir visuellement la case à cocher si
// l'utilisateur renonce au retrait.
export function setCookieConsentChoice(statistics, marketing) {
  return storeConsent(statistics, marketing);
}

export const COOKIE_CONSENT_CHANGED_EVENT = CONSENT_CHANGED_EVENT;

export function openCookiePreferences() {
  localStorage.removeItem(STORAGE_KEY);
  mountBanner();
}
