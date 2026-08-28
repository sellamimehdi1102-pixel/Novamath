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

function storeConsent(statistics, marketing) {
  const payload = { statistics, marketing, version: CONSENT_VERSION, decided_at: new Date().toISOString() };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  // Best-effort : un visiteur anonyme n'a pas de session, la requête échoue
  // silencieusement (401) sans jamais bloquer le bandeau côté client.
  api.setCookieConsent(statistics, marketing).catch(() => {});
}

function mountBanner() {
  if (document.getElementById("cookie-consent-banner")) return;
  const el = document.createElement("div");
  el.id = "cookie-consent-banner";
  el.className = "card cookie-banner";
  el.innerHTML = `
    <p>
      NovaMath utilise des cookies nécessaires au fonctionnement du site, ainsi que
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

  const close = () => el.remove();

  document.getElementById("cookie-banner-customize-link").addEventListener("click", () => {
    document.getElementById("cookie-banner-categories").hidden = false;
    document.getElementById("cookie-banner-save").hidden = false;
  });
  document.getElementById("cookie-banner-accept-all").addEventListener("click", () => {
    storeConsent(true, true);
    close();
  });
  document.getElementById("cookie-banner-reject-all").addEventListener("click", () => {
    storeConsent(false, false);
    close();
  });
  document.getElementById("cookie-banner-save").addEventListener("click", () => {
    storeConsent(
      document.getElementById("cookie-banner-statistics").checked,
      document.getElementById("cookie-banner-marketing").checked,
    );
    close();
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

export function openCookiePreferences() {
  localStorage.removeItem(STORAGE_KEY);
  mountBanner();
}
