import { api } from "./api.js";

const $ = (id) => document.getElementById(id);

// Le jeton fait partie du chemin (/parent/consent/<token>), jamais d'une
// query string — voir server.py::parent_consent_page.
const token = window.location.pathname.split("/").filter(Boolean).pop();

function showOnly(id) {
  ["consent-loading", "consent-pending", "consent-accepted", "consent-refused", "consent-invalid"]
    .forEach((sectionId) => { $(sectionId).hidden = sectionId !== id; });
}

async function loadStatus() {
  if (!token) {
    showOnly("consent-invalid");
    return;
  }
  try {
    const info = await api.getParentalConsentStatus(token);
    if (info.status === "accepted") {
      showOnly("consent-accepted");
    } else if (info.status === "refused") {
      showOnly("consent-refused");
    } else if (info.expired) {
      showOnly("consent-invalid");
    } else {
      $("consent-child-pseudo").textContent = info.child_pseudo || "";
      $("consent-expires-at").textContent = new Date(info.expires_at).toLocaleDateString("fr-FR");
      showOnly("consent-pending");
    }
  } catch {
    showOnly("consent-invalid");
  }
}

async function resolve(decision) {
  const errorEl = $("consent-error");
  errorEl.hidden = true;
  $("btn-consent-accept").disabled = true;
  $("btn-consent-refuse").disabled = true;
  try {
    if (decision === "accepted") {
      await api.acceptParentalConsent(token);
      showOnly("consent-accepted");
    } else {
      await api.refuseParentalConsent(token);
      showOnly("consent-refused");
    }
  } catch (err) {
    errorEl.textContent = err.message || "Une erreur est survenue.";
    errorEl.hidden = false;
    $("btn-consent-accept").disabled = false;
    $("btn-consent-refuse").disabled = false;
  }
}

$("btn-consent-accept").addEventListener("click", () => resolve("accepted"));
$("btn-consent-refuse").addEventListener("click", () => resolve("refused"));

loadStatus();
