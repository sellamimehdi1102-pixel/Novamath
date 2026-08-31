// ── Modales d'authentification (Inscription/Connexion/Mot de passe oublié/
// mentions légales/confidentialité) — extraites de index.html pour pouvoir
// être injectées par auth.js sur N'IMPORTE QUELLE page (dashboard, chapitres,
// entraînement, profil...), notamment pour le mode invité : "Créer un
// compte"/"Se connecter" doivent ouvrir EXACTEMENT les mêmes fenêtres partout,
// une seule source de vérité au lieu d'une copie par page.
export const AUTH_MODALS_HTML = `
<div class="modal-overlay" id="signup-modal-overlay" hidden>
  <div class="modal-card modal-card--wide card">
    <form id="signup-form" novalidate>
      <h3>Créer un compte</h3>

      <button type="button" class="btn btn-google" id="btn-google-signup">
        <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
          <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62Z"/>
          <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18Z"/>
          <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.03l2.97-2.33Z"/>
          <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.97L3.95 7.3C4.66 5.17 6.65 3.58 9 3.58Z"/>
        </svg>
        Continuer avec Google
      </button>
      <div class="auth-divider"><span>ou avec ton email</span></div>

      <div class="form-field">
        <label for="signup-email">Adresse Gmail</label>
        <input type="email" id="signup-email" autocomplete="email" placeholder="nom@gmail.com">
        <span class="form-error" id="signup-error-email" hidden></span>
      </div>
      <div class="form-row">
        <div class="form-field">
          <label for="signup-username">Nom d'utilisateur</label>
          <input type="text" id="signup-username" autocomplete="username" maxlength="25">
          <span class="form-error" id="signup-error-username" hidden></span>
        </div>
        <div class="form-field">
          <label for="signup-pseudo">Pseudo (nom affiché)</label>
          <input type="text" id="signup-pseudo" maxlength="30">
          <span class="form-error" id="signup-error-pseudo" hidden></span>
        </div>
      </div>
      <div class="form-field">
        <label for="signup-password">Mot de passe</label>
        <div class="password-field">
          <input type="password" id="signup-password" autocomplete="new-password">
          <button type="button" class="password-toggle" data-target="signup-password" aria-label="Afficher le mot de passe">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1.5 12S5 5 12 5s10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <div class="password-strength" id="signup-strength" hidden>
          <div class="password-strength-track"><div class="password-strength-fill" id="signup-strength-fill"></div></div>
          <span id="signup-strength-label"></span>
        </div>
        <ul class="password-rules" id="signup-password-rules">
          <li data-rule="len">8 caractères minimum</li>
          <li data-rule="lower">1 minuscule</li>
          <li data-rule="upper">1 majuscule</li>
          <li data-rule="digit">1 chiffre</li>
          <li data-rule="special">1 caractère spécial</li>
        </ul>
        <span class="form-error" id="signup-error-password" hidden></span>
      </div>
      <div class="form-field">
        <label for="signup-password-confirm">Confirmation du mot de passe</label>
        <div class="password-field">
          <input type="password" id="signup-password-confirm" autocomplete="new-password">
          <button type="button" class="password-toggle" data-target="signup-password-confirm" aria-label="Afficher le mot de passe">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1.5 12S5 5 12 5s10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <span class="form-error" id="signup-error-confirm" hidden></span>
      </div>

      <div class="form-field">
        <label for="signup-birth-date">Date de naissance</label>
        <input type="date" id="signup-birth-date" autocomplete="bday">
        <span class="form-error" id="signup-error-birth_date" hidden></span>
      </div>
      <div class="form-field" id="signup-parent-email-row" hidden>
        <label for="signup-parent-email">Email d'un parent ou tuteur</label>
        <input type="email" id="signup-parent-email" autocomplete="off">
        <span class="form-hint">Ton compte a besoin de l'autorisation d'un parent pour être activé (protection des mineurs, RGPD).</span>
        <span class="form-error" id="signup-error-parent_email" hidden></span>
      </div>

      <div class="form-field" id="signup-transfer-guest-row" hidden>
        <label>Souhaitez-vous conserver votre progression réalisée en mode invité ?</label>
        <div class="verdict-row" style="gap:8px;">
          <button type="button" class="btn btn-secondary btn-sm" id="btn-transfer-guest-yes" aria-pressed="true">Oui</button>
          <button type="button" class="btn btn-ghost btn-sm" id="btn-transfer-guest-no" aria-pressed="false">Non</button>
        </div>
      </div>

      <label class="checkbox-row">
        <input type="checkbox" id="signup-accept-terms">
        <span>J'accepte les <button type="button" class="link-inline js-open-legal">conditions d'utilisation</button></span>
      </label>
      <span class="form-error" id="signup-error-terms" hidden></span>
      <label class="checkbox-row">
        <input type="checkbox" id="signup-accept-privacy">
        <span>J'accepte la <button type="button" class="link-inline js-open-privacy">politique de confidentialité</button></span>
      </label>
      <span class="form-error" id="signup-error-privacy" hidden></span>

      <span class="form-error form-error--global" id="signup-error-global" hidden></span>

      <div class="verdict-row">
        <button type="button" class="btn btn-secondary" id="btn-signup-cancel">Annuler</button>
        <button type="submit" class="btn btn-primary" id="btn-signup-submit">Créer mon compte</button>
      </div>

      <p class="auth-switch">Déjà un compte ? <button type="button" class="link-inline js-switch-to-login">Se connecter</button></p>
    </form>
  </div>
</div>

<div class="modal-overlay" id="oauth-signup-modal-overlay" hidden>
  <div class="modal-card modal-card--wide card">
    <form id="oauth-signup-form" novalidate>
      <h3>Finaliser ton inscription</h3>
      <p class="form-hint">Ton compte Google est vérifié — il ne manque que ces quelques informations pour créer ton compte Mathadap.</p>

      <div class="form-row">
        <div class="form-field">
          <label for="oauth-signup-username">Nom d'utilisateur</label>
          <input type="text" id="oauth-signup-username" autocomplete="username" maxlength="25">
          <span class="form-error" id="oauth-signup-error-username" hidden></span>
        </div>
        <div class="form-field">
          <label for="oauth-signup-pseudo">Pseudo (nom affiché)</label>
          <input type="text" id="oauth-signup-pseudo" maxlength="30">
          <span class="form-error" id="oauth-signup-error-pseudo" hidden></span>
        </div>
      </div>

      <div class="form-field">
        <label for="oauth-signup-birth-date">Date de naissance</label>
        <input type="date" id="oauth-signup-birth-date" autocomplete="bday">
        <span class="form-error" id="oauth-signup-error-birth_date" hidden></span>
      </div>
      <div class="form-field" id="oauth-signup-parent-email-row" hidden>
        <label for="oauth-signup-parent-email">Email d'un parent ou tuteur</label>
        <input type="email" id="oauth-signup-parent-email" autocomplete="off">
        <span class="form-hint">Ton compte a besoin de l'autorisation d'un parent pour être activé (protection des mineurs, RGPD).</span>
        <span class="form-error" id="oauth-signup-error-parent_email" hidden></span>
      </div>

      <label class="checkbox-row">
        <input type="checkbox" id="oauth-signup-accept-terms">
        <span>J'accepte les <button type="button" class="link-inline js-open-legal">conditions d'utilisation</button></span>
      </label>
      <span class="form-error" id="oauth-signup-error-accept_terms" hidden></span>
      <label class="checkbox-row">
        <input type="checkbox" id="oauth-signup-accept-privacy">
        <span>J'accepte la <button type="button" class="link-inline js-open-privacy">politique de confidentialité</button></span>
      </label>
      <span class="form-error" id="oauth-signup-error-accept_privacy" hidden></span>

      <span class="form-error form-error--global" id="oauth-signup-error-global" hidden></span>

      <div class="verdict-row">
        <button type="button" class="btn btn-secondary" id="btn-oauth-signup-cancel">Annuler</button>
        <button type="submit" class="btn btn-primary" id="btn-oauth-signup-submit">Créer mon compte</button>
      </div>
    </form>
  </div>
</div>

<div class="modal-overlay" id="login-modal-overlay" hidden>
  <div class="modal-card modal-card--wide card">
    <form id="login-form" novalidate>
      <h3>Se connecter</h3>
      <p class="auth-next-hint" id="login-next-hint" hidden></p>

      <button type="button" class="btn btn-google" id="btn-google-login">
        <svg viewBox="0 0 18 18" width="18" height="18" aria-hidden="true">
          <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62Z"/>
          <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18Z"/>
          <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.97H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.03l2.97-2.33Z"/>
          <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.97L3.95 7.3C4.66 5.17 6.65 3.58 9 3.58Z"/>
        </svg>
        Continuer avec Google
      </button>
      <div class="auth-divider"><span>ou avec ton email</span></div>

      <div class="form-field">
        <label for="login-email">Adresse Gmail</label>
        <input type="email" id="login-email" autocomplete="email" placeholder="nom@gmail.com">
      </div>
      <div class="form-field">
        <label for="login-password">Mot de passe</label>
        <div class="password-field">
          <input type="password" id="login-password" autocomplete="current-password">
          <button type="button" class="password-toggle" data-target="login-password" aria-label="Afficher le mot de passe">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1.5 12S5 5 12 5s10.5 7 10.5 7-3.5 7-10.5 7S1.5 12 1.5 12Z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
      </div>

      <div class="login-options-row">
        <label class="checkbox-row checkbox-row--inline">
          <input type="checkbox" id="login-remember">
          <span>Se souvenir de moi</span>
        </label>
        <button type="button" class="link-inline js-open-forgot">Mot de passe oublié ?</button>
      </div>

      <span class="form-error form-error--global" id="login-error-global" hidden></span>

      <div class="verdict-row">
        <button type="button" class="btn btn-secondary" id="btn-login-cancel">Annuler</button>
        <button type="submit" class="btn btn-primary" id="btn-login-submit">Se connecter</button>
      </div>

      <p class="auth-switch">Pas encore de compte ? <button type="button" class="link-inline js-switch-to-signup">Créer un compte</button></p>
    </form>
  </div>
</div>

<div class="modal-overlay" id="login-2fa-modal-overlay" hidden>
  <div class="modal-card card">
    <form id="login-2fa-form" novalidate>
      <h3>Vérification en deux étapes</h3>
      <p id="login-2fa-intro">Saisis le code à 6 chiffres généré par ton application d'authentification.</p>

      <div class="form-field" id="login-2fa-code-row">
        <label for="login-2fa-code">Code à 6 chiffres</label>
        <input type="text" id="login-2fa-code" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" placeholder="123456">
      </div>
      <div class="form-field" id="login-2fa-recovery-row" hidden>
        <label for="login-2fa-recovery-code">Recovery code</label>
        <input type="text" id="login-2fa-recovery-code" autocomplete="off" placeholder="xxxx-xxxx-xxxx-xxxx">
      </div>

      <button type="button" class="link-inline" id="btn-2fa-toggle-recovery">Utiliser un recovery code</button>

      <span class="form-error form-error--global" id="login-2fa-error-global" hidden></span>

      <div class="verdict-row">
        <button type="button" class="btn btn-secondary" id="btn-login-2fa-cancel">Annuler</button>
        <button type="submit" class="btn btn-primary" id="btn-login-2fa-submit">Valider</button>
      </div>
    </form>
  </div>
</div>

<div class="modal-overlay" id="forgot-modal-overlay" hidden>
  <div class="modal-card card">
    <h3>Mot de passe oublié</h3>
    <p>Indique ton adresse Gmail : si un compte existe, un lien de réinitialisation est généré.</p>
    <div class="form-field">
      <label for="forgot-email">Adresse Gmail</label>
      <input type="email" id="forgot-email" autocomplete="email" placeholder="nom@gmail.com">
      <span class="form-error" id="forgot-error" hidden></span>
    </div>
    <div class="forgot-result" id="forgot-result" hidden></div>
    <div class="verdict-row">
      <button type="button" class="btn btn-secondary" id="btn-forgot-cancel">Annuler</button>
      <button type="button" class="btn btn-primary" id="btn-forgot-submit">Envoyer le lien</button>
    </div>
  </div>
</div>

<div class="modal-overlay" id="legal-modal-overlay" hidden>
  <div class="modal-card modal-card--wide card">
    <h3>Mentions légales</h3>
    <div class="legal-text">
      <p>Mathadap est un projet pédagogique développé à titre personnel, sans finalité commerciale. Il n'est pas
      édité par une société immatriculée.</p>
      <p><strong>Hébergement</strong> : dans sa version actuelle, l'application s'exécute en local sur la machine
      de l'utilisateur (aucun hébergeur tiers).</p>
      <p><strong>Contenu pédagogique</strong> : les exercices couvrent le programme de mathématiques de Seconde ;
      les corrections sont générées à partir d'une banque d'exercices contrôlée, jamais par génération de texte
      libre, pour garantir l'exactitude mathématique.</p>
      <p><strong>Comptes utilisateurs</strong> : la création d'un compte est gratuite et sert uniquement à
      sauvegarder ta progression personnelle (niveau, exercices, séries, avis).</p>
    </div>
    <div class="verdict-row"><button type="button" class="btn btn-primary" id="btn-legal-close">Fermer</button></div>
  </div>
</div>

<div class="modal-overlay" id="privacy-modal-overlay" hidden>
  <div class="modal-card modal-card--wide card">
    <h3>Politique de confidentialité</h3>
    <div class="legal-text">
      <p><strong>Données collectées</strong> : adresse email, nom d'utilisateur, pseudo, mot de passe (jamais
      stocké en clair — haché avec un algorithme sécurisé), photo de profil optionnelle, et ta progression
      d'apprentissage (réponses, séries, temps passé).</p>
      <p><strong>Utilisation</strong> : ces données servent exclusivement à faire fonctionner ton compte et à
      personnaliser ton expérience (niveau, recommandations d'exercices). Elles ne sont ni vendues, ni partagées
      avec des tiers, ni utilisées à des fins publicitaires.</p>
      <p><strong>Stockage</strong> : les comptes sont stockés dans une base de données locale au serveur
      (SQLite) ; ta progression détaillée dans des fichiers associés à ton compte.</p>
      <p><strong>Cookies</strong> : un unique cookie technique (session de connexion), nécessaire au
      fonctionnement du compte — aucun cookie publicitaire ou de tracking tiers.</p>
      <p><strong>Tes droits</strong> : tu peux modifier ton pseudo/photo depuis ton profil à tout moment, et
      demander la suppression de ton compte et de tes données.</p>
    </div>
    <div class="verdict-row"><button type="button" class="btn btn-primary" id="btn-privacy-close">Fermer</button></div>
  </div>
</div>

<div class="modal-overlay" id="policy-update-modal-overlay" hidden>
  <div class="modal-card card">
    <h3>Mise à jour de nos conditions</h3>
    <p>Nos conditions d'utilisation et/ou notre politique de confidentialité ont été mises à jour. Merci de les
    accepter à nouveau pour continuer à utiliser Mathadap.</p>
    <label class="checkbox-row">
      <input type="checkbox" id="policy-update-accept-terms">
      <span>J'accepte les <button type="button" class="link-inline js-open-legal">conditions d'utilisation</button></span>
    </label>
    <label class="checkbox-row">
      <input type="checkbox" id="policy-update-accept-privacy">
      <span>J'accepte la <button type="button" class="link-inline js-open-privacy">politique de confidentialité</button></span>
    </label>
    <span class="form-error form-error--global" id="policy-update-error" hidden></span>
    <div class="verdict-row">
      <button type="button" class="btn btn-primary" id="btn-policy-update-accept">Continuer</button>
    </div>
  </div>
</div>
`;
