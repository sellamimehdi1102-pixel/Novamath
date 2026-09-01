// ── Pages légales publiques (mentions-legales/confidentialite/cgu.html) ────
// Script minimal et autonome : ces pages sont servies par le handler statique
// par défaut de Flask (jamais _serve_protected()), donc SANS nonce CSP — un
// script inline y serait bloqué par script-src 'self' (voir
// security_headers_service.build_csp(), jamais de 'unsafe-inline'). D'où ce
// fichier externe plutôt qu'un <script> inline dans chaque page.
import { initTheme, bindThemeToggle } from "./theme.js";

initTheme();
bindThemeToggle(document.getElementById("theme-toggle"));
