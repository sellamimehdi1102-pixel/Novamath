import { defineConfig } from "vite";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { cpSync, existsSync } from "node:fs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const staticRoot = resolve(__dirname, "webapp/static");
const outDir = resolve(__dirname, "webapp/static-dist");

// Pages HTML réellement servies (voir server.py) — settings.html.removed est
// volontairement exclu (page retirée, voir server.py::_redirect_legacy_settings_page).
const PAGES = [
  "index.html",
  "dashboard.html",
  "abonnement.html",
  "chatbot.html",
  "chapitres.html",
  "choisir-classe.html",
  "cours.html",
  "exercice.html",
  "profil.html",
  "reset-password.html",
  "parent-consent.html",
  "admin.html",
  "mentions-legales.html",
  "confidentialite.html",
  "cgu.html",
  // Outil de diagnostic temporaire (voir server.py::_serve_debug_runtime),
  // gardé par config.DEBUG côté serveur — jamais accessible en production
  // même si le fichier est présent dans static-dist/.
  "debug-runtime.html",
];

// ── Copie verbatim des ressources hors du graphe de modules/HTML ───────────
// robots.txt, sitemap.xml et data/ (banques de cours, consommées via des URLs
// fetch() littérales côté serveur/JS) doivent conserver un nom de fichier
// STABLE (jamais de hash) : un crawler ou un fetch() vers /data/cours/... ne
// doit jamais casser. Tout le reste (JS/CSS/assets référencés depuis le HTML)
// passe par le pipeline Vite normal (hashé, cache-busté automatiquement).
function copyUnbundledAssets() {
  return {
    name: "novamath-copy-unbundled-assets",
    closeBundle() {
      for (const entry of ["robots.txt", "sitemap.xml", "data"]) {
        const src = resolve(staticRoot, entry);
        if (existsSync(src)) cpSync(src, resolve(outDir, entry), { recursive: true });
      }
    },
  };
}

export default defineConfig(() => ({
  root: staticRoot,
  base: "/",
  plugins: [copyUnbundledAssets()],
  build: {
    outDir,
    emptyOutDir: true,
    // Sourcemaps en développement UNIQUEMENT (voir `npm run dev`, serveur Vite
    // natif ES modules avec sourcemaps implicites) — jamais en build de
    // production, pour ne jamais exposer les sources non minifiées.
    sourcemap: false,
    // esbuild (par défaut) : minification JS/CSS + suppression du code mort
    // (tree shaking Rollup) sans dépendance supplémentaire.
    minify: "esbuild",
    cssMinify: true,
    rollupOptions: {
      input: Object.fromEntries(
        PAGES.map((page) => [page.replace(/\.html$/, ""), resolve(staticRoot, page)]),
      ),
      output: {
        // Cache busting : nom de fichier hashé sur le contenu, réécrit
        // automatiquement dans le HTML de sortie par Vite — jamais de
        // renommage manuel (voir DEPLOYMENT.md).
        entryFileNames: "assets/[name].[hash].js",
        chunkFileNames: "assets/[name].[hash].js",
        assetFileNames: "assets/[name].[hash][extname]",
      },
    },
  },
  test: {
    // `root` (ci-dessus) sert au BUILD (webapp/static/, pages HTML sources) —
    // Vitest doit résoudre `include`/`setupFiles` depuis la racine du dépôt,
    // sinon il les cherche sous webapp/static/webapp/static/... (double
    // préfixe) et ne trouve aucun test. `test.root` prévaut sur `root` pour
    // Vitest uniquement, sans affecter `vite build`/`vite dev`.
    root: __dirname,
    environment: "jsdom",
    globals: true,
    setupFiles: [resolve(__dirname, "webapp/static/js/__tests__/setup.js")],
    include: ["webapp/static/js/__tests__/**/*.test.js"],
    css: false,
    coverage: {
      provider: "v8",
      reportsDirectory: resolve(__dirname, "coverage/frontend"),
      include: ["webapp/static/js/**/*.js"],
      exclude: ["webapp/static/js/__tests__/**", "webapp/static/js/authModalsTemplate.js"],
    },
  },
}));
