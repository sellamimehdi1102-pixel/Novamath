import{a as m}from"./api.D9MhFfTx.js";import{g as q,i as he,j as R,k as be,l as j,b as ve}from"./theme.DpqEKRmI.js";const ye=`
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
      <p class="form-hint">Ton compte Google est vérifié — il ne manque que ces quelques informations pour créer ton compte NovaMath.</p>

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
      <p>NovaMath est un projet pédagogique développé à titre personnel, sans finalité commerciale. Il n'est pas
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
    accepter à nouveau pour continuer à utiliser NovaMath.</p>
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
`,W="lumis:stats",M="novamath:scoped_uid",ee=["lumis:stats","lumis:profile","lumis:series_in_progress","lumis:selected_chapters","lumis:open_chapter","lumis:last_level","lumis:practice_choices","lumis:pending_series","novamath:settings"];function _e(){ee.forEach(e=>localStorage.removeItem(e)),localStorage.removeItem(I),localStorage.removeItem(M);try{sessionStorage.removeItem("novamath:guest_lock_card_dismissed"),sessionStorage.removeItem("novamath:guest_card_dismissed")}catch{}}function we(e){const t=e!=null?String(e):null;let n;try{n=localStorage.getItem(M)}catch{return}n!==t&&(ee.forEach(o=>localStorage.removeItem(o)),t?localStorage.setItem(M,t):localStorage.removeItem(M))}typeof window<"u"&&we(window.__NOVAMATH_USER_ID__??null);const ke={1:1,2:1.3,3:1.6,4:1.9,5:2.2},E=[0,100,250,450,700,1e3,1400,1900,2500,3200,4e3],$=[{id:"ex_10",label:"10 exercices",test:e=>e.history.length>=10},{id:"ex_50",label:"50 exercices",test:e=>e.history.length>=50},{id:"ex_100",label:"100 exercices",test:e=>e.history.length>=100},{id:"streak_7",label:"Série de 7 jours",test:e=>J(e.history)>=7},{id:"streak_30",label:"Série de 30 jours",test:e=>J(e.history)>=30},{id:"chapter_mastered",label:"Un chapitre à 100%",test:e=>Object.values(te(e.history)).some(t=>t.rate>=1&&t.count>=5)},{id:"exam_pass",label:"Premier examen blanc réussi",test:e=>e.history.some(t=>t.mode==="examen"&&t.correct)}];function N(){return{xp:0,history:[],badges:[],series:[]}}function C(){try{const e=localStorage.getItem(W);return e?{...N(),...JSON.parse(e)}:N()}catch{return N()}}function F(e){localStorage.setItem(W,JSON.stringify(e)),m.saveStats(e).catch(()=>{})}function J(e){if(!e.length)return 0;const t=[...new Set(e.map(s=>s.date))].sort().reverse();let n=0,o=new Date;o.setHours(0,0,0,0);for(const s of t){const r=new Date(s);r.setHours(0,0,0,0);const l=Math.round((o-r)/864e5);if(l===0||l===1)n+=1,o=r;else break}return n}const Se=.7,xe=10;function Ze(e,t){const n=te(t)[e];return!n||n.count===0?"not_started":n.rate>=Se&&n.count>=xe?"mastered":"in_progress"}function te(e){const t={};for(const o of e){const s=o.chapter||"?";t[s]=t[s]||{total:0,correct:0},t[s].total+=1,o.correct&&(t[s].correct+=1)}const n={};for(const[o,s]of Object.entries(t))n[o]={count:s.total,rate:s.total?s.correct/s.total:0};return n}function ze(e){const t={};return e.forEach(n=>{n.id!=null&&(t[n.chapter]=t[n.chapter]||new Set,t[n.chapter].add(n.id))}),t}function Je(e){const t={};return e.forEach(n=>{if(n.id==null)return;const o=`${n.chapter}|${n.notion}`;t[o]=t[o]||new Set,t[o].add(n.id)}),t}function Ye(e){const t={};for(const o of e){const s=`${o.chapter}|${o.notion}`;t[s]=t[s]||{total:0,correct:0,last:null},t[s].total+=1,o.correct&&(t[s].correct+=1),(!t[s].last||o.ts>t[s].last)&&(t[s].last=o.ts)}const n={};for(const[o,s]of Object.entries(t))n[o]={count:s.total,rate:s.total?s.correct/s.total:0,last:s.last};return n}function Ke(e){let t=1;for(let l=0;l<E.length;l++)e>=E[l]&&(t=l+1);const n=E[t-1]??0,o=Math.min(t,E.length-1),s=E[o]??n+800,r=s>n?Math.min(1,(e-n)/(s-n)):1;return{level:t,floor:n,ceil:s,progress:r}}function Qe({id:e,chapter:t,notion:n,difficulty:o,correct:s,usedHint:r,mode:l,duration_s:d}){const u=C(),f=10*(ke[o]||1),h=s?Math.round(f+(s&&!r?5:0)):0;u.xp+=h,u.history.push({id:e,date:new Date().toISOString().slice(0,10),ts:Date.now(),chapter:t,notion:n,difficulty:o,correct:!!s,mode:l||"revisions",duration_s:d||0,xp:h,class_level:q()});const g=new Set(u.badges);u.badges=$.filter(_=>_.test(u)).map(_=>_.id);const k=u.badges.filter(_=>!g.has(_));return F(u),{gained:h,state:u,newlyUnlocked:k}}function Xe(){return C()}function We(e,t){const n=d=>(d.class_level||"seconde")===t,o=(e.history||[]).filter(n),s=(e.series||[]).filter(n),r=o.reduce((d,u)=>d+(u.xp||0),0),l=$.filter(d=>d.test({history:o,series:s,xp:r})).map(d=>d.id);return{xp:r,history:o,series:s,badges:l}}function et(){return $}function tt({mode:e,chapterId:t,notion:n,total:o}){return{id:`s_${Date.now()}`,startedAt:Date.now(),mode:e,chapterId:t,notion:n,total:o,questions:[]}}function nt(e,t){e.questions.push(t)}function at(e,t={}){const n=C(),o=e.questions.length,s=e.questions.filter(d=>d.correct).length,r=e.questions.reduce((d,u)=>d+(u.duration_s||0),0),l={id:e.id,date:new Date().toISOString().slice(0,10),startedAt:e.startedAt,endedAt:Date.now(),mode:e.mode,chapterId:e.chapterId,notion:e.notion||null,questions:e.questions,score:s,total:o,accuracy:o?Math.round(s/o*100):0,durationTotal_s:r,levelAtTime:t.levelAtTime||null,class_level:q()};return n.series=n.series||[],n.series.push(l),F(n),l}function ot(e){if(!e.length)return 0;const t=e.filter(n=>n.correct).length;return Math.round(t/e.length*20*2)/2}const I="lumis:series_in_progress";function st(e){localStorage.setItem(I,JSON.stringify({...e,class_level:q(),savedAt:Date.now()}))}function it(){try{const e=JSON.parse(localStorage.getItem(I));return e&&(e.class_level||"seconde")===q()?e:null}catch{return null}}function rt(){localStorage.removeItem(I)}async function lt(){try{const e=await m.getStats();if(e&&Array.isArray(e.history)&&e.history.length){const t=C();if(e.history.length>t.history.length)return F(e),e}}catch{}return C()}const ne="nm_cookie_consent",ae="1";function Ee(){try{const e=localStorage.getItem(ne);if(!e)return null;const t=JSON.parse(e);return t&&t.version===ae?t:null}catch{return null}}function P(e,t){const n={statistics:e,marketing:t,version:ae,decided_at:new Date().toISOString()};localStorage.setItem(ne,JSON.stringify(n)),m.setCookieConsent(e,t).catch(()=>{})}function Ce(){if(document.getElementById("cookie-consent-banner"))return;const e=document.createElement("div");e.id="cookie-consent-banner",e.className="card cookie-banner",e.innerHTML=`
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
  `,document.body.appendChild(e);const t=()=>e.remove();document.getElementById("cookie-banner-customize-link").addEventListener("click",()=>{document.getElementById("cookie-banner-categories").hidden=!1,document.getElementById("cookie-banner-save").hidden=!1}),document.getElementById("cookie-banner-accept-all").addEventListener("click",()=>{P(!0,!0),t()}),document.getElementById("cookie-banner-reject-all").addEventListener("click",()=>{P(!1,!1),t()}),document.getElementById("cookie-banner-save").addEventListener("click",()=>{P(document.getElementById("cookie-banner-statistics").checked,document.getElementById("cookie-banner-marketing").checked),t()})}Ee()||Ce();const a=e=>document.getElementById(e),oe=/^[a-zA-Z0-9](?:[a-zA-Z0-9._+-]*[a-zA-Z0-9])?@gmail\.com$/,se=/^[a-zA-Z0-9_-]{3,25}$/;function Ae(){a("signup-modal-overlay")||document.body.insertAdjacentHTML("beforeend",ye)}Ae();function A(e){e.hidden=!1}function y(e){e.hidden=!0}function ie(){["signup-modal-overlay","oauth-signup-modal-overlay","login-modal-overlay","login-2fa-modal-overlay","forgot-modal-overlay","legal-modal-overlay","privacy-modal-overlay"].forEach(e=>{a(e).hidden=!0})}function S(e,t,n){document.addEventListener("click",o=>{o.target.closest(e)&&(ie(),n&&n(),A(a(t)))})}let re=!0;function B(e){re=e,a("btn-transfer-guest-yes").classList.toggle("btn-primary",e),a("btn-transfer-guest-yes").classList.toggle("btn-secondary",!e),a("btn-transfer-guest-yes").setAttribute("aria-pressed",String(e)),a("btn-transfer-guest-no").classList.toggle("btn-primary",!e),a("btn-transfer-guest-no").classList.toggle("btn-secondary",e),a("btn-transfer-guest-no").setAttribute("aria-pressed",String(!e))}document.addEventListener("click",e=>{e.target.closest("#btn-transfer-guest-yes")&&B(!0),e.target.closest("#btn-transfer-guest-no")&&B(!1)});S(".js-open-signup","signup-modal-overlay",()=>{a("signup-transfer-guest-row").hidden=!(w!=null&&w.is_guest),B(!0)});const Le=15;function Me(e){const[t,n,o]=e.split("-").map(Number);if(!t||!n||!o)return null;const s=new Date(t,n-1,o),r=new Date;let l=r.getFullYear()-s.getFullYear();return(r.getMonth()<s.getMonth()||r.getMonth()===s.getMonth()&&r.getDate()<s.getDate())&&(l-=1),l}function x(e="signup-birth-date"){const t=a(e).value;if(!t)return!1;const n=Me(t);return n!==null&&n<Le}a("signup-birth-date").addEventListener("change",()=>{a("signup-parent-email-row").hidden=!x()});a("oauth-signup-birth-date").addEventListener("change",()=>{a("oauth-signup-parent-email-row").hidden=!x("oauth-signup-birth-date")});S(".js-open-login","login-modal-overlay");S(".js-open-legal","legal-modal-overlay");S(".js-open-privacy","privacy-modal-overlay");S(".js-open-forgot","forgot-modal-overlay",()=>{a("forgot-email").value=a("login-email").value||"",a("forgot-result").hidden=!0,a("forgot-error").hidden=!0});S(".js-switch-to-login","login-modal-overlay");S(".js-switch-to-signup","signup-modal-overlay");document.addEventListener("click",e=>{var t;(t=e.target.classList)!=null&&t.contains("modal-overlay")&&y(e.target)});document.addEventListener("click",e=>{e.target.closest("#btn-signup-cancel")&&y(a("signup-modal-overlay")),e.target.closest("#btn-oauth-signup-cancel")&&y(a("oauth-signup-modal-overlay")),e.target.closest("#btn-login-cancel")&&y(a("login-modal-overlay")),e.target.closest("#btn-forgot-cancel")&&y(a("forgot-modal-overlay")),e.target.closest("#btn-legal-close")&&y(a("legal-modal-overlay")),e.target.closest("#btn-privacy-close")&&y(a("privacy-modal-overlay"))});let w=null;m.me().then(({user:e})=>{w=e,e.is_guest||Te()}).catch(()=>{document.querySelector(".js-start-guest-eval")&&_e()});async function Te(){try{if(!(await m.getPolicyStatus()).needs_reacceptance)return}catch{return}a("policy-update-modal-overlay").hidden=!1}a("btn-policy-update-accept").addEventListener("click",async()=>{const e=a("policy-update-error");if(e.hidden=!0,!a("policy-update-accept-terms").checked||!a("policy-update-accept-privacy").checked){e.textContent="Tu dois accepter les deux documents pour continuer.",e.hidden=!1;return}try{await m.acceptPolicy(),a("policy-update-modal-overlay").hidden=!0}catch(t){e.textContent=t.message||"Une erreur est survenue.",e.hidden=!1}});document.addEventListener("click",async e=>{const t=e.target.closest(".js-start-guest-eval");if(t){t.disabled=!0;try{w||await m.enterGuest(),window.location.href="/evaluation.html"}catch{t.disabled=!1}}});document.querySelectorAll(".password-toggle").forEach(e=>{e.addEventListener("click",()=>{const t=a(e.dataset.target),n=t.type==="text";t.type=n?"password":"text",e.classList.toggle("is-visible",!n),e.setAttribute("aria-label",n?"Afficher le mot de passe":"Masquer le mot de passe")})});function le(e){const t={len:e.length>=8,lower:/[a-z]/.test(e),upper:/[A-Z]/.test(e),digit:/[0-9]/.test(e),special:/[^a-zA-Z0-9]/.test(e)};let n=Object.values(t).filter(Boolean).length;e.length<8&&(n=Math.min(n,1));const o=["Faible","Faible","Faible","Moyen","Fort","Très fort"],s=[1,1,1,2,3,4];return{rules:t,score:n,label:o[n],level:s[n]}}a("signup-password").addEventListener("input",()=>{const e=a("signup-password").value,{rules:t,label:n,level:o}=le(e),s=a("signup-strength");s.hidden=e.length===0,a("signup-strength-fill").style.width=`${o*25}%`,a("signup-strength-fill").dataset.level=String(o),a("signup-strength-label").textContent=n,document.querySelectorAll("#signup-password-rules li").forEach(r=>{r.classList.toggle("is-valid",!!t[r.dataset.rule])})});function i(e,t,n){const o=a(`${e}-error-${t}`);o&&(o.textContent=n||o.textContent,o.hidden=!n)}function U(e,t){t.forEach(n=>i(e,n,""))}function qe(){U("signup",["email","username","pseudo","birth_date","parent_email","password","confirm","terms","privacy","global"]);let e=!0;const t=a("signup-email").value.trim();t?oe.test(t)||(i("signup","email","Utilise une adresse Gmail valide (nom@gmail.com)."),e=!1):(i("signup","email","L'adresse email est obligatoire."),e=!1);const n=a("signup-username").value.trim();n?se.test(n)||(i("signup","username","3 à 25 caractères : lettres, chiffres, - ou _ uniquement."),e=!1):(i("signup","username","Le nom d'utilisateur est obligatoire."),e=!1),a("signup-pseudo").value.trim()||(i("signup","pseudo","Le pseudo est obligatoire."),e=!1);const s=a("signup-birth-date").value;s?new Date(s)>new Date?(i("signup","birth_date","La date de naissance ne peut pas être dans le futur."),e=!1):x()&&!a("signup-parent-email").value.trim()&&(i("signup","parent_email","L'email d'un parent est obligatoire pour ton âge."),e=!1):(i("signup","birth_date","La date de naissance est obligatoire."),e=!1);const r=a("signup-password").value,{rules:l}=le(r);r?Object.values(l).every(Boolean)||(i("signup","password","Le mot de passe ne respecte pas toutes les conditions ci-dessus."),e=!1):(i("signup","password","Le mot de passe est obligatoire."),e=!1);const d=a("signup-password-confirm").value;return r!==d&&(i("signup","confirm","Les deux mots de passe ne correspondent pas."),e=!1),a("signup-accept-terms").checked||(i("signup","terms","Tu dois accepter les conditions d'utilisation."),e=!1),a("signup-accept-privacy").checked||(i("signup","privacy","Tu dois accepter la politique de confidentialité."),e=!1),e}function D(){const t=new URLSearchParams(window.location.search).get("next"),n=["dashboard.html","chapitres.html","exercice.html","evaluation.html","profil.html"];window.location.href=t&&n.includes(t)?`/${t}`:"/dashboard.html"}a("signup-form").addEventListener("submit",async e=>{if(e.preventDefault(),!qe())return;const t=a("btn-signup-submit");t.disabled=!0;try{const n=x(),o=await m.register({email:a("signup-email").value.trim(),username:a("signup-username").value.trim(),pseudo:a("signup-pseudo").value.trim(),birth_date:a("signup-birth-date").value,parent_email:n?a("signup-parent-email").value.trim():void 0,password:a("signup-password").value,confirm_password:a("signup-password-confirm").value,accept_terms:a("signup-accept-terms").checked,accept_privacy:a("signup-accept-privacy").checked,transfer_guest:!!(w!=null&&w.is_guest)&&re});if(o.account_status==="pending_parental_consent"){i("signup","global",o.message),a("signup-error-global").classList.add("form-error--info");return}D()}catch(n){n.field?i("signup",n.field,n.message):i("signup","global",n.message||"Une erreur est survenue.")}finally{t.disabled=!1}});let ce=null;function Ie(){U("oauth-signup",["username","pseudo","birth_date","parent_email","accept_terms","accept_privacy","global"]);let e=!0;const t=a("oauth-signup-username").value.trim();t?se.test(t)||(i("oauth-signup","username","3 à 25 caractères : lettres, chiffres, - ou _ uniquement."),e=!1):(i("oauth-signup","username","Le nom d'utilisateur est obligatoire."),e=!1),a("oauth-signup-pseudo").value.trim()||(i("oauth-signup","pseudo","Le pseudo est obligatoire."),e=!1);const o=a("oauth-signup-birth-date").value;return o?new Date(o)>new Date?(i("oauth-signup","birth_date","La date de naissance ne peut pas être dans le futur."),e=!1):x("oauth-signup-birth-date")&&!a("oauth-signup-parent-email").value.trim()&&(i("oauth-signup","parent_email","L'email d'un parent est obligatoire pour ton âge."),e=!1):(i("oauth-signup","birth_date","La date de naissance est obligatoire."),e=!1),a("oauth-signup-accept-terms").checked||(i("oauth-signup","accept_terms","Tu dois accepter les conditions d'utilisation."),e=!1),a("oauth-signup-accept-privacy").checked||(i("oauth-signup","accept_privacy","Tu dois accepter la politique de confidentialité."),e=!1),e}function De(e){ce=e,ie(),U("oauth-signup",["username","pseudo","birth_date","parent_email","accept_terms","accept_privacy","global"]),a("oauth-signup-form").reset(),a("oauth-signup-parent-email-row").hidden=!0,A(a("oauth-signup-modal-overlay"))}a("oauth-signup-form").addEventListener("submit",async e=>{if(e.preventDefault(),!Ie())return;const t=a("btn-oauth-signup-submit");t.disabled=!0;try{const n=x("oauth-signup-birth-date"),o=await m.oauthCompleteSignup(ce,{username:a("oauth-signup-username").value.trim(),pseudo:a("oauth-signup-pseudo").value.trim(),birth_date:a("oauth-signup-birth-date").value,parent_email:n?a("oauth-signup-parent-email").value.trim():void 0,accept_terms:a("oauth-signup-accept-terms").checked,accept_privacy:a("oauth-signup-accept-privacy").checked});if(o.account_status==="pending_parental_consent"){i("oauth-signup","global",o.message),a("oauth-signup-error-global").classList.add("form-error--info");return}D()}catch(n){n.field?i("oauth-signup",n.field,n.message):i("oauth-signup","global",n.message||"Une erreur est survenue.")}finally{t.disabled=!1}});a("login-form").addEventListener("submit",async e=>{e.preventDefault(),i("login","global","");const t=a("login-email").value.trim(),n=a("login-password").value;if(!t||!n){i("login","global","Adresse email et mot de passe requis.");return}const o=a("btn-login-submit");o.disabled=!0;try{const s=await m.login({email:t,password:n,remember:a("login-remember").checked});s.two_factor_required?(y(a("login-modal-overlay")),ue(s.challenge_token)):D()}catch(s){i("login","global",s.message||"Connexion impossible.")}finally{o.disabled=!1}});let G=!1;function de(e){G=e,a("login-2fa-code-row").hidden=e,a("login-2fa-recovery-row").hidden=!e,a("login-2fa-intro").textContent=e?"Saisis l'un de tes recovery codes (généré lors de l'activation de la double authentification).":"Saisis le code à 6 chiffres généré par ton application d'authentification.",a("btn-2fa-toggle-recovery").textContent=e?"Utiliser le code de mon application":"Utiliser un recovery code",a("login-2fa-error-global").hidden=!0;const t=a(e?"login-2fa-recovery-code":"login-2fa-code");setTimeout(()=>t.focus(),50)}function ue(e){a("login-2fa-form").dataset.challengeToken=e,a("login-2fa-code").value="",a("login-2fa-recovery-code").value="",de(!1),A(a("login-2fa-modal-overlay"))}a("btn-2fa-toggle-recovery").addEventListener("click",()=>de(!G));a("btn-login-2fa-cancel").addEventListener("click",()=>y(a("login-2fa-modal-overlay")));a("login-2fa-form").addEventListener("submit",async e=>{e.preventDefault(),a("login-2fa-error-global").hidden=!0;const t=e.currentTarget.dataset.challengeToken,n=a("btn-login-2fa-submit");n.disabled=!0;try{G?await m.recover2FA(t,a("login-2fa-recovery-code").value.trim()):await m.verify2FA(t,a("login-2fa-code").value.trim()),D()}catch(o){a("login-2fa-error-global").textContent=o.message||"Code invalide.",a("login-2fa-error-global").hidden=!1}finally{n.disabled=!1}});a("btn-forgot-submit").addEventListener("click",async()=>{a("forgot-error").hidden=!0,a("forgot-result").hidden=!0;const e=a("forgot-email").value.trim();if(!e||!oe.test(e)){a("forgot-error").textContent="Utilise une adresse Gmail valide.",a("forgot-error").hidden=!1;return}const t=a("btn-forgot-submit");t.disabled=!0;try{const n=await m.forgotPassword(e);a("forgot-result").innerHTML=n.dev_reset_link?`${n.message}<br><a href="${n.dev_reset_link}">Lien de réinitialisation (mode développement, aucun service d'email configuré)</a>`:n.message,a("forgot-result").hidden=!1}catch(n){a("forgot-error").textContent=n.message||"Une erreur est survenue.",a("forgot-error").hidden=!1}finally{t.disabled=!1}});async function pe(){try{const e=await fetch("/api/auth/google/start",{redirect:"manual"});if(e.type==="opaqueredirect"||e.status===0){window.location.href="/api/auth/google/start";return}const t=await e.json().catch(()=>({}));i("signup","global",t.error||"Connexion Google indisponible pour le moment."),i("login","global",t.error||"Connexion Google indisponible pour le moment.")}catch{i("signup","global","Connexion Google indisponible pour le moment."),i("login","global","Connexion Google indisponible pour le moment.")}}a("btn-google-signup").addEventListener("click",pe);a("btn-google-login").addEventListener("click",pe);function O(e){const t=new URL(window.location.href);e.forEach(n=>t.searchParams.delete(n)),window.history.replaceState({},"",t.pathname+t.search+t.hash)}(function(){const t=new URLSearchParams(window.location.search),n=t.get("oauth_error");if(n){O(["oauth_error"]),i("login","global",n),A(a("login-modal-overlay"));return}const o=t.get("oauth_two_factor_required");if(o){O(["oauth_two_factor_required"]),ue(o);return}const s=t.get("oauth_complete_signup");if(s){O(["oauth_complete_signup"]),De(s);return}const r=t.get("next");if(!r)return;const l={"dashboard.html":"ton dashboard","chapitres.html":"les exercices","exercice.html":"l'entraînement","evaluation.html":"l'évaluation","profil.html":"ton profil"};a("login-next-hint").textContent=`Connecte-toi pour accéder à ${l[r]||"cette page"}.`,a("login-next-hint").hidden=!1,A(a("login-modal-overlay"))})();let T=0;function Ne(){T+=1,document.body.style.overflow="hidden"}function Pe(){T=Math.max(0,T-1),T===0&&(document.body.style.overflow="")}function V({id:e,title:t,bodyHtml:n="",bodyEl:o=null,size:s="md",closeOnEscape:r=!0,closeOnOverlayClick:l=!0,showCloseButton:d=!0,onOpen:u,onClose:f}={}){let p=e?document.getElementById(e):null;const h=!!p;p||(p=document.createElement("div"),e&&(p.id=e)),p.className="popup-overlay",p.hidden=!1;const g=document.createElement("div");if(g.className=`popup-card popup-card--${s} card card--glass`,g.setAttribute("role","dialog"),g.setAttribute("aria-modal","true"),t||d){const v=document.createElement("div");if(v.className="popup-header",t){const b=`popup-title-${Math.random().toString(36).slice(2)}`;g.setAttribute("aria-labelledby",b),v.innerHTML=`<h2 class="popup-title" id="${b}">${t}</h2>`}else v.innerHTML='<h2 class="popup-title"></h2>';if(d){const b=document.createElement("button");b.type="button",b.className="popup-close",b.setAttribute("aria-label","Fermer"),b.innerHTML=he("x"),b.addEventListener("click",()=>L()),v.appendChild(b)}g.appendChild(v)}const k=document.createElement("div");k.className="popup-body",o?k.appendChild(o):k.innerHTML=n,g.appendChild(k),p.innerHTML="",p.appendChild(g),h||document.body.appendChild(p),Ne(),requestAnimationFrame(()=>p.classList.add("is-open"));let _=!1;function L(){if(_)return;_=!0,p.classList.remove("is-open"),document.removeEventListener("keydown",Z),Pe();const v=()=>{p.hidden=!0,p.innerHTML="",f&&f()};let b=!1;const z=()=>{b||(b=!0,v())};p.addEventListener("transitionend",z,{once:!0}),setTimeout(z,300)}function Z(v){v.key==="Escape"&&r&&L()}return document.addEventListener("keydown",Z),l&&p.addEventListener("click",v=>{v.target===p&&L()}),u&&u(g),{close:L,el:p,bodyEl:k}}function Oe({title:e="",label:t="",defaultValue:n="",placeholder:o="",confirmLabel:s="Valider",cancelLabel:r="Annuler"}={}){return new Promise(l=>{let d=!1;const u=g=>{d||(d=!0,l(g))},f=document.createElement("div");f.innerHTML=`
      <div class="form-field">
        ${t?`<label for="popup-prompt-input">${t}</label>`:""}
        <input type="text" id="popup-prompt-input" placeholder="${o}">
      </div>
      <div class="verdict-row">
        <button type="button" class="btn btn-ghost" data-action="cancel">${r}</button>
        <button type="button" class="btn btn-primary" data-action="confirm">${s}</button>
      </div>
    `;const p=V({title:e,bodyEl:f,size:"sm",onClose:()=>u(null)}),h=f.querySelector("#popup-prompt-input");h.value=n,f.querySelector('[data-action="cancel"]').addEventListener("click",()=>{u(null),p.close()}),f.querySelector('[data-action="confirm"]').addEventListener("click",()=>{u(h.value),p.close()}),h.addEventListener("keydown",g=>{g.key==="Enter"&&(g.preventDefault(),u(h.value),p.close())}),requestAnimationFrame(()=>{h.focus(),h.select()})})}function je({title:e="",message:t="",confirmLabel:n="Confirmer",cancelLabel:o="Annuler",danger:s=!1}={}){return new Promise(r=>{let l=!1;const d=p=>{l||(l=!0,r(p))},u=document.createElement("div");u.innerHTML=`
      <p class="popup-confirm-message">${t}</p>
      <div class="verdict-row">
        <button type="button" class="btn btn-ghost" data-action="cancel">${o}</button>
        <button type="button" class="btn ${s?"btn-danger-outline":"btn-primary"}" data-action="confirm">${n}</button>
      </div>
    `;const f=V({title:e,bodyEl:u,size:"sm",onClose:()=>d(!1)});u.querySelector('[data-action="cancel"]').addEventListener("click",()=>{d(!1),f.close()}),u.querySelector('[data-action="confirm"]').addEventListener("click",()=>{d(!0),f.close()})})}const ct=Object.freeze(Object.defineProperty({__proto__:null,openConfirmPopup:je,openPopup:V,openPromptPopup:Oe},Symbol.toStringTag,{value:"Module"})),Be="1.80",ge="novamath:settings";let c=null,Y=null,K=Promise.resolve();function He(){try{return JSON.parse(localStorage.getItem(ge))||{}}catch{return{}}}function H(e){localStorage.setItem(ge,JSON.stringify(e))}function me(e,t){window.dispatchEvent(new CustomEvent("novamath:settings-changed",{detail:{category:e,patch:t,settings:c}}))}function Re(e){e==="appearance"&&j(c.appearance)}async function dt(e){be();const t=He();c={appearance:R(),...t},j(c.appearance),ve(document.getElementById("theme-toggle"));const n=document.getElementById("sidebar-version");n&&(n.textContent=`NovaMath v${Be}`);try{c=await m.getSettings(),H(c),j(c.appearance),me("*",c)}catch{}return c}function $e(){return c||{appearance:R()}}function Fe(e){const t=n=>e(n);return window.addEventListener("novamath:settings-changed",t),()=>window.removeEventListener("novamath:settings-changed",t)}function ut(e,t,n){c||(c={appearance:R()});const o=c[e];return t===null?c={...c,[e]:n}:c={...c,[e]:{...c[e],[t]:n}},H(c),Re(e),me(e,c[e]),clearTimeout(Y),Y=setTimeout(()=>{K=K.then(()=>m.saveSettings(c)).then(s=>{c=s,H(c)}).catch(()=>{o!==void 0&&(c={...c,[e]:o})})},250),c}const Q={fr:{"nav.dashboard":"Dashboard","nav.exercices":"Exercices","nav.cours":"Cours","nav.entrainement":"Entraînement","nav.chatbot":"Chatbot","nav.abonnement":"Abonnement","nav.profil":"Voir le profil","settings.title":"Paramètres","settings.cat.account":"Compte","settings.cat.appearance":"Apparence","settings.cat.training":"Entraînement","settings.cat.learning":"Apprentissage","settings.cat.security":"Confidentialité & Sécurité","settings.cat.language":"Langue","settings.cat.chatbot":"Chatbot","settings.cat.help":"Aide & À propos","exercise.notice_fr_only":"Le contenu des exercices reste en français quelle que soit la langue de l'interface.",chatbot_card_view_course:"Voir le cours",chatbot_card_practice:"Commencer un entraînement",chatbot_card_review_weak:"Revoir cette notion",chatbot_card_redo_series:"Refaire cette série",chatbot_mentions_searching:"Recherche…",chatbot_mentions_no_result:"Aucune ressource trouvée.",chatbot_mentions_did_you_mean:"Voulez-vous dire",cmd_palette_placeholder:"Rechercher ou naviguer…",cmd_palette_no_result:"Aucun résultat",cmd_palette_dashboard:"Voir ma progression",cmd_palette_cours:"Parcourir les cours",cmd_palette_chapitres:"Choisir un chapitre",cmd_palette_entrainement:"S'entraîner",cmd_palette_chatbot:"Poser une question",cmd_palette_abonnement:"Passer à Premium ou Ultra",cmd_palette_profil:"Voir mon profil"},en:{"nav.dashboard":"Dashboard","nav.exercices":"Exercises","nav.cours":"Courses","nav.entrainement":"Practice","nav.chatbot":"Chatbot","nav.abonnement":"Subscription","nav.profil":"View profile","settings.title":"Settings","settings.cat.account":"Account","settings.cat.appearance":"Appearance","settings.cat.training":"Practice","settings.cat.learning":"Learning","settings.cat.security":"Privacy & Security","settings.cat.language":"Language","settings.cat.chatbot":"Chatbot","settings.cat.help":"Help & About","exercise.notice_fr_only":"Exercise content stays in French regardless of the interface language.",chatbot_card_view_course:"View the course",chatbot_card_practice:"Start practicing",chatbot_card_review_weak:"Review this topic",chatbot_card_redo_series:"Redo this series",chatbot_mentions_searching:"Searching…",chatbot_mentions_no_result:"No matching resource found.",chatbot_mentions_did_you_mean:"Did you mean",cmd_palette_placeholder:"Search or navigate…",cmd_palette_no_result:"No results",cmd_palette_dashboard:"View my progress",cmd_palette_cours:"Browse courses",cmd_palette_chapitres:"Choose a chapter",cmd_palette_entrainement:"Practice",cmd_palette_chatbot:"Ask a question",cmd_palette_abonnement:"Upgrade to Premium or Ultra",cmd_palette_profil:"View my profile"}};function fe(){var t;return((t=$e())==null?void 0:t.language)==="en"?"en":"fr"}function Ue(e,t){var o;const n=fe();return((o=Q[n])==null?void 0:o[e])??Q.fr[e]??t??e}function X(e=document){e.querySelectorAll("[data-i18n]").forEach(t=>{const n=t.getAttribute("data-i18n"),o=t.getAttribute("data-i18n-attr"),s=Ue(n);o?t.setAttribute(o,s):t.textContent=s}),document.documentElement.setAttribute("lang",fe())}function pt(e=document){X(e),Fe(t=>{(t.detail.category==="language"||t.detail.category==="*")&&X(e)})}export{st as A,V as B,ct as C,Je as a,pt as b,ze as c,Ye as d,it as e,$e as f,Xe as g,Ze as h,dt as i,ut as j,je as k,Fe as l,te as m,lt as n,Oe as o,J as p,Ke as q,ot as r,We as s,Ue as t,et as u,Qe as v,nt as w,at as x,tt as y,rt as z};
