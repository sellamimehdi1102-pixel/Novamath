const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/i18n.B3NAIOE2.js","assets/api.D9MhFfTx.js","assets/api.DopDIIUb.css","assets/theme.DpqEKRmI.js"])))=>i.map(i=>d[i]);
import{l as W,t as $,f as I,j as z,B as j}from"./i18n.B3NAIOE2.js";import{a as f}from"./api.D9MhFfTx.js";import{i as d,h as J,d as X}from"./theme.DpqEKRmI.js";const _e={free:"Gratuit",premium:"Premium",ultra:"Ultra"},U={free:0,premium:1,ultra:2};function Re(e,t){return(U[e]??0)>=(U[t]??0)}const T=["free","premium","ultra"];function Ne(e){const t=T.indexOf(e);return T[Math.min(t+1,T.length-1)]||"premium"}const Q={chatbot:{label:"Chatbot",requiredPlan:"free"},chatbot_unlimited:{label:"Chatbot illimité",requiredPlan:"premium"},advanced_ai:{label:"Analyse de documents joints",requiredPlan:"ultra"},advanced_explanations:{label:"Explications avancées",requiredPlan:"premium"},courses:{label:"Cours",requiredPlan:"free"},exercises:{label:"Exercices",requiredPlan:"free"},custom_exercises:{label:"Exercices sur mesure",requiredPlan:"ultra"},statistics:{label:"Statistiques",requiredPlan:"free"},history:{label:"Historique",requiredPlan:"free"},goals:{label:"Objectifs quotidiens",requiredPlan:"free"},export:{label:"Export des données",requiredPlan:"free"},profile_analytics:{label:"Statistiques avancées du profil",requiredPlan:"premium"},early_access:{label:"Accès anticipé aux nouveautés",requiredPlan:"ultra"},priority_queue:{label:"File d'attente prioritaire",requiredPlan:"ultra"},priority_support:{label:"Support prioritaire",requiredPlan:"premium"},long_responses:{label:"Réponses longues",requiredPlan:"ultra"}},Te={};function je(e){var t;return((t=Q[e])==null?void 0:t.label)||"Cette fonctionnalité"}function De(e){var t;return((t=Q[e])==null?void 0:t.requiredPlan)||"premium"}const Y="modulepreload",Z=function(e){return"/"+e},F={},ee=function(t,n,s){let o=Promise.resolve();if(n&&n.length>0){let r=function(g){return Promise.all(g.map(C=>Promise.resolve(C).then(x=>({status:"fulfilled",value:x}),x=>({status:"rejected",reason:x}))))};document.getElementsByTagName("link");const i=document.querySelector("meta[property=csp-nonce]"),m=(i==null?void 0:i.nonce)||(i==null?void 0:i.getAttribute("nonce"));o=r(n.map(g=>{if(g=Z(g),g in F)return;F[g]=!0;const C=g.endsWith(".css"),x=C?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${g}"]${x}`))return;const y=document.createElement("link");if(y.rel=C?"stylesheet":Y,C||(y.as="script"),y.crossOrigin="",y.href=g,m&&y.setAttribute("nonce",m),document.head.appendChild(y),C)return new Promise((N,p)=>{y.addEventListener("load",N),y.addEventListener("error",()=>p(new Error(`Unable to preload CSS for ${g}`)))})}))}function l(r){const i=new Event("vite:preloadError",{cancelable:!0});if(i.payload=r,window.dispatchEvent(i),!i.defaultPrevented)throw r}return o.then(r=>{for(const i of r||[])i.status==="rejected"&&l(i.reason);return t().catch(l)})},a=e=>document.getElementById(e);let v,R,c=null,L=null,b=null;function V(){return[{id:"account",label:$("settings.cat.account"),icon:"user"},{id:"appearance",label:$("settings.cat.appearance"),icon:"palette"},{id:"training",label:$("settings.cat.training"),icon:"sliders"},{id:"learning",label:$("settings.cat.learning"),icon:"target"},{id:"chatbot",label:$("settings.cat.chatbot"),icon:"messageSquare"},{id:"security",label:$("settings.cat.security"),icon:"lock"},{id:"language",label:$("settings.cat.language"),icon:"globe"},{id:"help",label:$("settings.cat.help"),icon:"helpCircle"}]}let k=localStorage.getItem("novamath:settings_tab")||"account";V().some(e=>e.id===k)||(k="account");let H=null;function h(e,t=!1){const n=a("settings-toast");clearTimeout(H),n.className=`toast${t?" toast--error":""}`,n.innerHTML=`${d(t?"x":"check")}<span>${e}</span>`,n.hidden=!1,H=setTimeout(()=>{n.classList.add("is-leaving"),n.addEventListener("animationend",()=>{n.hidden=!0},{once:!0})},2600)}function P({title:e,text:t,confirmLabel:n="Confirmer",danger:s=!0,fields:o=[],onConfirm:l}){const r=a("confirm-modal-overlay");a("confirm-modal-title").textContent=e,a("confirm-modal-text").textContent=t||"",a("confirm-modal-error").hidden=!0,a("confirm-modal-error").textContent="";const i=a("confirm-modal-extra");i.innerHTML=o.map(p=>`
    <div class="form-field">
      <label for="modal-field-${p.name}">${p.label}</label>
      <input type="${p.type||"text"}" id="modal-field-${p.name}" placeholder="${p.placeholder||""}" autocomplete="${p.autocomplete||"off"}">
    </div>
  `).join("");const m=a("confirm-modal-confirm");m.textContent=n,m.className=`btn ${s?"btn-danger-outline":"btn-primary"}`;const g=()=>{r.hidden=!0,N()},C=async()=>{var G;const p={};for(const M of o)p[M.name]=((G=a(`modal-field-${M.name}`))==null?void 0:G.value)??"";m.disabled=!0;try{await l(p),g()}catch(M){a("confirm-modal-error").textContent=M.message||"Une erreur est survenue.",a("confirm-modal-error").hidden=!1}finally{m.disabled=!1}},x=()=>g(),y=p=>{p.target===r&&g()};function N(){m.removeEventListener("click",C),a("confirm-modal-cancel").removeEventListener("click",x),r.removeEventListener("click",y)}m.addEventListener("click",C),a("confirm-modal-cancel").addEventListener("click",x),r.addEventListener("click",y),r.hidden=!1,o.length&&setTimeout(()=>{var p;return(p=a(`modal-field-${o[0].name}`))==null?void 0:p.focus()},50)}function u(e,t,n){L=z(e,t,n)}function te(e,t){L=z(e,null,t)}function D(){R.innerHTML=V().map(e=>`
    <button type="button" class="settings-menu-item${e.id===k?" active":""}" data-cat="${e.id}">
      ${d(e.icon)}<span>${e.label}</span>
    </button>
  `).join(""),R.querySelectorAll(".settings-menu-item").forEach(e=>{e.addEventListener("click",()=>{k=e.dataset.cat,localStorage.setItem("novamath:settings_tab",k),D(),w()})})}function q(e,t,n=!1){return`<label class="toggle-switch"><input type="checkbox" id="${e}" ${t?"checked":""} ${n?"disabled":""}><span class="track"></span></label>`}function E(e,t,n){return`
    <div class="setting-row">
      <div class="setting-row-text"><span class="label">${e}</span>${t?`<span class="desc">${t}</span>`:""}</div>
      <div class="setting-row-control">${n}</div>
    </div>`}function A(e,t,n){return`<div class="choice-group" data-group="${e}">${t.map(s=>`
    <button type="button" class="choice-pill${String(s.value)===String(n)?" active":""}" data-value="${s.value}">${s.label}</button>
  `).join("")}</div>`}function S(e,t,n){e.querySelectorAll(`[data-group="${t}"] .choice-pill`).forEach(s=>{s.addEventListener("click",()=>{e.querySelectorAll(`[data-group="${t}"] .choice-pill`).forEach(o=>o.classList.remove("active")),s.classList.add("active"),n(s.dataset.value)})})}function ne(e){return String(e||"").trim().split(/\s+/).slice(0,2).map(n=>{var s;return((s=n[0])==null?void 0:s.toUpperCase())||""}).join("")||"?"}function K(e="cette action"){return`<p class="settings-empty">Le mode invité ne permet pas ${e}. <a href="profil.html" style="color:var(--brand-indigo);">Crée un compte</a> pour en profiter.</p>`}function ae(){return c.is_guest?`
      <h2>${d("user")} Compte</h2>
      <p class="settings-panel-desc">Tu es en mode invité : ta progression n'est pas sauvegardée durablement.</p>
      ${K("la gestion de compte")}
      <div class="settings-actions-grid">
        <a href="profil.html" class="btn btn-primary">Créer un compte</a>
      </div>

      <div class="settings-section">
        <div class="settings-section-title">Cursus</div>
        <div class="settings-actions-grid">
          <button class="btn btn-secondary" id="btn-change-class" type="button">
            <span class="class-badge-label" id="settings-class-badge-label">Seconde</span> — Changer de classe
          </button>
        </div>
      </div>
    `:`
    <h2>${d("user")} Compte</h2>
    <p class="settings-panel-desc">Gère ton identité et la sécurité de ton compte NovaMath.</p>

    <div class="account-summary">
      <div class="account-summary-avatar" id="acc-avatar">${c.avatar?`<img src="${c.avatar}" alt="">`:ne(c.pseudo)}</div>
      <div class="account-summary-meta">
        <div class="name">${c.pseudo}</div>
        <div class="sub">@${c.username}</div>
      </div>
    </div>

    <div class="account-info-grid">
      <div class="account-info-item"><div class="label">Adresse email</div><div class="value">${c.email}</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Identité</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-edit-pseudo">Modifier le pseudo</button>
        <button class="btn btn-secondary" id="btn-edit-email">Modifier l'adresse Gmail</button>
        <button class="btn btn-secondary" id="btn-edit-password">Modifier le mot de passe</button>
        <button class="btn btn-secondary" id="btn-change-photo">Changer la photo</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Cursus</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-change-class" type="button">
          <span class="class-badge-label" id="settings-class-badge-label">Seconde</span> — Changer de classe
        </button>
      </div>
    </div>

    <input type="file" id="avatar-file-input" accept="image/png,image/jpeg,image/webp" hidden>
  `}function se(e,t=480){return new Promise((n,s)=>{const o=new FileReader;o.onerror=()=>s(new Error("Impossible de lire ce fichier.")),o.onload=()=>{const l=new Image;l.onerror=()=>s(new Error("Fichier image invalide.")),l.onload=()=>{const r=Math.min(1,t/Math.max(l.width,l.height)),i=document.createElement("canvas");i.width=Math.round(l.width*r),i.height=Math.round(l.height*r),i.getContext("2d").drawImage(l,0,0,i.width,i.height),n(i.toDataURL("image/jpeg",.85))},l.src=o.result},o.readAsDataURL(e)})}function ie(){X(a("btn-change-class")),!c.is_guest&&(a("btn-edit-pseudo").addEventListener("click",()=>{P({title:"Modifier le pseudo",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"pseudo",label:"Pseudo",placeholder:c.pseudo}],onConfirm:async({pseudo:e})=>{if(!e.trim())throw new Error("Le pseudo est obligatoire.");const{user:t}=await f.updateMe({pseudo:e.trim()});c=t,window.dispatchEvent(new CustomEvent("novamath:account-updated",{detail:c})),w(),h("Pseudo mis à jour")}})}),a("btn-edit-email").addEventListener("click",()=>{P({title:"Modifier l'adresse Gmail",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"email",label:"Nouvelle adresse Gmail",placeholder:"nom@gmail.com"},{name:"current_password",label:"Mot de passe actuel",type:"password"}],onConfirm:async({email:e,current_password:t})=>{const{user:n}=await f.updateMe({email:e,current_password:t});c=n,w(),h("Adresse email mise à jour")}})}),a("btn-edit-password").addEventListener("click",()=>{P({title:"Modifier le mot de passe",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"current_password",label:"Mot de passe actuel",type:"password"},{name:"new_password",label:"Nouveau mot de passe",type:"password"},{name:"confirm_password",label:"Confirmer le nouveau mot de passe",type:"password"}],onConfirm:async({current_password:e,new_password:t,confirm_password:n})=>{await f.changePassword({current_password:e,new_password:t,confirm_password:n}),h("Mot de passe mis à jour")}})}),a("btn-change-photo").addEventListener("click",()=>a("avatar-file-input").click()),a("avatar-file-input").addEventListener("change",async e=>{const t=e.target.files[0];if(e.target.value="",!!t)try{const n=await se(t),{user:s}=await f.updateMe({avatar:n});c=s,window.dispatchEvent(new CustomEvent("novamath:account-updated",{detail:c})),w(),h("Photo de profil mise à jour")}catch(n){h(n.message||"Échec de l'envoi de la photo.",!0)}}))}const oe=[{value:"purple",label:"Nova Purple"},{value:"blue",label:"Bleu"},{value:"green",label:"Vert"},{value:"red",label:"Rose"},{value:"orange",label:"Orange"}];function re(){const e=L.appearance;return`
    <h2>${d("palette")} Apparence</h2>
    <p class="settings-panel-desc">Personnalise l'apparence de NovaMath — tout s'applique immédiatement.</p>

    <div class="settings-section">
      <div class="settings-section-title">Thème</div>
      ${A("theme",[{value:"dark",label:"Mode sombre"},{value:"light",label:"Mode clair"}],J())}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Couleur principale</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Violet par défaut. Change la couleur d'accent dans toute l'interface (boutons, badges, liens, états actifs, graphiques...) — les fonds et le thème clair/sombre ne changent pas.</p>
      <div class="color-swatch-group">
        ${oe.map(t=>`<button type="button" class="color-swatch swatch-${t.value}${e.accent===t.value?" active":""}" data-accent="${t.value}" title="${t.label}" aria-label="${t.label}"></button>`).join("")}
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Taille du texte</div>
      ${A("fontSize",[{value:"normal",label:"Normal"},{value:"large",label:"Grand"}],e.fontSize)}
    </div>

    <div class="settings-section">
      ${E("Animations","Transitions et animations dans toute l'interface.",q("toggle-animations",e.animations))}
    </div>
  `}function le(){S(v,"theme",e=>u("appearance","theme",e)),S(v,"fontSize",e=>u("appearance","fontSize",e)),v.querySelectorAll(".color-swatch").forEach(e=>{e.addEventListener("click",()=>{v.querySelectorAll(".color-swatch").forEach(t=>t.classList.remove("active")),e.classList.add("active"),u("appearance","accent",e.dataset.accent)})}),a("toggle-animations").addEventListener("change",e=>u("appearance","animations",e.target.checked))}function ce(){const e=L.training;return`
    <h2>${d("sliders")} Entraînement</h2>
    <p class="settings-panel-desc">Ajuste le déroulement de tes séries d'exercices.</p>

    <div class="settings-section">
      <div class="settings-section-title">Nombre de questions par série</div>
      ${A("questionsPerSeries",[5,10,15,20].map(t=>({value:t,label:String(t)})),e.questionsPerSeries)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Mode de correction</div>
      ${A("correctionDisplay",[{value:"chaque_question",label:"Après chaque question"},{value:"fin",label:"À la fin de la série"}],e.correctionDisplay)}
    </div>

    <div class="settings-section">
      ${E("Chronomètre","Limite de temps par question en mode Défi chronométré.",q("toggle-chrono",e.chrono))}
      ${E("Effets sonores","Petits sons de confirmation en cas de bonne/mauvaise réponse.",q("toggle-sound",e.soundEffects))}
    </div>
  `}function de(){S(v,"questionsPerSeries",e=>u("training","questionsPerSeries",Number(e))),S(v,"correctionDisplay",e=>u("training","correctionDisplay",e)),a("toggle-chrono").addEventListener("change",e=>u("training","chrono",e.target.checked)),a("toggle-sound").addEventListener("change",e=>u("training","soundEffects",e.target.checked))}function ue(){const e=L.learning;return`
    <h2>${d("target")} Apprentissage</h2>
    <p class="settings-panel-desc">Rends NovaMath plus intelligent en précisant tes objectifs.</p>

    <div class="settings-section">
      <div class="settings-section-title">Objectif quotidien</div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Nombre d'exercices souhaités</span></div>
        <div class="setting-row-control"><input type="number" min="1" max="100" id="input-daily-exercises" value="${e.dailyGoalExercises}" style="width:80px;" class="learning-input"></div>
      </div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Temps quotidien (minutes)</span></div>
        <div class="setting-row-control"><input type="number" min="1" max="240" id="input-daily-time" value="${e.dailyGoalTimeMin}" style="width:80px;" class="learning-input"></div>
      </div>
    </div>

    <div class="settings-section">
      ${E("Révision espacée","Refait réapparaître les exercices déjà vus au bon moment pour mémoriser durablement.",q("toggle-spaced",e.spacedRepetition))}
    </div>
  `}function pe(){a("input-daily-exercises").addEventListener("change",e=>u("learning","dailyGoalExercises",Math.max(1,Number(e.target.value)||1))),a("input-daily-time").addEventListener("change",e=>u("learning","dailyGoalTimeMin",Math.max(1,Number(e.target.value)||1))),a("toggle-spaced").addEventListener("change",e=>u("learning","spacedRepetition",e.target.checked))}function me(){const e=L.chatbot||{};return`
    <h2>${d("messageSquare")} Chatbot</h2>
    <p class="settings-panel-desc">Personnalise l'assistant pédagogique NovaMath — tout s'applique dès le prochain message.</p>

    <div class="settings-section">
      <div class="settings-section-title">Niveau d'explication</div>
      ${A("chatbotExplanationLevel",[{value:"auto",label:"Automatique"},{value:"college",label:"Collège"},{value:"lycee",label:"Lycée"}],e.explanationLevel)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Mode</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Change la façon dont le chatbot construit ses réponses.</p>
      ${A("chatbotMode",[{value:"professeur",label:"Professeur"},{value:"pas_a_pas",label:"Pas-à-pas"},{value:"rapide",label:"Rapide"}],e.mode)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Longueur des réponses</div>
      ${A("chatbotResponseLength",[{value:"court",label:"Courtes"},{value:"normal",label:"Normales"},{value:"detaille",label:"Détaillées"}],e.responseLength)}
    </div>

    <div class="settings-section">
      ${E("Mémoire","Le chatbot retient tes préférences et ta progression d'une conversation à l'autre.",q("toggle-chatbot-memory",e.memoryEnabled!==!1))}
      ${E("Historique","Le chatbot relit les messages précédents de la conversation en cours.",q("toggle-chatbot-history",e.historyEnabled!==!1))}
      ${E("Affichage progressif","Les réponses s'affichent au fur et à mesure plutôt que d'un coup.",q("toggle-chatbot-streaming",e.streaming!==!1))}
    </div>
  `}function ge(){S(v,"chatbotExplanationLevel",e=>u("chatbot","explanationLevel",e)),S(v,"chatbotMode",e=>u("chatbot","mode",e)),S(v,"chatbotResponseLength",e=>u("chatbot","responseLength",e)),a("toggle-chatbot-memory").addEventListener("change",e=>u("chatbot","memoryEnabled",e.target.checked)),a("toggle-chatbot-history").addEventListener("change",e=>u("chatbot","historyEnabled",e.target.checked)),a("toggle-chatbot-streaming").addEventListener("change",e=>u("chatbot","streaming",e.target.checked))}function ve(){return c.is_guest?`<h2>${d("lock")} Confidentialité & Sécurité</h2>${K("la gestion de la sécurité")}`:`
    <h2>${d("lock")} Confidentialité & Sécurité</h2>
    <p class="settings-panel-desc">Garde le contrôle de l'accès à ton compte.</p>

    <div class="settings-section">
      ${E("Authentification à deux facteurs",c.two_factor_enabled?"Activée — un code à usage unique est demandé à chaque connexion.":"Protège ton compte avec un code généré par Google Authenticator, Microsoft Authenticator, Authy, 1Password ou Bitwarden.",c.two_factor_enabled?'<button type="button" class="btn btn-danger-outline btn-sm" id="btn-2fa-disable">Désactiver</button>':'<button type="button" class="btn btn-primary btn-sm" id="btn-2fa-enable">Activer</button>')}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Appareils</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-logout-others">Déconnecter tous les autres appareils</button>
      </div>
    </div>

    ${b===null?"":`
    <div class="settings-section">
      <div class="settings-section-title">Cookies</div>
      ${E("Cookies statistiques","Mesure d'audience anonyme pour améliorer NovaMath.",q("toggle-cookie-statistics",b.statistics))}
      ${E("Cookies marketing","Personnalisation des communications NovaMath.",q("toggle-cookie-marketing",b.marketing))}
    </div>`}

    <div class="settings-section">
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-delete-account-sec">Supprimer définitivement mon compte</button>
      </div>
    </div>
  `}async function be(){let e;try{e=await f.setup2FA()}catch(r){h(r.message||"Impossible de démarrer la configuration.",!0);return}const t=document.createElement("div");t.innerHTML=`
    <p class="settings-panel-desc">Scanne ce QR code avec ton application d'authentification (Google Authenticator, Microsoft Authenticator, Authy, 1Password, Bitwarden...).</p>
    <div class="twofa-qr-wrap"><img src="${e.qr_code}" alt="QR code d'activation de la double authentification" width="200" height="200"></div>
    <div class="form-field">
      <label for="twofa-secret-text">Impossible de scanner ? Saisis cette clé manuellement</label>
      <div class="twofa-secret-row">
        <code id="twofa-secret-text">${e.secret}</code>
        <button type="button" class="btn btn-ghost btn-sm" id="btn-2fa-copy-secret" aria-label="Copier la clé">${d("copy")}</button>
      </div>
    </div>
    <div class="form-field">
      <label for="twofa-setup-code">Code à 6 chiffres généré par l'application</label>
      <input type="text" id="twofa-setup-code" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" placeholder="123456">
      <span class="form-error" id="twofa-setup-error" hidden></span>
    </div>
    <div class="verdict-row">
      <button type="button" class="btn btn-ghost" data-action="cancel">Annuler</button>
      <button type="button" class="btn btn-primary" data-action="confirm">Activer</button>
    </div>
  `;const n=j({title:"Activer la double authentification",bodyEl:t,size:"sm"}),s=t.querySelector("#twofa-setup-code"),o=t.querySelector("#twofa-setup-error");t.querySelector("#btn-2fa-copy-secret").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(e.secret),h("Clé copiée")}catch{h("Copie impossible sur ce navigateur.",!0)}}),t.querySelector('[data-action="cancel"]').addEventListener("click",()=>n.close());async function l(){o.hidden=!0;const r=s.value.trim();if(!/^\d{6}$/.test(r)){o.textContent="Saisis les 6 chiffres affichés par ton application.",o.hidden=!1;return}const i=t.querySelector('[data-action="confirm"]');i.disabled=!0;try{const{recovery_codes:m}=await f.enable2FA(r);c.two_factor_enabled=!0,n.close(),w(),h("Authentification à deux facteurs activée"),fe(m)}catch(m){o.textContent=m.message||"Code invalide.",o.hidden=!1}finally{i.disabled=!1}}t.querySelector('[data-action="confirm"]').addEventListener("click",l),s.addEventListener("keydown",r=>{r.key==="Enter"&&(r.preventDefault(),l())}),requestAnimationFrame(()=>s.focus())}function fe(e){const t=document.createElement("div");t.innerHTML=`
    <p class="settings-panel-desc">Conserve ces codes de récupération en lieu sûr : chacun permet de te connecter <strong>une seule fois</strong> si tu perds l'accès à ton application d'authentification. Ils ne seront plus jamais affichés.</p>
    <ul class="twofa-recovery-list">${e.map(s=>`<li><code>${s}</code></li>`).join("")}</ul>
    <div class="verdict-row">
      <button type="button" class="btn btn-secondary" id="btn-2fa-copy-codes">${d("copy")} Copier</button>
      <button type="button" class="btn btn-primary" id="btn-2fa-download-codes">${d("download")} Télécharger</button>
    </div>
  `;const n=j({title:"Codes de récupération",bodyEl:t,size:"sm"});return t.querySelector("#btn-2fa-copy-codes").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(e.join(`
`)),h("Codes copiés")}catch{h("Copie impossible sur ce navigateur.",!0)}}),t.querySelector("#btn-2fa-download-codes").addEventListener("click",()=>{const s=new Blob([e.join(`
`)+`
`],{type:"text/plain"}),o=URL.createObjectURL(s),l=document.createElement("a");l.href=o,l.download="novamath-recovery-codes.txt",document.body.appendChild(l),l.click(),l.remove(),URL.revokeObjectURL(o)}),n}function he(){var e,t;c.is_guest||((e=a("btn-2fa-enable"))==null||e.addEventListener("click",()=>be()),(t=a("btn-2fa-disable"))==null||t.addEventListener("click",()=>{P({title:"Désactiver la double authentification",text:"Ton compte ne sera plus protégé par un code à usage unique. Confirme avec ton mot de passe et un code de ton application d'authentification.",confirmLabel:"Désactiver",fields:[{name:"password",label:"Mot de passe actuel",type:"password"},{name:"code",label:"Code à 6 chiffres",placeholder:"123456"}],onConfirm:async({password:n,code:s})=>{await f.disable2FA(n,s),c.two_factor_enabled=!1,w(),h("Authentification à deux facteurs désactivée")}})}),a("btn-logout-others").addEventListener("click",()=>{P({title:"Déconnecter tous les autres appareils",text:"Toutes les sessions actives, sauf celle-ci, seront immédiatement fermées.",confirmLabel:"Déconnecter",onConfirm:async()=>{await f.logoutOtherSessions(),h("Autres appareils déconnectés")}})}),b!==null&&(a("toggle-cookie-statistics").addEventListener("change",n=>{b={...b,statistics:n.target.checked},f.setCookieConsent(b.statistics,b.marketing).catch(()=>{})}),a("toggle-cookie-marketing").addEventListener("change",n=>{b={...b,marketing:n.target.checked},f.setCookieConsent(b.statistics,b.marketing).catch(()=>{})})),a("btn-delete-account-sec").addEventListener("click",()=>{P({title:"Supprimer définitivement le compte",text:"Cette action est irréversible.",confirmLabel:"Supprimer mon compte",fields:[{name:"password",label:"Mot de passe",type:"password"}],onConfirm:async({password:n})=>{await f.deleteMe({password:n,confirm:!0}),window.location.href="/"}})}))}const ye=[{code:"fr",name:"Français",native:"Français"},{code:"en",name:"English",native:"English"}],Ee=[{name:"العربية",native:"Arabe"},{name:"Español",native:"Espagnol"},{name:"Deutsch",native:"Allemand"}];function we(){return`
    <h2>${d("globe")} Langue</h2>
    <p class="settings-panel-desc">Choisis la langue de NovaMath.</p>
    <div class="language-grid">
      ${ye.map(e=>`
        <button type="button" class="language-card${L.language===e.code?" active":""}" data-lang="${e.code}">
          <div class="lang-name">${e.name}</div>
          <div class="lang-native">${e.native}</div>
        </button>
      `).join("")}
      ${Ee.map(e=>`
        <button type="button" class="language-card is-disabled" disabled title="Bientôt disponible">
          <div class="lang-name">${e.name}</div>
          <div class="lang-native">${e.native} · Bientôt disponible</div>
        </button>
      `).join("")}
    </div>
    <p class="settings-panel-desc" style="margin-top:18px;">${L.language==="en"?"Exercise content stays in French regardless of the interface language — only the interface itself is translated.":"Le contenu des exercices reste en français quelle que soit la langue de l'interface — seule l'interface elle-même est traduite."}</p>
  `}function Le(){v.querySelectorAll(".language-card").forEach(e=>{e.addEventListener("click",()=>{te("language",e.dataset.lang),w()})})}const Ce={faq:{title:"FAQ — Questions fréquentes",body:`
      <p><strong>Le contenu des exercices est-il disponible en anglais ?</strong><br>Non : l'interface (menus, boutons, paramètres) est traduite en anglais, mais les énoncés d'exercices restent en français.</p>
      <p><strong>Pourquoi mes préférences ne sont-elles pas sauvegardées en mode invité ?</strong><br>Un compte invité est temporaire par conception : ses données sont automatiquement supprimées à la fin de la session. Crée un compte pour conserver ta progression durablement.</p>
      <p><strong>Comment changer le nombre d'exercices par série ?</strong><br>Paramètres → Entraînement → « Nombre de questions par série ». Le changement s'applique immédiatement à toutes les prochaines séries, depuis n'importe quelle page.</p>
      <p><strong>Le chronomètre reste actif alors que je l'ai désactivé, que faire ?</strong><br>Ce comportement a été corrigé : la désactivation est désormais appliquée en direct, y compris pendant une série déjà en cours d'affichage.</p>
      <p><strong>Comment supprimer mon compte ?</strong><br>Page Profil → « Supprimer définitivement le compte ». Cette action est irréversible.</p>`},guide:{title:"Guide utilisateur",body:`
      <p><strong>Démarrer une série</strong> — depuis Entraînement, choisis un mode (Révisions, Objectif du jour, Examen blanc, Défi chronométré, Erreurs précédentes) puis lance-la. Depuis Exercices, ouvre un chapitre, sélectionne une ou plusieurs notions puis clique sur « Commencer la série ».</p>
      <p><strong>Reprendre une série interrompue</strong> — le Dashboard affiche une carte « Continuer » tant qu'une série n'est pas terminée.</p>
      <p><strong>Personnaliser l'apparence</strong> — Paramètres → Apparence permet de changer le thème clair/sombre, la couleur d'accent, la taille du texte et les animations ; chaque changement s'applique instantanément à tout le site.</p>
      <p><strong>Suivre ses objectifs</strong> — Paramètres → Apprentissage définit l'objectif quotidien (nombre d'exercices, temps), visible en temps réel sur le Dashboard.</p>`},contact:{title:"Nous contacter",body:`
      <p>Le moyen le plus rapide de nous joindre est la section Avis de la page d'accueil, consultée en priorité par l'équipe.</p>
      <p>Pour un bug ou une suggestion, décris précisément le contexte (page, action effectuée, comportement attendu) : cela accélère beaucoup la résolution.</p>`},privacy:{title:"Politique de confidentialité",body:`
      <p>NovaMath collecte uniquement les données nécessaires au fonctionnement du service : identifiant de compte, pseudo, adresse email, préférences, et historique d'entraînement (exercices réalisés, résultats, durée).</p>
      <p>Ces données ne sont jamais vendues ni partagées avec des tiers à des fins commerciales. Elles servent exclusivement à faire fonctionner le suivi de progression et la personnalisation de l'entraînement.</p>
      <p>Un compte invité est entièrement temporaire : ses données sont supprimées automatiquement à la fin de la session, sans action nécessaire de ta part.</p>
      <p>Tu peux à tout moment demander une copie de tes données ou la suppression définitive de ton compte (Paramètres → Compte) via la page Nous contacter.</p>`},terms:{title:"Conditions générales d'utilisation",body:`
      <p>L'utilisation de NovaMath implique l'acceptation des présentes conditions. Le service est fourni « en l'état », à des fins d'entraînement pédagogique, sans garantie d'exhaustivité du programme scolaire.</p>
      <p>Chaque utilisateur est responsable de la confidentialité de son mot de passe. Toute utilisation frauduleuse ou automatisée (scripts, bots) du service est interdite et peut entraîner la suspension du compte.</p>
      <p>NovaMath se réserve le droit de faire évoluer les fonctionnalités du service ; les préférences et la progression des utilisateurs sont préservées lors de ces évolutions dans la mesure du possible.</p>`}};function O(e){const t=Ce[e];t&&ee(async()=>{const{openPopup:n}=await import("./i18n.B3NAIOE2.js").then(s=>s.C);return{openPopup:n}},__vite__mapDeps([0,1,2,3])).then(({openPopup:n})=>{n({title:t.title,bodyHtml:`<div class="help-page-content">${t.body}</div>`,size:"md"})})}function $e(){return`
    <h2>${d("helpCircle")} Aide & À propos</h2>
    <p class="settings-panel-desc">Tout savoir sur NovaMath, comment l'utiliser, et comment nous contacter.</p>

    <div class="settings-section">
      <div class="settings-section-title">Aide</div>
      <div class="help-links">
        <button class="help-link" data-help="guide">Guide utilisateur ${d("arrowRight")}</button>
        <button class="help-link" data-help="faq">FAQ ${d("arrowRight")}</button>
        <button class="help-link" id="help-support-link">Nous contacter ${d("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Légal</div>
      <div class="help-links">
        <button class="help-link" data-help="terms">Conditions générales d'utilisation ${d("arrowRight")}</button>
        <button class="help-link" data-help="privacy">Politique de confidentialité ${d("arrowRight")}</button>
      </div>
    </div>
  `}function qe(){v.querySelectorAll("[data-help]").forEach(e=>{e.addEventListener("click",()=>O(e.dataset.help))}),a("help-support-link").addEventListener("click",()=>O("contact"))}const B={account:[ae,ie],appearance:[re,le],training:[ce,de],learning:[ue,pe],chatbot:[me,ge],security:[ve,he],language:[we,Le],help:[$e,qe]};function w(){const[e,t]=B[k]||B.account;v.innerHTML=e(),t()}async function xe(e){v=e.querySelector("#settings-panel"),R=e.querySelector("#settings-menu"),L=I();try{const{user:t}=await f.me();c=t}catch{window.location.href="/";return}D(),w(),c.is_guest||f.getCookieConsent().then(t=>{b=t,k==="security"&&w()}).catch(()=>{})}W(e=>{e.detail.category!=="language"&&e.detail.category!=="*"||!v||!R||(L=I(),D(),w())});const ke=`
  <nav class="settings-menu" id="settings-menu" aria-label="Catégories de paramètres"></nav>
  <div class="settings-panel" id="settings-panel"></div>

  <div class="modal-overlay" id="confirm-modal-overlay" hidden>
    <div class="modal-card card">
      <h3 id="confirm-modal-title">Confirmer l'action</h3>
      <p id="confirm-modal-text"></p>
      <div id="confirm-modal-extra"></div>
      <span class="form-error form-error--global" id="confirm-modal-error" hidden></span>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-danger-outline" id="confirm-modal-confirm">Confirmer</button>
        <button type="button" class="btn btn-ghost" id="confirm-modal-cancel">Annuler</button>
      </div>
    </div>
  </div>

  <div class="toast" id="settings-toast" hidden></div>
`;let _=null;function Ae(){if(_)return _;const e=document.createElement("div");e.className="settings-shell",e.innerHTML=ke;const t=j({id:"settings-popup-overlay",title:$("settings.title"),bodyEl:e,size:"xl",onClose:()=>{_=null}});return _=t,xe(e),t}function Ge(e){e&&e.addEventListener("click",()=>Ae())}export{_e as P,Te as a,Ge as b,je as f,Ne as n,Re as p,De as r};
