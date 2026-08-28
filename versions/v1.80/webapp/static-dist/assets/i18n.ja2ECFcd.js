import{a as m}from"./api.CC07HWUE.js";import{g as M,i as de,j as O,k as ue,l as N,b as pe}from"./theme.BLPjMu9D.js";const ge=`
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
`,Q="lumis:stats",A="novamath:scoped_uid",X=["lumis:stats","lumis:profile","lumis:series_in_progress","lumis:selected_chapters","lumis:open_chapter","lumis:last_level","lumis:practice_choices","lumis:pending_series","novamath:settings"];function me(){X.forEach(e=>localStorage.removeItem(e)),localStorage.removeItem(T),localStorage.removeItem(A);try{sessionStorage.removeItem("novamath:guest_lock_card_dismissed"),sessionStorage.removeItem("novamath:guest_card_dismissed")}catch{}}function fe(e){const t=e!=null?String(e):null;let n;try{n=localStorage.getItem(A)}catch{return}n!==t&&(X.forEach(a=>localStorage.removeItem(a)),t?localStorage.setItem(A,t):localStorage.removeItem(A))}typeof window<"u"&&fe(window.__NOVAMATH_USER_ID__??null);const be={1:1,2:1.3,3:1.6,4:1.9,5:2.2},x=[0,100,250,450,700,1e3,1400,1900,2500,3200,4e3],P=[{id:"ex_10",label:"10 exercices",test:e=>e.history.length>=10},{id:"ex_50",label:"50 exercices",test:e=>e.history.length>=50},{id:"ex_100",label:"100 exercices",test:e=>e.history.length>=100},{id:"streak_7",label:"Série de 7 jours",test:e=>Z(e.history)>=7},{id:"streak_30",label:"Série de 30 jours",test:e=>Z(e.history)>=30},{id:"chapter_mastered",label:"Un chapitre à 100%",test:e=>Object.values(W(e.history)).some(t=>t.rate>=1&&t.count>=5)},{id:"exam_pass",label:"Premier examen blanc réussi",test:e=>e.history.some(t=>t.mode==="examen"&&t.correct)}];function I(){return{xp:0,history:[],badges:[],series:[]}}function E(){try{const e=localStorage.getItem(Q);return e?{...I(),...JSON.parse(e)}:I()}catch{return I()}}function B(e){localStorage.setItem(Q,JSON.stringify(e)),m.saveStats(e).catch(()=>{})}function Z(e){if(!e.length)return 0;const t=[...new Set(e.map(s=>s.date))].sort().reverse();let n=0,a=new Date;a.setHours(0,0,0,0);for(const s of t){const i=new Date(s);i.setHours(0,0,0,0);const r=Math.round((a-i)/864e5);if(r===0||r===1)n+=1,a=i;else break}return n}const he=.7,ve=10;function Fe(e,t){const n=W(t)[e];return!n||n.count===0?"not_started":n.rate>=he&&n.count>=ve?"mastered":"in_progress"}function W(e){const t={};for(const a of e){const s=a.chapter||"?";t[s]=t[s]||{total:0,correct:0},t[s].total+=1,a.correct&&(t[s].correct+=1)}const n={};for(const[a,s]of Object.entries(t))n[a]={count:s.total,rate:s.total?s.correct/s.total:0};return n}function Ue(e){const t={};return e.forEach(n=>{n.id!=null&&(t[n.chapter]=t[n.chapter]||new Set,t[n.chapter].add(n.id))}),t}function Ge(e){const t={};return e.forEach(n=>{if(n.id==null)return;const a=`${n.chapter}|${n.notion}`;t[a]=t[a]||new Set,t[a].add(n.id)}),t}function Ve(e){const t={};for(const a of e){const s=`${a.chapter}|${a.notion}`;t[s]=t[s]||{total:0,correct:0,last:null},t[s].total+=1,a.correct&&(t[s].correct+=1),(!t[s].last||a.ts>t[s].last)&&(t[s].last=a.ts)}const n={};for(const[a,s]of Object.entries(t))n[a]={count:s.total,rate:s.total?s.correct/s.total:0,last:s.last};return n}function Ze(e){let t=1;for(let r=0;r<x.length;r++)e>=x[r]&&(t=r+1);const n=x[t-1]??0,a=Math.min(t,x.length-1),s=x[a]??n+800,i=s>n?Math.min(1,(e-n)/(s-n)):1;return{level:t,floor:n,ceil:s,progress:i}}function ze({id:e,chapter:t,notion:n,difficulty:a,correct:s,usedHint:i,mode:r,duration_s:c}){const d=E(),f=10*(be[a]||1),b=s?Math.round(f+(s&&!i?5:0)):0;d.xp+=b,d.history.push({id:e,date:new Date().toISOString().slice(0,10),ts:Date.now(),chapter:t,notion:n,difficulty:a,correct:!!s,mode:r||"revisions",duration_s:c||0,xp:b,class_level:M()});const g=new Set(d.badges);d.badges=P.filter(y=>y.test(d)).map(y=>y.id);const S=d.badges.filter(y=>!g.has(y));return B(d),{gained:b,state:d,newlyUnlocked:S}}function Je(){return E()}function Ye(e,t){const n=c=>(c.class_level||"seconde")===t,a=(e.history||[]).filter(n),s=(e.series||[]).filter(n),i=a.reduce((c,d)=>c+(d.xp||0),0),r=P.filter(c=>c.test({history:a,series:s,xp:i})).map(c=>c.id);return{xp:i,history:a,series:s,badges:r}}function Ke(){return P}function Qe({mode:e,chapterId:t,notion:n,total:a}){return{id:`s_${Date.now()}`,startedAt:Date.now(),mode:e,chapterId:t,notion:n,total:a,questions:[]}}function Xe(e,t){e.questions.push(t)}function We(e,t={}){const n=E(),a=e.questions.length,s=e.questions.filter(c=>c.correct).length,i=e.questions.reduce((c,d)=>c+(d.duration_s||0),0),r={id:e.id,date:new Date().toISOString().slice(0,10),startedAt:e.startedAt,endedAt:Date.now(),mode:e.mode,chapterId:e.chapterId,notion:e.notion||null,questions:e.questions,score:s,total:a,accuracy:a?Math.round(s/a*100):0,durationTotal_s:i,levelAtTime:t.levelAtTime||null,class_level:M()};return n.series=n.series||[],n.series.push(r),B(n),r}function et(e){if(!e.length)return 0;const t=e.filter(n=>n.correct).length;return Math.round(t/e.length*20*2)/2}const T="lumis:series_in_progress";function tt(e){localStorage.setItem(T,JSON.stringify({...e,class_level:M(),savedAt:Date.now()}))}function nt(){try{const e=JSON.parse(localStorage.getItem(T));return e&&(e.class_level||"seconde")===M()?e:null}catch{return null}}function ot(){localStorage.removeItem(T)}async function at(){try{const e=await m.getStats();if(e&&Array.isArray(e.history)&&e.history.length){const t=E();if(e.history.length>t.history.length)return B(e),e}}catch{}return E()}const ee="nm_cookie_consent",te="1";function ye(){try{const e=localStorage.getItem(ee);if(!e)return null;const t=JSON.parse(e);return t&&t.version===te?t:null}catch{return null}}function q(e,t){const n={statistics:e,marketing:t,version:te,decided_at:new Date().toISOString()};localStorage.setItem(ee,JSON.stringify(n)),m.setCookieConsent(e,t).catch(()=>{})}function _e(){if(document.getElementById("cookie-consent-banner"))return;const e=document.createElement("div");e.id="cookie-consent-banner",e.className="card cookie-banner",e.innerHTML=`
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
  `,document.body.appendChild(e);const t=()=>e.remove();document.getElementById("cookie-banner-customize-link").addEventListener("click",()=>{document.getElementById("cookie-banner-categories").hidden=!1,document.getElementById("cookie-banner-save").hidden=!1}),document.getElementById("cookie-banner-accept-all").addEventListener("click",()=>{q(!0,!0),t()}),document.getElementById("cookie-banner-reject-all").addEventListener("click",()=>{q(!1,!1),t()}),document.getElementById("cookie-banner-save").addEventListener("click",()=>{q(document.getElementById("cookie-banner-statistics").checked,document.getElementById("cookie-banner-marketing").checked),t()})}ye()||_e();const o=e=>document.getElementById(e),ne=/^[a-zA-Z0-9](?:[a-zA-Z0-9._+-]*[a-zA-Z0-9])?@gmail\.com$/,we=/^[a-zA-Z0-9_-]{3,25}$/;function Se(){o("signup-modal-overlay")||document.body.insertAdjacentHTML("beforeend",ge)}Se();function H(e){e.hidden=!1}function _(e){e.hidden=!0}function ke(){["signup-modal-overlay","login-modal-overlay","login-2fa-modal-overlay","forgot-modal-overlay","legal-modal-overlay","privacy-modal-overlay"].forEach(e=>{o(e).hidden=!0})}function k(e,t,n){document.addEventListener("click",a=>{a.target.closest(e)&&(ke(),n&&n(),H(o(t)))})}let oe=!0;function D(e){oe=e,o("btn-transfer-guest-yes").classList.toggle("btn-primary",e),o("btn-transfer-guest-yes").classList.toggle("btn-secondary",!e),o("btn-transfer-guest-yes").setAttribute("aria-pressed",String(e)),o("btn-transfer-guest-no").classList.toggle("btn-primary",!e),o("btn-transfer-guest-no").classList.toggle("btn-secondary",e),o("btn-transfer-guest-no").setAttribute("aria-pressed",String(!e))}document.addEventListener("click",e=>{e.target.closest("#btn-transfer-guest-yes")&&D(!0),e.target.closest("#btn-transfer-guest-no")&&D(!1)});k(".js-open-signup","signup-modal-overlay",()=>{o("signup-transfer-guest-row").hidden=!(w!=null&&w.is_guest),D(!0)});const xe=15;function Ee(e){const[t,n,a]=e.split("-").map(Number);if(!t||!n||!a)return null;const s=new Date(t,n-1,a),i=new Date;let r=i.getFullYear()-s.getFullYear();return(i.getMonth()<s.getMonth()||i.getMonth()===s.getMonth()&&i.getDate()<s.getDate())&&(r-=1),r}function R(){const e=o("signup-birth-date").value;if(!e)return!1;const t=Ee(e);return t!==null&&t<xe}o("signup-birth-date").addEventListener("change",()=>{o("signup-parent-email-row").hidden=!R()});k(".js-open-login","login-modal-overlay");k(".js-open-legal","legal-modal-overlay");k(".js-open-privacy","privacy-modal-overlay");k(".js-open-forgot","forgot-modal-overlay",()=>{o("forgot-email").value=o("login-email").value||"",o("forgot-result").hidden=!0,o("forgot-error").hidden=!0});k(".js-switch-to-login","login-modal-overlay");k(".js-switch-to-signup","signup-modal-overlay");document.addEventListener("click",e=>{var t;(t=e.target.classList)!=null&&t.contains("modal-overlay")&&_(e.target)});document.addEventListener("click",e=>{e.target.closest("#btn-signup-cancel")&&_(o("signup-modal-overlay")),e.target.closest("#btn-login-cancel")&&_(o("login-modal-overlay")),e.target.closest("#btn-forgot-cancel")&&_(o("forgot-modal-overlay")),e.target.closest("#btn-legal-close")&&_(o("legal-modal-overlay")),e.target.closest("#btn-privacy-close")&&_(o("privacy-modal-overlay"))});let w=null;m.me().then(({user:e})=>{w=e,e.is_guest||Ce()}).catch(()=>{document.querySelector(".js-start-guest-eval")&&me()});async function Ce(){try{if(!(await m.getPolicyStatus()).needs_reacceptance)return}catch{return}o("policy-update-modal-overlay").hidden=!1}o("btn-policy-update-accept").addEventListener("click",async()=>{const e=o("policy-update-error");if(e.hidden=!0,!o("policy-update-accept-terms").checked||!o("policy-update-accept-privacy").checked){e.textContent="Tu dois accepter les deux documents pour continuer.",e.hidden=!1;return}try{await m.acceptPolicy(),o("policy-update-modal-overlay").hidden=!0}catch(t){e.textContent=t.message||"Une erreur est survenue.",e.hidden=!1}});document.addEventListener("click",async e=>{const t=e.target.closest(".js-start-guest-eval");if(t){t.disabled=!0;try{w||await m.enterGuest(),window.location.href="/evaluation.html"}catch{t.disabled=!1}}});document.querySelectorAll(".password-toggle").forEach(e=>{e.addEventListener("click",()=>{const t=o(e.dataset.target),n=t.type==="text";t.type=n?"password":"text",e.classList.toggle("is-visible",!n),e.setAttribute("aria-label",n?"Afficher le mot de passe":"Masquer le mot de passe")})});function ae(e){const t={len:e.length>=8,lower:/[a-z]/.test(e),upper:/[A-Z]/.test(e),digit:/[0-9]/.test(e),special:/[^a-zA-Z0-9]/.test(e)};let n=Object.values(t).filter(Boolean).length;e.length<8&&(n=Math.min(n,1));const a=["Faible","Faible","Faible","Moyen","Fort","Très fort"],s=[1,1,1,2,3,4];return{rules:t,score:n,label:a[n],level:s[n]}}o("signup-password").addEventListener("input",()=>{const e=o("signup-password").value,{rules:t,label:n,level:a}=ae(e),s=o("signup-strength");s.hidden=e.length===0,o("signup-strength-fill").style.width=`${a*25}%`,o("signup-strength-fill").dataset.level=String(a),o("signup-strength-label").textContent=n,document.querySelectorAll("#signup-password-rules li").forEach(i=>{i.classList.toggle("is-valid",!!t[i.dataset.rule])})});function p(e,t,n){const a=o(`${e}-error-${t}`);a&&(a.textContent=n||a.textContent,a.hidden=!n)}function Ae(e,t){t.forEach(n=>p(e,n,""))}function Le(){Ae("signup",["email","username","pseudo","birth_date","parent_email","password","confirm","terms","privacy","global"]);let e=!0;const t=o("signup-email").value.trim();t?ne.test(t)||(p("signup","email","Utilise une adresse Gmail valide (nom@gmail.com)."),e=!1):(p("signup","email","L'adresse email est obligatoire."),e=!1);const n=o("signup-username").value.trim();n?we.test(n)||(p("signup","username","3 à 25 caractères : lettres, chiffres, - ou _ uniquement."),e=!1):(p("signup","username","Le nom d'utilisateur est obligatoire."),e=!1),o("signup-pseudo").value.trim()||(p("signup","pseudo","Le pseudo est obligatoire."),e=!1);const s=o("signup-birth-date").value;s?new Date(s)>new Date?(p("signup","birth_date","La date de naissance ne peut pas être dans le futur."),e=!1):R()&&!o("signup-parent-email").value.trim()&&(p("signup","parent_email","L'email d'un parent est obligatoire pour ton âge."),e=!1):(p("signup","birth_date","La date de naissance est obligatoire."),e=!1);const i=o("signup-password").value,{rules:r}=ae(i);i?Object.values(r).every(Boolean)||(p("signup","password","Le mot de passe ne respecte pas toutes les conditions ci-dessus."),e=!1):(p("signup","password","Le mot de passe est obligatoire."),e=!1);const c=o("signup-password-confirm").value;return i!==c&&(p("signup","confirm","Les deux mots de passe ne correspondent pas."),e=!1),o("signup-accept-terms").checked||(p("signup","terms","Tu dois accepter les conditions d'utilisation."),e=!1),o("signup-accept-privacy").checked||(p("signup","privacy","Tu dois accepter la politique de confidentialité."),e=!1),e}function $(){const t=new URLSearchParams(window.location.search).get("next"),n=["dashboard.html","chapitres.html","exercice.html","evaluation.html","profil.html"];window.location.href=t&&n.includes(t)?`/${t}`:"/dashboard.html"}o("signup-form").addEventListener("submit",async e=>{if(e.preventDefault(),!Le())return;const t=o("btn-signup-submit");t.disabled=!0;try{const n=R(),a=await m.register({email:o("signup-email").value.trim(),username:o("signup-username").value.trim(),pseudo:o("signup-pseudo").value.trim(),birth_date:o("signup-birth-date").value,parent_email:n?o("signup-parent-email").value.trim():void 0,password:o("signup-password").value,confirm_password:o("signup-password-confirm").value,accept_terms:o("signup-accept-terms").checked,accept_privacy:o("signup-accept-privacy").checked,transfer_guest:!!(w!=null&&w.is_guest)&&oe});if(a.account_status==="pending_parental_consent"){p("signup","global",a.message),o("signup-error-global").classList.add("form-error--info");return}$()}catch(n){n.field?p("signup",n.field,n.message):p("signup","global",n.message||"Une erreur est survenue.")}finally{t.disabled=!1}});o("login-form").addEventListener("submit",async e=>{e.preventDefault(),p("login","global","");const t=o("login-email").value.trim(),n=o("login-password").value;if(!t||!n){p("login","global","Adresse email et mot de passe requis.");return}const a=o("btn-login-submit");a.disabled=!0;try{const s=await m.login({email:t,password:n,remember:o("login-remember").checked});s.two_factor_required?(_(o("login-modal-overlay")),Me(s.challenge_token)):$()}catch(s){p("login","global",s.message||"Connexion impossible.")}finally{a.disabled=!1}});let F=!1;function se(e){F=e,o("login-2fa-code-row").hidden=e,o("login-2fa-recovery-row").hidden=!e,o("login-2fa-intro").textContent=e?"Saisis l'un de tes recovery codes (généré lors de l'activation de la double authentification).":"Saisis le code à 6 chiffres généré par ton application d'authentification.",o("btn-2fa-toggle-recovery").textContent=e?"Utiliser le code de mon application":"Utiliser un recovery code",o("login-2fa-error-global").hidden=!0;const t=o(e?"login-2fa-recovery-code":"login-2fa-code");setTimeout(()=>t.focus(),50)}function Me(e){o("login-2fa-form").dataset.challengeToken=e,o("login-2fa-code").value="",o("login-2fa-recovery-code").value="",se(!1),H(o("login-2fa-modal-overlay"))}o("btn-2fa-toggle-recovery").addEventListener("click",()=>se(!F));o("btn-login-2fa-cancel").addEventListener("click",()=>_(o("login-2fa-modal-overlay")));o("login-2fa-form").addEventListener("submit",async e=>{e.preventDefault(),o("login-2fa-error-global").hidden=!0;const t=e.currentTarget.dataset.challengeToken,n=o("btn-login-2fa-submit");n.disabled=!0;try{F?await m.recover2FA(t,o("login-2fa-recovery-code").value.trim()):await m.verify2FA(t,o("login-2fa-code").value.trim()),$()}catch(a){o("login-2fa-error-global").textContent=a.message||"Code invalide.",o("login-2fa-error-global").hidden=!1}finally{n.disabled=!1}});o("btn-forgot-submit").addEventListener("click",async()=>{o("forgot-error").hidden=!0,o("forgot-result").hidden=!0;const e=o("forgot-email").value.trim();if(!e||!ne.test(e)){o("forgot-error").textContent="Utilise une adresse Gmail valide.",o("forgot-error").hidden=!1;return}const t=o("btn-forgot-submit");t.disabled=!0;try{const n=await m.forgotPassword(e);o("forgot-result").innerHTML=n.dev_reset_link?`${n.message}<br><a href="${n.dev_reset_link}">Lien de réinitialisation (mode développement, aucun service d'email configuré)</a>`:n.message,o("forgot-result").hidden=!1}catch(n){o("forgot-error").textContent=n.message||"Une erreur est survenue.",o("forgot-error").hidden=!1}finally{t.disabled=!1}});async function ie(){try{const e=await fetch("/api/auth/google/start",{redirect:"manual"});if(e.type==="opaqueredirect"||e.status===0){window.location.href="/api/auth/google/start";return}const t=await e.json().catch(()=>({}));p("signup","global",t.error||"Connexion Google indisponible pour le moment."),p("login","global",t.error||"Connexion Google indisponible pour le moment.")}catch{p("signup","global","Connexion Google indisponible pour le moment."),p("login","global","Connexion Google indisponible pour le moment.")}}o("btn-google-signup").addEventListener("click",ie);o("btn-google-login").addEventListener("click",ie);(function(){const n=new URLSearchParams(window.location.search).get("next");if(!n)return;const a={"dashboard.html":"ton dashboard","chapitres.html":"les exercices","exercice.html":"l'entraînement","evaluation.html":"l'évaluation","profil.html":"ton profil"};o("login-next-hint").textContent=`Connecte-toi pour accéder à ${a[n]||"cette page"}.`,o("login-next-hint").hidden=!1,H(o("login-modal-overlay"))})();let L=0;function Te(){L+=1,document.body.style.overflow="hidden"}function Ie(){L=Math.max(0,L-1),L===0&&(document.body.style.overflow="")}function U({id:e,title:t,bodyHtml:n="",bodyEl:a=null,size:s="md",closeOnEscape:i=!0,closeOnOverlayClick:r=!0,showCloseButton:c=!0,onOpen:d,onClose:f}={}){let u=e?document.getElementById(e):null;const b=!!u;u||(u=document.createElement("div"),e&&(u.id=e)),u.className="popup-overlay",u.hidden=!1;const g=document.createElement("div");if(g.className=`popup-card popup-card--${s} card card--glass`,g.setAttribute("role","dialog"),g.setAttribute("aria-modal","true"),t||c){const v=document.createElement("div");if(v.className="popup-header",t){const h=`popup-title-${Math.random().toString(36).slice(2)}`;g.setAttribute("aria-labelledby",h),v.innerHTML=`<h2 class="popup-title" id="${h}">${t}</h2>`}else v.innerHTML='<h2 class="popup-title"></h2>';if(c){const h=document.createElement("button");h.type="button",h.className="popup-close",h.setAttribute("aria-label","Fermer"),h.innerHTML=de("x"),h.addEventListener("click",()=>C()),v.appendChild(h)}g.appendChild(v)}const S=document.createElement("div");S.className="popup-body",a?S.appendChild(a):S.innerHTML=n,g.appendChild(S),u.innerHTML="",u.appendChild(g),b||document.body.appendChild(u),Te(),requestAnimationFrame(()=>u.classList.add("is-open"));let y=!1;function C(){if(y)return;y=!0,u.classList.remove("is-open"),document.removeEventListener("keydown",G),Ie();const v=()=>{u.hidden=!0,u.innerHTML="",f&&f()};let h=!1;const V=()=>{h||(h=!0,v())};u.addEventListener("transitionend",V,{once:!0}),setTimeout(V,300)}function G(v){v.key==="Escape"&&i&&C()}return document.addEventListener("keydown",G),r&&u.addEventListener("click",v=>{v.target===u&&C()}),d&&d(g),{close:C,el:u,bodyEl:S}}function qe({title:e="",label:t="",defaultValue:n="",placeholder:a="",confirmLabel:s="Valider",cancelLabel:i="Annuler"}={}){return new Promise(r=>{let c=!1;const d=g=>{c||(c=!0,r(g))},f=document.createElement("div");f.innerHTML=`
      <div class="form-field">
        ${t?`<label for="popup-prompt-input">${t}</label>`:""}
        <input type="text" id="popup-prompt-input" placeholder="${a}">
      </div>
      <div class="verdict-row">
        <button type="button" class="btn btn-ghost" data-action="cancel">${i}</button>
        <button type="button" class="btn btn-primary" data-action="confirm">${s}</button>
      </div>
    `;const u=U({title:e,bodyEl:f,size:"sm",onClose:()=>d(null)}),b=f.querySelector("#popup-prompt-input");b.value=n,f.querySelector('[data-action="cancel"]').addEventListener("click",()=>{d(null),u.close()}),f.querySelector('[data-action="confirm"]').addEventListener("click",()=>{d(b.value),u.close()}),b.addEventListener("keydown",g=>{g.key==="Enter"&&(g.preventDefault(),d(b.value),u.close())}),requestAnimationFrame(()=>{b.focus(),b.select()})})}function Ne({title:e="",message:t="",confirmLabel:n="Confirmer",cancelLabel:a="Annuler",danger:s=!1}={}){return new Promise(i=>{let r=!1;const c=u=>{r||(r=!0,i(u))},d=document.createElement("div");d.innerHTML=`
      <p class="popup-confirm-message">${t}</p>
      <div class="verdict-row">
        <button type="button" class="btn btn-ghost" data-action="cancel">${a}</button>
        <button type="button" class="btn ${s?"btn-danger-outline":"btn-primary"}" data-action="confirm">${n}</button>
      </div>
    `;const f=U({title:e,bodyEl:d,size:"sm",onClose:()=>c(!1)});d.querySelector('[data-action="cancel"]').addEventListener("click",()=>{c(!1),f.close()}),d.querySelector('[data-action="confirm"]').addEventListener("click",()=>{c(!0),f.close()})})}const st=Object.freeze(Object.defineProperty({__proto__:null,openConfirmPopup:Ne,openPopup:U,openPromptPopup:qe},Symbol.toStringTag,{value:"Module"})),De="1.70",re="novamath:settings";let l=null,z=null,J=Promise.resolve();function je(){try{return JSON.parse(localStorage.getItem(re))||{}}catch{return{}}}function j(e){localStorage.setItem(re,JSON.stringify(e))}function le(e,t){window.dispatchEvent(new CustomEvent("novamath:settings-changed",{detail:{category:e,patch:t,settings:l}}))}function Oe(e){e==="appearance"&&N(l.appearance)}async function it(e){ue();const t=je();l={appearance:O(),...t},N(l.appearance),pe(document.getElementById("theme-toggle"));const n=document.getElementById("sidebar-version");n&&(n.textContent=`NovaMath v${De}`);try{l=await m.getSettings(),j(l),N(l.appearance),le("*",l)}catch{}return l}function Pe(){return l||{appearance:O()}}function Be(e){const t=n=>e(n);return window.addEventListener("novamath:settings-changed",t),()=>window.removeEventListener("novamath:settings-changed",t)}function rt(e,t,n){l||(l={appearance:O()});const a=l[e];return t===null?l={...l,[e]:n}:l={...l,[e]:{...l[e],[t]:n}},j(l),Oe(e),le(e,l[e]),clearTimeout(z),z=setTimeout(()=>{J=J.then(()=>m.saveSettings(l)).then(s=>{l=s,j(l)}).catch(()=>{a!==void 0&&(l={...l,[e]:a})})},250),l}const Y={fr:{"nav.dashboard":"Dashboard","nav.exercices":"Exercices","nav.cours":"Cours","nav.entrainement":"Entraînement","nav.chatbot":"Chatbot","nav.abonnement":"Abonnement","nav.profil":"Voir le profil","settings.title":"Paramètres","settings.cat.account":"Compte","settings.cat.appearance":"Apparence","settings.cat.training":"Entraînement","settings.cat.learning":"Apprentissage","settings.cat.data":"Données","settings.cat.security":"Confidentialité & Sécurité","settings.cat.language":"Langue","settings.cat.chatbot":"Chatbot","settings.cat.help":"Aide & À propos","exercise.notice_fr_only":"Le contenu des exercices reste en français quelle que soit la langue de l'interface.",chatbot_card_view_course:"Voir le cours",chatbot_card_practice:"Commencer un entraînement",chatbot_card_review_weak:"Revoir cette notion",chatbot_card_redo_series:"Refaire cette série",chatbot_mentions_searching:"Recherche…",chatbot_mentions_no_result:"Aucune ressource trouvée.",chatbot_mentions_did_you_mean:"Voulez-vous dire",cmd_palette_placeholder:"Rechercher ou naviguer…",cmd_palette_no_result:"Aucun résultat",cmd_palette_dashboard:"Voir ma progression",cmd_palette_cours:"Parcourir les cours",cmd_palette_chapitres:"Choisir un chapitre",cmd_palette_entrainement:"S'entraîner",cmd_palette_chatbot:"Poser une question",cmd_palette_abonnement:"Passer à Premium ou Ultra",cmd_palette_profil:"Voir mon profil"},en:{"nav.dashboard":"Dashboard","nav.exercices":"Exercises","nav.cours":"Courses","nav.entrainement":"Practice","nav.chatbot":"Chatbot","nav.abonnement":"Subscription","nav.profil":"View profile","settings.title":"Settings","settings.cat.account":"Account","settings.cat.appearance":"Appearance","settings.cat.training":"Practice","settings.cat.learning":"Learning","settings.cat.data":"Data","settings.cat.security":"Privacy & Security","settings.cat.language":"Language","settings.cat.chatbot":"Chatbot","settings.cat.help":"Help & About","exercise.notice_fr_only":"Exercise content stays in French regardless of the interface language.",chatbot_card_view_course:"View the course",chatbot_card_practice:"Start practicing",chatbot_card_review_weak:"Review this topic",chatbot_card_redo_series:"Redo this series",chatbot_mentions_searching:"Searching…",chatbot_mentions_no_result:"No matching resource found.",chatbot_mentions_did_you_mean:"Did you mean",cmd_palette_placeholder:"Search or navigate…",cmd_palette_no_result:"No results",cmd_palette_dashboard:"View my progress",cmd_palette_cours:"Browse courses",cmd_palette_chapitres:"Choose a chapter",cmd_palette_entrainement:"Practice",cmd_palette_chatbot:"Ask a question",cmd_palette_abonnement:"Upgrade to Premium or Ultra",cmd_palette_profil:"View my profile"}};function ce(){var t;return((t=Pe())==null?void 0:t.language)==="en"?"en":"fr"}function He(e,t){var a;const n=ce();return((a=Y[n])==null?void 0:a[e])??Y.fr[e]??t??e}function K(e=document){e.querySelectorAll("[data-i18n]").forEach(t=>{const n=t.getAttribute("data-i18n"),a=t.getAttribute("data-i18n-attr"),s=He(n);a?t.setAttribute(a,s):t.textContent=s}),document.documentElement.setAttribute("lang",ce())}function lt(e=document){K(e),Be(t=>{(t.detail.category==="language"||t.detail.category==="*")&&K(e)})}export{tt as A,U as B,st as C,De as N,Ge as a,lt as b,Ue as c,Ve as d,nt as e,Pe as f,Je as g,Fe as h,it as i,rt as j,Ne as k,Be as l,W as m,at as n,qe as o,Z as p,Ze as q,et as r,Ye as s,He as t,Ke as u,ze as v,Xe as w,We as x,Qe as y,ot as z};
