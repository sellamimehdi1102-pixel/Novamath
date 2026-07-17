import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import globals from "globals";

// Globales injectées par Vitest à l'exécution (voir vite.config.js::test.globals)
// — jamais résolues statiquement par ESLint, donc déclarées ici pour éviter de
// faux positifs no-undef dans les fichiers de tests.
const vitestGlobals = {
  describe: "readonly", it: "readonly", test: "readonly", expect: "readonly",
  vi: "readonly", beforeEach: "readonly", afterEach: "readonly",
  beforeAll: "readonly", afterAll: "readonly",
};

// ── Lint frontend (ESLint 9, config plate) ─────────────────────────────────
// Périmètre : webapp/static/js/ uniquement (voir package.json::scripts.lint).
// Bloquant en CI (voir .github/workflows/ci.yml, job "frontend").
export default [
  js.configs.recommended,
  {
    files: ["webapp/static/js/**/*.js"],
    ignores: ["webapp/static/js/__tests__/**"],
    plugins: { import: importPlugin },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser },
    },
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-debugger": "error",
      // Autorisé en développement (diagnostics ponctuels), interdit dans le
      // code livré en production — voir NODE_ENV, appliqué par la CI qui
      // construit avec `vite build` (mode production par défaut).
      "no-console": process.env.NODE_ENV === "production" ? "error" : "warn",
      "no-unreachable": "error",
      "no-duplicate-imports": "error",
      "no-dupe-keys": "error",
      "no-dupe-else-if": "error",
      "no-self-compare": "error",
      "import/no-unresolved": "error",
      "import/no-duplicates": "error",
      "import/no-self-import": "error",
      "import/no-cycle": "warn",
    },
  },
  {
    files: ["webapp/static/js/__tests__/**/*.js"],
    plugins: { import: importPlugin },
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.browser, ...globals.node, ...vitestGlobals },
    },
    rules: {
      "no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
  {
    files: ["*.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: { ...globals.node },
    },
  },
];
