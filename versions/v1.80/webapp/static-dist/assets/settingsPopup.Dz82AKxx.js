const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/pdfExport.D1fB8DmB.js","assets/api.CC07HWUE.js","assets/api.BFPSYiBF.css","assets/i18n.ja2ECFcd.js","assets/theme.BLPjMu9D.js"])))=>i.map(i=>d[i]);
import{l as ie,t as L,f as X,N as Z,j as J,B as I}from"./i18n.ja2ECFcd.js";import{a as u}from"./api.CC07HWUE.js";import{i as s,h as se,d as oe}from"./theme.BLPjMu9D.js";const Qe={free:"Gratuit",premium:"Premium",ultra:"Ultra"},B={free:0,premium:1,ultra:2};function Ke(e,t){return(B[e]??0)>=(B[t]??0)}const G=["free","premium","ultra"];function We(e){const t=G.indexOf(e);return G[Math.min(t+1,G.length-1)]||"premium"}const Y={chatbot:{label:"Chatbot IA",requiredPlan:"free"},chatbot_unlimited:{label:"Chatbot IA illimité",requiredPlan:"premium"},advanced_ai:{label:"IA avancée (analyse de documents joints)",requiredPlan:"ultra"},advanced_explanations:{label:"Explications avancées",requiredPlan:"premium"},courses:{label:"Cours",requiredPlan:"free"},exercises:{label:"Exercices",requiredPlan:"free"},custom_exercises:{label:"Exercices sur mesure",requiredPlan:"ultra"},statistics:{label:"Statistiques",requiredPlan:"free"},history:{label:"Historique",requiredPlan:"free"},goals:{label:"Objectifs quotidiens",requiredPlan:"free"},export:{label:"Export des données",requiredPlan:"free"},profile_analytics:{label:"Statistiques avancées du profil",requiredPlan:"premium"},early_access:{label:"Accès anticipé aux nouveautés",requiredPlan:"ultra"},priority_queue:{label:"File d'attente prioritaire",requiredPlan:"ultra"},priority_support:{label:"Support prioritaire",requiredPlan:"premium"},long_responses:{label:"Réponses longues",requiredPlan:"ultra"}},Xe={};function Ze(e){var t;return((t=Y[e])==null?void 0:t.label)||"Cette fonctionnalité"}function Je(e){var t;return((t=Y[e])==null?void 0:t.requiredPlan)||"premium"}const re="modulepreload",le=function(e){return"/"+e},V={},ee=function(t,n,i){let c=Promise.resolve();if(n&&n.length>0){let d=function($){return Promise.all($.map(P=>Promise.resolve(P).then(A=>({status:"fulfilled",value:A}),A=>({status:"rejected",reason:A}))))};document.getElementsByTagName("link");const l=document.querySelector("meta[property=csp-nonce]"),y=(l==null?void 0:l.nonce)||(l==null?void 0:l.getAttribute("nonce"));c=d(n.map($=>{if($=le($),$ in V)return;V[$]=!0;const P=$.endsWith(".css"),A=P?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${$}"]${A}`))return;const w=document.createElement("link");if(w.rel=P?"stylesheet":re,P||(w.as="script"),w.crossOrigin="",w.href=$,y&&w.setAttribute("nonce",y),document.head.appendChild(w),P)return new Promise((O,b)=>{w.addEventListener("load",O),w.addEventListener("error",()=>b(new Error(`Unable to preload CSS for ${$}`)))})}))}function p(d){const l=new Event("vite:preloadError",{cancelable:!0});if(l.payload=d,window.dispatchEvent(l),!l.defaultPrevented)throw d}return c.then(d=>{for(const l of d||[])l.status==="rejected"&&p(l.reason);return t().catch(p)})},a=e=>document.getElementById(e);let g,F,o=null,q=null,M=null,R=null,E=null,D=null;function te(){return[{id:"account",label:L("settings.cat.account"),icon:"user"},{id:"appearance",label:L("settings.cat.appearance"),icon:"palette"},{id:"training",label:L("settings.cat.training"),icon:"sliders"},{id:"learning",label:L("settings.cat.learning"),icon:"target"},{id:"data",label:L("settings.cat.data"),icon:"database"},{id:"chatbot",label:L("settings.cat.chatbot"),icon:"messageSquare"},{id:"security",label:L("settings.cat.security"),icon:"lock"},{id:"language",label:L("settings.cat.language"),icon:"globe"},{id:"help",label:L("settings.cat.help"),icon:"helpCircle"}]}let k=localStorage.getItem("novamath:settings_tab")||"account";te().some(e=>e.id===k)||(k="account");let Q=null;function v(e,t=!1){const n=a("settings-toast");clearTimeout(Q),n.className=`toast${t?" toast--error":""}`,n.innerHTML=`${s(t?"x":"check")}<span>${e}</span>`,n.hidden=!1,Q=setTimeout(()=>{n.classList.add("is-leaving"),n.addEventListener("animationend",()=>{n.hidden=!0},{once:!0})},2600)}function C({title:e,text:t,confirmLabel:n="Confirmer",danger:i=!0,fields:c=[],onConfirm:p}){const d=a("confirm-modal-overlay");a("confirm-modal-title").textContent=e,a("confirm-modal-text").textContent=t||"",a("confirm-modal-error").hidden=!0,a("confirm-modal-error").textContent="";const l=a("confirm-modal-extra");l.innerHTML=c.map(b=>`
    <div class="form-field">
      <label for="modal-field-${b.name}">${b.label}</label>
      <input type="${b.type||"text"}" id="modal-field-${b.name}" placeholder="${b.placeholder||""}" autocomplete="${b.autocomplete||"off"}">
    </div>
  `).join("");const y=a("confirm-modal-confirm");y.textContent=n,y.className=`btn ${i?"btn-danger-outline":"btn-primary"}`;const $=()=>{d.hidden=!0,O()},P=async()=>{var z;const b={};for(const N of c)b[N.name]=((z=a(`modal-field-${N.name}`))==null?void 0:z.value)??"";y.disabled=!0;try{await p(b),$()}catch(N){a("confirm-modal-error").textContent=N.message||"Une erreur est survenue.",a("confirm-modal-error").hidden=!1}finally{y.disabled=!1}},A=()=>$(),w=b=>{b.target===d&&$()};function O(){y.removeEventListener("click",P),a("confirm-modal-cancel").removeEventListener("click",A),d.removeEventListener("click",w)}y.addEventListener("click",P),a("confirm-modal-cancel").addEventListener("click",A),d.addEventListener("click",w),d.hidden=!1,c.length&&setTimeout(()=>{var b;return(b=a(`modal-field-${c[0].name}`))==null?void 0:b.focus()},50)}function r(e,t,n){q=J(e,t,n)}function ce(e,t){q=J(e,null,t)}function H(){F.innerHTML=te().map(e=>`
    <button type="button" class="settings-menu-item${e.id===k?" active":""}" data-cat="${e.id}">
      ${s(e.icon)}<span>${e.label}</span>
    </button>
  `).join(""),F.querySelectorAll(".settings-menu-item").forEach(e=>{e.addEventListener("click",()=>{k=e.dataset.cat,localStorage.setItem("novamath:settings_tab",k),H(),m()})})}function f(e,t,n=!1){return`<label class="toggle-switch"><input type="checkbox" id="${e}" ${t?"checked":""} ${n?"disabled":""}><span class="track"></span></label>`}function h(e,t,n){return`
    <div class="setting-row">
      <div class="setting-row-text"><span class="label">${e}</span>${t?`<span class="desc">${t}</span>`:""}</div>
      <div class="setting-row-control">${n}</div>
    </div>`}function S(e,t,n){return`<div class="choice-group" data-group="${e}">${t.map(i=>`
    <button type="button" class="choice-pill${String(i.value)===String(n)?" active":""}" data-value="${i.value}">${i.label}</button>
  `).join("")}</div>`}function x(e,t,n){e.querySelectorAll(`[data-group="${t}"] .choice-pill`).forEach(i=>{i.addEventListener("click",()=>{e.querySelectorAll(`[data-group="${t}"] .choice-pill`).forEach(c=>c.classList.remove("active")),i.classList.add("active"),n(i.dataset.value)})})}function _(e){if(!e)return"—";try{return new Date(e).toLocaleDateString("fr-FR",{day:"numeric",month:"long",year:"numeric"})}catch{return e}}function de(e){const t=e||0;if(t<60)return`${t} s`;const n=Math.floor(t/3600),i=Math.round(t%3600/60);return n?`${n} h ${i} min`:`${i} min`}function ue(e){return String(e||"").trim().split(/\s+/).slice(0,2).map(n=>{var i;return((i=n[0])==null?void 0:i.toUpperCase())||""}).join("")||"?"}function U(e="cette action"){return`<p class="settings-empty">Le mode invité ne permet pas ${e}. <a href="profil.html" style="color:var(--brand-indigo);">Crée un compte</a> pour en profiter.</p>`}function pe(){return o.is_guest?`
      <h2>${s("user")} Compte</h2>
      <p class="settings-panel-desc">Tu es en mode invité : ta progression n'est pas sauvegardée durablement.</p>
      ${U("la gestion de compte")}
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
    <h2>${s("user")} Compte</h2>
    <p class="settings-panel-desc">Gère ton identité et la sécurité de ton compte NovaMath.</p>

    <div class="account-summary">
      <div class="account-summary-avatar" id="acc-avatar">${o.avatar?`<img src="${o.avatar}" alt="">`:ue(o.pseudo)}</div>
      <div class="account-summary-meta">
        <div class="name">${o.pseudo}</div>
        <div class="sub">@${o.username}</div>
      </div>
    </div>

    <div class="account-info-grid">
      <div class="account-info-item"><div class="label">Adresse email</div><div class="value">${o.email}</div></div>
      <div class="account-info-item"><div class="label">Compte vérifié</div><div class="value">${o.email_verified?s("check")+" Vérifié":"Non vérifié"}</div></div>
      <div class="account-info-item"><div class="label">Date de création</div><div class="value">${_(o.created_at)}</div></div>
      <div class="account-info-item"><div class="label">Identifiant utilisateur</div><div class="value">#${o.id}</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Identité</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-edit-pseudo">Modifier le pseudo</button>
        <button class="btn btn-secondary" id="btn-edit-email">Modifier l'adresse Gmail</button>
        <button class="btn btn-secondary" id="btn-edit-password">Modifier le mot de passe</button>
        <button class="btn btn-secondary" id="btn-change-photo">Changer la photo</button>
        <button class="btn btn-secondary" id="btn-remove-photo" ${o.avatar?"":"disabled"}>Supprimer la photo</button>
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

    <div class="settings-section danger-zone">
      <div class="settings-section-title">Zone sensible</div>
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-logout">Déconnexion</button>
        <button class="btn btn-danger-outline" id="btn-delete-account">Supprimer définitivement le compte</button>
      </div>
    </div>

    <input type="file" id="avatar-file-input" accept="image/png,image/jpeg,image/webp" hidden>
  `}function me(e,t=480){return new Promise((n,i)=>{const c=new FileReader;c.onerror=()=>i(new Error("Impossible de lire ce fichier.")),c.onload=()=>{const p=new Image;p.onerror=()=>i(new Error("Fichier image invalide.")),p.onload=()=>{const d=Math.min(1,t/Math.max(p.width,p.height)),l=document.createElement("canvas");l.width=Math.round(p.width*d),l.height=Math.round(p.height*d),l.getContext("2d").drawImage(p,0,0,l.width,l.height),n(l.toDataURL("image/jpeg",.85))},p.src=c.result},c.readAsDataURL(e)})}function ve(){oe(a("btn-change-class")),!o.is_guest&&(a("btn-edit-pseudo").addEventListener("click",()=>{C({title:"Modifier le pseudo",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"pseudo",label:"Pseudo",placeholder:o.pseudo}],onConfirm:async({pseudo:e})=>{if(!e.trim())throw new Error("Le pseudo est obligatoire.");const{user:t}=await u.updateMe({pseudo:e.trim()});o=t,window.dispatchEvent(new CustomEvent("novamath:account-updated",{detail:o})),m(),v("Pseudo mis à jour")}})}),a("btn-edit-email").addEventListener("click",()=>{C({title:"Modifier l'adresse Gmail",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"email",label:"Nouvelle adresse Gmail",placeholder:"nom@gmail.com"},{name:"current_password",label:"Mot de passe actuel",type:"password"}],onConfirm:async({email:e,current_password:t})=>{const{user:n}=await u.updateMe({email:e,current_password:t});o=n,m(),v("Adresse email mise à jour")}})}),a("btn-edit-password").addEventListener("click",()=>{C({title:"Modifier le mot de passe",confirmLabel:"Enregistrer",danger:!1,fields:[{name:"current_password",label:"Mot de passe actuel",type:"password"},{name:"new_password",label:"Nouveau mot de passe",type:"password"},{name:"confirm_password",label:"Confirmer le nouveau mot de passe",type:"password"}],onConfirm:async({current_password:e,new_password:t,confirm_password:n})=>{await u.changePassword({current_password:e,new_password:t,confirm_password:n}),v("Mot de passe mis à jour")}})}),a("btn-change-photo").addEventListener("click",()=>a("avatar-file-input").click()),a("avatar-file-input").addEventListener("change",async e=>{const t=e.target.files[0];if(e.target.value="",!!t)try{const n=await me(t),{user:i}=await u.updateMe({avatar:n});o=i,window.dispatchEvent(new CustomEvent("novamath:account-updated",{detail:o})),m(),v("Photo de profil mise à jour")}catch(n){v(n.message||"Échec de l'envoi de la photo.",!0)}}),a("btn-remove-photo").addEventListener("click",()=>{C({title:"Supprimer la photo de profil",text:"Ta photo sera remplacée par tes initiales. Cette action est réversible en ajoutant une nouvelle photo.",confirmLabel:"Supprimer",onConfirm:async()=>{const{user:e}=await u.updateMe({avatar:null});o=e,window.dispatchEvent(new CustomEvent("novamath:account-updated",{detail:o})),m(),v("Photo supprimée")}})}),a("btn-logout").addEventListener("click",()=>{C({title:"Se déconnecter",text:"Tu devras te reconnecter pour retrouver ta progression sur cet appareil.",confirmLabel:"Déconnexion",danger:!1,onConfirm:async()=>{await u.logout(),window.location.href="/"}})}),a("btn-delete-account").addEventListener("click",()=>{C({title:"Supprimer définitivement le compte",text:"Cette action est irréversible : toute ta progression, tes statistiques et tes préférences seront supprimées.",confirmLabel:"Supprimer mon compte",fields:[{name:"password",label:"Mot de passe",type:"password"}],onConfirm:async({password:e})=>{await u.deleteMe({password:e,confirm:!0}),window.location.href="/"}})}))}const ge=[{value:"purple",label:"Nova Purple"},{value:"blue",label:"Bleu"},{value:"green",label:"Vert"},{value:"red",label:"Rose"},{value:"orange",label:"Orange"}];function be(){const e=q.appearance;return`
    <h2>${s("palette")} Apparence</h2>
    <p class="settings-panel-desc">Personnalise l'apparence de NovaMath — tout s'applique immédiatement.</p>

    <div class="settings-section">
      <div class="settings-section-title">Thème</div>
      ${S("theme",[{value:"dark",label:"Mode sombre"},{value:"light",label:"Mode clair"}],se())}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Couleur principale</div>
      <div class="color-swatch-group">
        ${ge.map(t=>`<button type="button" class="color-swatch swatch-${t.value}${e.accent===t.value?" active":""}" data-accent="${t.value}" title="${t.label}" aria-label="${t.label}"></button>`).join("")}
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Taille du texte</div>
      ${S("fontSize",[{value:"small",label:"Petit"},{value:"normal",label:"Normal"},{value:"large",label:"Grand"}],e.fontSize)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Coins des cartes</div>
      ${S("radius",[{value:"normal",label:"Normaux"},{value:"rounded",label:"Très arrondis"}],e.radius)}
    </div>

    <div class="settings-section">
      ${h("Animations","Transitions et animations dans toute l'interface.",f("toggle-animations",e.animations))}
      ${h("Effet de transparence","Surfaces vitrées (cartes, fenêtres) légèrement transparentes.",f("toggle-transparency",e.transparency))}
    </div>
  `}function he(){x(g,"theme",e=>r("appearance","theme",e)),x(g,"fontSize",e=>r("appearance","fontSize",e)),x(g,"radius",e=>r("appearance","radius",e)),g.querySelectorAll(".color-swatch").forEach(e=>{e.addEventListener("click",()=>{g.querySelectorAll(".color-swatch").forEach(t=>t.classList.remove("active")),e.classList.add("active"),r("appearance","accent",e.dataset.accent)})}),a("toggle-animations").addEventListener("change",e=>r("appearance","animations",e.target.checked)),a("toggle-transparency").addEventListener("change",e=>r("appearance","transparency",e.target.checked))}function fe(){const e=q.training;return`
    <h2>${s("sliders")} Entraînement</h2>
    <p class="settings-panel-desc">Ajuste le déroulement de tes séries d'exercices.</p>

    <div class="settings-section">
      <div class="settings-section-title">Nombre de questions par série</div>
      ${S("questionsPerSeries",[5,10,15,20].map(t=>({value:t,label:String(t)})),e.questionsPerSeries)}
    </div>

    <div class="settings-section">
      ${h("Chronomètre","Limite de temps par question en mode Défi chronométré.",f("toggle-chrono",e.chrono))}
      ${h("Confirmation avant de quitter une série","Une fenêtre te demande confirmation si tu quittes en cours de série.",f("toggle-confirm-leave",e.confirmBeforeLeave))}
      ${h("Reprendre automatiquement une série interrompue","Sinon, NovaMath te demande avant de reprendre.",f("toggle-auto-resume",e.autoResume))}
      ${h("Afficher automatiquement la correction","La méthode s'affiche juste après chaque réponse, sans clic.",f("toggle-auto-correction",e.autoShowCorrection))}
      ${h("Effets sonores","Petits sons de confirmation en cas de bonne/mauvaise réponse.",f("toggle-sound",e.soundEffects))}
    </div>
  `}function ye(){x(g,"questionsPerSeries",e=>r("training","questionsPerSeries",Number(e))),a("toggle-chrono").addEventListener("change",e=>r("training","chrono",e.target.checked)),a("toggle-confirm-leave").addEventListener("change",e=>r("training","confirmBeforeLeave",e.target.checked)),a("toggle-auto-resume").addEventListener("change",e=>r("training","autoResume",e.target.checked)),a("toggle-auto-correction").addEventListener("change",e=>r("training","autoShowCorrection",e.target.checked)),a("toggle-sound").addEventListener("change",e=>r("training","soundEffects",e.target.checked))}function $e(){const e=q.learning;return`
    <h2>${s("target")} Apprentissage</h2>
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
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Accuracy cible</span><span class="desc">Sur 20, comme au dashboard (ex. 18/20)</span></div>
        <div class="setting-row-control"><input type="number" min="0" max="20" step="0.5" id="input-target-accuracy" value="${e.targetAccuracyOn20}" style="width:80px;" class="learning-input"></div>
      </div>
    </div>

    <div class="settings-section">
      ${h("Prioriser les notions faibles","Les exercices proposés favorisent tes notions les moins maîtrisées.",f("toggle-prioritize-weak",e.prioritizeWeakNotions))}
      ${h("Prioriser les chapitres non maîtrisés","",f("toggle-prioritize-chapters",e.prioritizeUnmasteredChapters))}
      ${h("Révision espacée","Refait réapparaître les exercices déjà vus au bon moment pour mémoriser durablement.",f("toggle-spaced",e.spacedRepetition))}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Afficher des indices pendant les exercices</div>
      ${S("hints",[{value:"jamais",label:"Jamais"},{value:"parfois",label:"Parfois"},{value:"toujours",label:"Toujours"}],e.hints)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Afficher la correction</div>
      ${S("correctionDisplay",[{value:"fin",label:"Uniquement à la fin"},{value:"chaque_question",label:"Après chaque question"}],e.correctionDisplay)}
    </div>
  `}function Ee(){a("input-daily-exercises").addEventListener("change",e=>r("learning","dailyGoalExercises",Math.max(1,Number(e.target.value)||1))),a("input-daily-time").addEventListener("change",e=>r("learning","dailyGoalTimeMin",Math.max(1,Number(e.target.value)||1))),a("input-target-accuracy").addEventListener("change",e=>r("learning","targetAccuracyOn20",Math.min(20,Math.max(0,Number(e.target.value)||0)))),a("toggle-prioritize-weak").addEventListener("change",e=>r("learning","prioritizeWeakNotions",e.target.checked)),a("toggle-prioritize-chapters").addEventListener("change",e=>r("learning","prioritizeUnmasteredChapters",e.target.checked)),a("toggle-spaced").addEventListener("change",e=>r("learning","spacedRepetition",e.target.checked)),x(g,"hints",e=>r("learning","hints",e)),x(g,"correctionDisplay",e=>r("learning","correctionDisplay",e))}function we(){if(o.is_guest)return`<h2>${s("database")} Données</h2>${U("la gestion des données")}`;if(M===null)return`
      <h2>${s("database")} Données</h2>
      <p class="settings-panel-desc">Ta progression, en chiffres.</p>
      <div class="data-stats-grid">
        ${Array.from({length:5}).map(()=>'<div class="skeleton" style="height:76px; border-radius:var(--radius-sm);"></div>').join("")}
      </div>`;const e=M;return`
    <h2>${s("database")} Données</h2>
    <p class="settings-panel-desc">Ta progression, en chiffres.</p>

    <div class="data-stats-grid">
      <div class="data-stat-card"><div class="value">${e.totalExercises??"—"}</div><div class="label">Exercices réalisés</div></div>
      <div class="data-stat-card"><div class="value">${e.accuracy??0}%</div><div class="label">Accuracy</div></div>
      <div class="data-stat-card"><div class="value">${de(e.totalTimeS)}</div><div class="label">Temps d'entraînement</div></div>
      <div class="data-stat-card"><div class="value">${e.seriesCount??0}</div><div class="label">Séries</div></div>
      <div class="data-stat-card"><div class="value" style="font-size:1rem;">${_(e.memberSince)}</div><div class="label">Première connexion</div></div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Exporter</div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-export-pdf">${s("fileText")} Exporter mon rapport (PDF)</button>
        <a class="btn btn-secondary" id="btn-privacy-export" href="/api/data/export">${s("fileText")} Télécharger toutes mes données (RGPD)</a>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Confidentialité &amp; RGPD</div>
      ${E===null?"":`
        ${h("Cookies statistiques","Mesure d'audience anonyme pour améliorer NovaMath.",f("toggle-cookie-statistics",E.statistics))}
        ${h("Cookies marketing","Personnalisation des communications NovaMath.",f("toggle-cookie-marketing",E.marketing))}
      `}
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-consent-history">${s("fileText")} Historique de mes consentements</button>
      </div>
      ${D===null?"":`
        <ul class="consent-history-list">
          ${D.length===0?"<li>Aucun consentement enregistré.</li>":D.map(t=>`
            <li><strong>${t.consent_type}</strong> — ${t.decision} (${_(t.created_at)}${t.policy_version?`, version ${t.policy_version}`:""})</li>
          `).join("")}
        </ul>
      `}
    </div>

    <div class="settings-section danger-zone">
      <div class="settings-section-title">Zone sensible</div>
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-reset-stats">Réinitialiser les statistiques</button>
        <button class="btn btn-danger-outline" id="btn-reset-progress">Réinitialiser entièrement ma progression</button>
      </div>
    </div>
  `}function xe(){if(o.is_guest||M===null)return;a("btn-export-pdf").addEventListener("click",async()=>{const t=a("btn-export-pdf");t.disabled=!0,t.textContent="Génération du PDF…";try{const{exportProgressPdf:n}=await ee(async()=>{const{exportProgressPdf:i}=await import("./pdfExport.D1fB8DmB.js");return{exportProgressPdf:i}},__vite__mapDeps([0,1,2,3,4]));await n(),v("Rapport PDF téléchargé")}catch{v("Échec de l'export PDF.",!0)}finally{t.disabled=!1,t.innerHTML=`${s("fileText")} Exporter mon rapport (PDF)`}});const e=t=>C({title:t,text:"Cette action est irréversible : XP, historique, séries et badges seront remis à zéro.",confirmLabel:"Réinitialiser",onConfirm:async()=>{await u.resetProgress(),M=await u.getDataSummary().catch(()=>M),m(),v("Progression réinitialisée")}});a("btn-reset-stats").addEventListener("click",()=>e("Réinitialiser les statistiques")),a("btn-reset-progress").addEventListener("click",()=>e("Réinitialiser entièrement ma progression")),E!==null&&(a("toggle-cookie-statistics").addEventListener("change",t=>{E={...E,statistics:t.target.checked},u.setCookieConsent(E.statistics,E.marketing).catch(()=>{})}),a("toggle-cookie-marketing").addEventListener("change",t=>{E={...E,marketing:t.target.checked},u.setCookieConsent(E.statistics,E.marketing).catch(()=>{})})),a("btn-consent-history").addEventListener("click",async()=>{D=await u.getConsentHistory().then(t=>t.consent_history).catch(()=>[]),m()})}const Le=[{value:"fake",label:"Aucun (moteur NovaMath, par défaut)"},{value:"anthropic",label:"Claude (Anthropic)"},{value:"ollama",label:"Ollama (local)"},{value:"openai",label:"OpenAI (bientôt disponible)",disabled:!0},{value:"gemini",label:"Gemini (bientôt disponible)",disabled:!0}],Ce={fake:[{value:"moteur-novamath",label:"Moteur NovaMath (sans IA)"}],ollama:[{value:"mistral",label:"Mistral (par défaut)"}],anthropic:[{value:"claude-sonnet-5",label:"Claude Sonnet 5 (équilibré)"},{value:"claude-opus-4-8",label:"Claude Opus 4.8 (le plus capable)"},{value:"claude-haiku-4-5-20251001",label:"Claude Haiku 4.5 (le plus rapide)"}]};let j=null;function ne(){u.chatbotModels().then(e=>{j=e,k==="chatbot"&&m()}).catch(()=>{})}function ae(e){if(j&&j.provider===e){const t=Object.entries(j.models||{});if(t.length)return t.map(([n,i])=>({value:n,label:i}))}return Ce[e]||[]}function ke(){const e=q.chatbot||{},t=e.provider||"fake",n=ae(t);return`
    <h2>${s("messageSquare")} Chatbot</h2>
    <p class="settings-panel-desc">Personnalise l'assistant pédagogique NovaMath — tout s'applique dès le prochain message.</p>

    <div class="settings-section">
      <div class="settings-section-title">Fournisseur IA</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Par défaut, le chatbot répond avec le moteur interne NovaMath (règles, calcul, cours) — aucune donnée n'est envoyée à une IA. Tu peux activer Claude (Anthropic) ou Ollama (local) pour des explications plus poussées ; architecture prête pour en accueillir d'autres (OpenAI, Gemini…) sans changement du reste du site.</p>
      <div class="choice-group" data-group="chatbotProvider">
        ${Le.map(i=>`<button type="button" class="choice-pill${i.value===t?" active":""}" data-value="${i.value}" ${i.disabled?"disabled":""}>${i.label}</button>`).join("")}
      </div>
      <div class="settings-section-title" style="margin-top:18px;">Modèle</div>
      <div class="choice-group" data-group="chatbotModel">
        ${n.map(i=>`<button type="button" class="choice-pill${i.value===e.model?" active":""}" data-value="${i.value}">${i.label}</button>`).join("")}
      </div>
      ${t==="ollama"?`<p class="settings-panel-desc" style="margin-top:8px;">Modèles détectés automatiquement dans Ollama (<code>ollama list</code>). Installe-en d'autres avec <code>ollama pull &lt;modèle&gt;</code>, puis rouvre ce panneau.</p>`:""}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Créativité</div>
      <div class="setting-row">
        <div class="setting-row-text"><span class="label">Température (${e.temperature??.6})</span><span class="desc">Plus basse = réponses plus factuelles, plus haute = plus créatives.</span></div>
        <div class="setting-row-control"><input type="range" min="0" max="1" step="0.1" id="range-chatbot-temperature" value="${e.temperature??.6}"></div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Longueur des réponses</div>
      ${S("chatbotResponseLength",[{value:"court",label:"Court"},{value:"normal",label:"Normal"},{value:"detaille",label:"Détaillé"}],e.responseLength)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Niveau d'explication</div>
      ${S("chatbotExplanationLevel",[{value:"auto",label:"Automatique"},{value:"college",label:"Collège"},{value:"lycee",label:"Lycée"},{value:"expert",label:"Expert"}],e.explanationLevel)}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Mode</div>
      <p class="settings-panel-desc" style="margin-bottom:10px;">Change la façon dont le chatbot construit ses réponses.</p>
      ${S("chatbotMode",[{value:"professeur",label:"Professeur"},{value:"rapide",label:"Rapide"},{value:"pas_a_pas",label:"Pas-à-pas"},{value:"visuel",label:"Visuel"},{value:"examen",label:"Examen"}],e.mode)}
    </div>

    <div class="settings-section">
      ${h("Streaming","Affiche la réponse au fur et à mesure qu'elle est générée.",f("toggle-chatbot-streaming",e.streaming))}
      ${h("Historique","Le chatbot garde le fil de la conversation en cours.",f("toggle-chatbot-history",e.historyEnabled))}
      ${h("Mémoire","Le chatbot tient compte de ta progression NovaMath (niveau, notions faibles, chapitres en cours).",f("toggle-chatbot-memory",e.memoryEnabled))}
    </div>
  `}function qe(){x(g,"chatbotProvider",e=>{var t;r("chatbot","provider",e),r("chatbot","model",((t=ae(e)[0])==null?void 0:t.value)||""),ne(),m(),typeof window.checkChatbotProviderHealth=="function"&&window.checkChatbotProviderHealth(e)}),x(g,"chatbotModel",e=>r("chatbot","model",e)),a("range-chatbot-temperature").addEventListener("input",e=>r("chatbot","temperature",Number(e.target.value))),a("range-chatbot-temperature").addEventListener("change",()=>m()),x(g,"chatbotResponseLength",e=>r("chatbot","responseLength",e)),x(g,"chatbotExplanationLevel",e=>r("chatbot","explanationLevel",e)),x(g,"chatbotMode",e=>r("chatbot","mode",e)),a("toggle-chatbot-streaming").addEventListener("change",e=>r("chatbot","streaming",e.target.checked)),a("toggle-chatbot-history").addEventListener("change",e=>r("chatbot","historyEnabled",e.target.checked)),a("toggle-chatbot-memory").addEventListener("change",e=>r("chatbot","memoryEnabled",e.target.checked))}function Pe(e){return/mobile/i.test(e)?"Mobile":/tablet|ipad/i.test(e)?"Tablette":"Ordinateur"}function Se(){return R===null?'<div class="skeleton" style="height:52px; margin-bottom:8px; border-radius:var(--radius-sm);"></div><div class="skeleton" style="height:52px; border-radius:var(--radius-sm);"></div>':R.length?R.map(e=>`
    <div class="device-item">
      <span class="device-icon">${s("monitor")}</span>
      <div class="device-item-text">
        <div class="ua">${Pe(e.user_agent)}${e.current?" · Cet appareil":""}</div>
        <div class="meta">Connecté depuis le ${_(e.created_at)}</div>
      </div>
    </div>
  `).join(""):'<p class="settings-empty">Aucun appareil actif.</p>'}function Ae(){return o.is_guest?`<h2>${s("lock")} Confidentialité & Sécurité</h2>${U("la gestion de la sécurité")}`:`
    <h2>${s("lock")} Confidentialité & Sécurité</h2>
    <p class="settings-panel-desc">Garde le contrôle de l'accès à ton compte.</p>

    <div class="settings-section">
      ${h("Authentification à deux facteurs",o.two_factor_enabled?"Activée — un code à usage unique est demandé à chaque connexion.":"Protège ton compte avec un code généré par Google Authenticator, Microsoft Authenticator, Authy, 1Password ou Bitwarden.",o.two_factor_enabled?'<button type="button" class="btn btn-danger-outline btn-sm" id="btn-2fa-disable">Désactiver</button>':'<button type="button" class="btn btn-primary btn-sm" id="btn-2fa-enable">Activer</button>')}
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Appareils connectés</div>
      <div class="device-list">
        ${Se()}
      </div>
      <div class="settings-actions-grid">
        <button class="btn btn-secondary" id="btn-logout-others">Déconnecter tous les autres appareils</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Dernière connexion</div>
      <div class="account-info-grid">
        <div class="account-info-item"><div class="label">Date</div><div class="value">${_(o.last_login_at)}</div></div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-actions-grid">
        <button class="btn btn-danger-outline" id="btn-delete-account-sec">Supprimer définitivement mon compte</button>
      </div>
    </div>
  `}async function Me(){let e;try{e=await u.setup2FA()}catch(d){v(d.message||"Impossible de démarrer la configuration.",!0);return}const t=document.createElement("div");t.innerHTML=`
    <p class="settings-panel-desc">Scanne ce QR code avec ton application d'authentification (Google Authenticator, Microsoft Authenticator, Authy, 1Password, Bitwarden...).</p>
    <div class="twofa-qr-wrap"><img src="${e.qr_code}" alt="QR code d'activation de la double authentification" width="200" height="200"></div>
    <div class="form-field">
      <label for="twofa-secret-text">Impossible de scanner ? Saisis cette clé manuellement</label>
      <div class="twofa-secret-row">
        <code id="twofa-secret-text">${e.secret}</code>
        <button type="button" class="btn btn-ghost btn-sm" id="btn-2fa-copy-secret" aria-label="Copier la clé">${s("copy")}</button>
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
  `;const n=I({title:"Activer la double authentification",bodyEl:t,size:"sm"}),i=t.querySelector("#twofa-setup-code"),c=t.querySelector("#twofa-setup-error");t.querySelector("#btn-2fa-copy-secret").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(e.secret),v("Clé copiée")}catch{v("Copie impossible sur ce navigateur.",!0)}}),t.querySelector('[data-action="cancel"]').addEventListener("click",()=>n.close());async function p(){c.hidden=!0;const d=i.value.trim();if(!/^\d{6}$/.test(d)){c.textContent="Saisis les 6 chiffres affichés par ton application.",c.hidden=!1;return}const l=t.querySelector('[data-action="confirm"]');l.disabled=!0;try{const{recovery_codes:y}=await u.enable2FA(d);o.two_factor_enabled=!0,n.close(),m(),v("Authentification à deux facteurs activée"),Re(y)}catch(y){c.textContent=y.message||"Code invalide.",c.hidden=!1}finally{l.disabled=!1}}t.querySelector('[data-action="confirm"]').addEventListener("click",p),i.addEventListener("keydown",d=>{d.key==="Enter"&&(d.preventDefault(),p())}),requestAnimationFrame(()=>i.focus())}function Re(e){const t=document.createElement("div");t.innerHTML=`
    <p class="settings-panel-desc">Conserve ces codes de récupération en lieu sûr : chacun permet de te connecter <strong>une seule fois</strong> si tu perds l'accès à ton application d'authentification. Ils ne seront plus jamais affichés.</p>
    <ul class="twofa-recovery-list">${e.map(i=>`<li><code>${i}</code></li>`).join("")}</ul>
    <div class="verdict-row">
      <button type="button" class="btn btn-secondary" id="btn-2fa-copy-codes">${s("copy")} Copier</button>
      <button type="button" class="btn btn-primary" id="btn-2fa-download-codes">${s("download")} Télécharger</button>
    </div>
  `;const n=I({title:"Codes de récupération",bodyEl:t,size:"sm"});return t.querySelector("#btn-2fa-copy-codes").addEventListener("click",async()=>{try{await navigator.clipboard.writeText(e.join(`
`)),v("Codes copiés")}catch{v("Copie impossible sur ce navigateur.",!0)}}),t.querySelector("#btn-2fa-download-codes").addEventListener("click",()=>{const i=new Blob([e.join(`
`)+`
`],{type:"text/plain"}),c=URL.createObjectURL(i),p=document.createElement("a");p.href=c,p.download="novamath-recovery-codes.txt",document.body.appendChild(p),p.click(),p.remove(),URL.revokeObjectURL(c)}),n}function _e(){var e,t;o.is_guest||((e=a("btn-2fa-enable"))==null||e.addEventListener("click",()=>Me()),(t=a("btn-2fa-disable"))==null||t.addEventListener("click",()=>{C({title:"Désactiver la double authentification",text:"Ton compte ne sera plus protégé par un code à usage unique. Confirme avec ton mot de passe et un code de ton application d'authentification.",confirmLabel:"Désactiver",fields:[{name:"password",label:"Mot de passe actuel",type:"password"},{name:"code",label:"Code à 6 chiffres",placeholder:"123456"}],onConfirm:async({password:n,code:i})=>{await u.disable2FA(n,i),o.two_factor_enabled=!1,m(),v("Authentification à deux facteurs désactivée")}})}),a("btn-logout-others").addEventListener("click",()=>{C({title:"Déconnecter tous les autres appareils",text:"Toutes les sessions actives, sauf celle-ci, seront immédiatement fermées.",confirmLabel:"Déconnecter",onConfirm:async()=>{await u.logoutOtherSessions(),R=await u.getSessions().then(n=>n.sessions).catch(()=>R),m(),v("Autres appareils déconnectés")}})}),a("btn-delete-account-sec").addEventListener("click",()=>{C({title:"Supprimer définitivement le compte",text:"Cette action est irréversible.",confirmLabel:"Supprimer mon compte",fields:[{name:"password",label:"Mot de passe",type:"password"}],onConfirm:async({password:n})=>{await u.deleteMe({password:n,confirm:!0}),window.location.href="/"}})}))}const Ne=[{code:"fr",name:"Français",native:"Français"},{code:"en",name:"English",native:"English"}],Te=[{name:"العربية",native:"Arabe"},{name:"Español",native:"Espagnol"},{name:"Deutsch",native:"Allemand"}];function De(){return`
    <h2>${s("globe")} Langue</h2>
    <p class="settings-panel-desc">Choisis la langue de NovaMath.</p>
    <div class="language-grid">
      ${Ne.map(e=>`
        <button type="button" class="language-card${q.language===e.code?" active":""}" data-lang="${e.code}">
          <div class="lang-name">${e.name}</div>
          <div class="lang-native">${e.native}</div>
        </button>
      `).join("")}
      ${Te.map(e=>`
        <button type="button" class="language-card is-disabled" disabled title="Bientôt disponible">
          <div class="lang-name">${e.name}</div>
          <div class="lang-native">${e.native} · Bientôt disponible</div>
        </button>
      `).join("")}
    </div>
    <p class="settings-panel-desc" style="margin-top:18px;">${q.language==="en"?"Exercise content stays in French regardless of the interface language — only the interface itself is translated.":"Le contenu des exercices reste en français quelle que soit la langue de l'interface — seule l'interface elle-même est traduite."}</p>
  `}function je(){g.querySelectorAll(".language-card").forEach(e=>{e.addEventListener("click",()=>{ce("language",e.dataset.lang),m()})})}const Fe={presentation:{title:"Présentation de NovaMath",body:`
      <p>NovaMath est une plateforme française d'entraînement aux mathématiques, conçue pour accompagner les élèves du secondaire dans la maîtrise progressive du programme, chapitre par chapitre et notion par notion.</p>
      <p>La plateforme s'appuie sur une base de plus de 2000 exercices répartis sur 12 chapitres et 51 notions, avec 5 niveaux de difficulté, pour proposer un entraînement réellement adapté au niveau de chaque élève plutôt qu'un contenu générique.</p>
      <p>Chaque série d'exercices est suivie d'une correction détaillée, d'indices contextuels et d'un suivi de progression (précision, temps, régularité) afin de transformer l'entraînement en une boucle de progrès mesurable.</p>`},mission:{title:"Notre mission",body:`
      <p>Rendre l'entraînement aux mathématiques aussi efficace que possible, en combinant trois principes : <strong>la répétition ciblée</strong> (travailler en priorité ce qui n'est pas encore maîtrisé), <strong>la mesure honnête</strong> (des statistiques de progression fidèles, jamais gonflées) et <strong>l'autonomie</strong> (un élève doit pouvoir comprendre pourquoi il se trompe, pas seulement le savoir).</p>
      <p>NovaMath n'a pas vocation à remplacer un enseignant : c'est un outil d'entraînement complémentaire, pensé pour le travail personnel entre les cours.</p>`},fonctionnement:{title:"Comment fonctionne NovaMath",body:`
      <p><strong>1. Évaluation initiale.</strong> Un court test de positionnement estime ton niveau de départ.</p>
      <p><strong>2. Entraînement ciblé.</strong> Depuis Exercices ou Entraînement, tu lances des séries d'exercices dont le nombre, le chronomètre et le comportement suivent tes préférences définies dans Paramètres → Entraînement — quel que soit l'endroit d'où tu les lances.</p>
      <p><strong>3. Correction et indices.</strong> Chaque exercice propose un indice, une méthode détaillée et une solution, pour comprendre plutôt que deviner.</p>
      <p><strong>4. Suivi de progression.</strong> Le Dashboard centralise ton niveau, ton XP, ta précision, ton objectif quotidien et ton historique récent.</p>`},faq:{title:"FAQ — Questions fréquentes",body:`
      <p><strong>Le contenu des exercices est-il disponible en anglais ?</strong><br>Non : l'interface (menus, boutons, paramètres) est traduite en anglais, mais les énoncés d'exercices restent en français.</p>
      <p><strong>Pourquoi mes préférences ne sont-elles pas sauvegardées en mode invité ?</strong><br>Un compte invité est temporaire par conception : ses données sont automatiquement supprimées à la fin de la session. Crée un compte pour conserver ta progression durablement.</p>
      <p><strong>Comment changer le nombre d'exercices par série ?</strong><br>Paramètres → Entraînement → « Nombre de questions par série ». Le changement s'applique immédiatement à toutes les prochaines séries, depuis n'importe quelle page.</p>
      <p><strong>Le chronomètre reste actif alors que je l'ai désactivé, que faire ?</strong><br>Ce comportement a été corrigé : la désactivation est désormais appliquée en direct, y compris pendant une série déjà en cours d'affichage.</p>
      <p><strong>Comment supprimer mon compte ?</strong><br>Paramètres → Compte → Zone sensible → « Supprimer définitivement le compte ». Cette action est irréversible.</p>`},guide:{title:"Guide utilisateur",body:`
      <p><strong>Démarrer une série</strong> — depuis Entraînement, choisis un mode (Révisions, Objectif du jour, Examen blanc, Défi chronométré, Erreurs précédentes) puis lance-la. Depuis Exercices, ouvre un chapitre, sélectionne une ou plusieurs notions puis clique sur « Commencer la série ».</p>
      <p><strong>Reprendre une série interrompue</strong> — le Dashboard affiche une carte « Continuer » tant qu'une série n'est pas terminée.</p>
      <p><strong>Personnaliser l'apparence</strong> — Paramètres → Apparence permet de changer le thème clair/sombre, la couleur d'accent, la taille du texte, la transparence et les animations ; chaque changement s'applique instantanément à tout le site.</p>
      <p><strong>Suivre ses objectifs</strong> — Paramètres → Apprentissage définit l'objectif quotidien (nombre d'exercices, temps), visible en temps réel sur le Dashboard.</p>
      <p><strong>Exporter ses données</strong> — Paramètres → Données → « Exporter mon rapport (PDF) » génère un rapport complet et imprimable de ta progression.</p>`},contact:{title:"Nous contacter",body:`
      <p>Le moyen le plus rapide de nous joindre est la section Avis de la page d'accueil, consultée en priorité par l'équipe.</p>
      <p>Pour un bug ou une suggestion, décris précisément le contexte (page, action effectuée, comportement attendu) : cela accélère beaucoup la résolution.</p>`},privacy:{title:"Politique de confidentialité",body:`
      <p>NovaMath collecte uniquement les données nécessaires au fonctionnement du service : identifiant de compte, pseudo, adresse email, préférences, et historique d'entraînement (exercices réalisés, résultats, durée).</p>
      <p>Ces données ne sont jamais vendues ni partagées avec des tiers à des fins commerciales. Elles servent exclusivement à faire fonctionner le suivi de progression et la personnalisation de l'entraînement.</p>
      <p>Un compte invité est entièrement temporaire : ses données sont supprimées automatiquement à la fin de la session, sans action nécessaire de ta part.</p>
      <p>Tu peux à tout moment consulter, exporter (Paramètres → Données) ou supprimer définitivement (Paramètres → Compte) tes données.</p>`},terms:{title:"Conditions générales d'utilisation",body:`
      <p>L'utilisation de NovaMath implique l'acceptation des présentes conditions. Le service est fourni « en l'état », à des fins d'entraînement pédagogique, sans garantie d'exhaustivité du programme scolaire.</p>
      <p>Chaque utilisateur est responsable de la confidentialité de son mot de passe. Toute utilisation frauduleuse ou automatisée (scripts, bots) du service est interdite et peut entraîner la suspension du compte.</p>
      <p>NovaMath se réserve le droit de faire évoluer les fonctionnalités du service ; les préférences et la progression des utilisateurs sont préservées lors de ces évolutions dans la mesure du possible.</p>`},legal:{title:"Mentions légales",body:`
      <p>NovaMath est un service édité à des fins pédagogiques. Les contenus mathématiques (énoncés, corrections) sont produits ou vérifiés par l'équipe éditoriale de NovaMath.</p>
      <p>Le nom « NovaMath » et le logo associé sont la propriété de l'éditeur du service. Toute reproduction non autorisée est interdite.</p>`},cookies:{title:"Gestion des cookies",body:`
      <p>NovaMath utilise un cookie de session strictement nécessaire à l'authentification (maintien de la connexion) ainsi qu'un cookie technique anti-CSRF, indispensables au fonctionnement du service — ils ne peuvent pas être désactivés sans empêcher la connexion.</p>
      <p>Aucun cookie publicitaire ou de traçage tiers n'est utilisé. Les préférences d'interface (thème, couleur, langue…) sont stockées localement dans ton navigateur (localStorage), jamais partagées.</p>`},roadmap:{title:"Roadmap",body:`
      <p><strong>Récemment livré :</strong> centre de paramètres unifié en popup, thème et couleur d'accent propagés à tout le site, export PDF du rapport de progression, interface bilingue français/anglais.</p>
      <p><strong>À venir :</strong> traduction complète de la base d'exercices, authentification à deux facteurs, rapport enseignant, certificats de progression.</p>
      <p>Cette roadmap est indicative et peut évoluer selon les retours des utilisateurs (section Avis).</p>`},credits:{title:"Crédits, technologies & licences",body:`
      <p><strong>Technologies utilisées :</strong> Flask (backend Python), JavaScript vanilla en modules ES (frontend, sans framework), SQLite pour le stockage.</p>
      <p><strong>Bibliothèques tierces :</strong></p>
      <p>— <strong>KaTeX</strong> (rendu des formules mathématiques) — licence MIT.<br>— <strong>jsPDF</strong> (génération de l'export PDF) — licence MIT.</p>
      <p>NovaMath n'utilise aucune dépendance propriétaire : l'ensemble des bibliothèques tierces est open source.</p>`},security:{title:"Sécurité",body:`
      <p>Les mots de passe sont stockés sous forme hachée (Argon2), jamais en clair. Les sessions sont protégées par cookies sécurisés et une protection CSRF par double-soumission de jeton.</p>
      <p>Aucune donnée de paiement n'est collectée par NovaMath.</p>`}};function K(e){const t=Fe[e];t&&ee(async()=>{const{openPopup:n}=await import("./i18n.ja2ECFcd.js").then(i=>i.C);return{openPopup:n}},__vite__mapDeps([3,1,2,4])).then(({openPopup:n})=>{n({title:t.title,bodyHtml:`<div class="help-page-content">${t.body}</div>`,size:"md"})})}function Oe(){return`
    <h2>${s("helpCircle")} Aide & À propos</h2>
    <p class="settings-panel-desc">Tout savoir sur NovaMath, comment l'utiliser, et comment nous contacter.</p>

    <div class="settings-section">
      <div class="settings-section-title">NovaMath</div>
      <div class="help-links">
        <button class="help-link" data-help="presentation">Présentation NovaMath ${s("arrowRight")}</button>
        <button class="help-link" data-help="mission">Notre mission ${s("arrowRight")}</button>
        <button class="help-link" data-help="fonctionnement">Comment ça fonctionne ${s("arrowRight")}</button>
        <button class="help-link" data-help="roadmap">Roadmap ${s("arrowRight")}</button>
        <button class="help-link" data-help="credits">Crédits & technologies ${s("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Aide</div>
      <div class="help-links">
        <button class="help-link" data-help="guide">Guide utilisateur ${s("arrowRight")}</button>
        <button class="help-link" data-help="faq">FAQ ${s("arrowRight")}</button>
        <button class="help-link" id="help-support-link">Support & nous contacter ${s("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-section-title">Légal</div>
      <div class="help-links">
        <button class="help-link" data-help="terms">Conditions générales d'utilisation ${s("arrowRight")}</button>
        <button class="help-link" data-help="privacy">Politique de confidentialité ${s("arrowRight")}</button>
        <button class="help-link" data-help="cookies">Gestion des cookies ${s("arrowRight")}</button>
        <button class="help-link" data-help="legal">Mentions légales ${s("arrowRight")}</button>
        <button class="help-link" data-help="security">Sécurité ${s("arrowRight")}</button>
      </div>
    </div>

    <div class="settings-section" style="margin-top:8px;">
      <div class="account-info-grid">
        <div class="account-info-item"><div class="label">Version actuelle</div><div class="value">NovaMath v${Z}</div></div>
      </div>
      <div class="settings-actions-grid" style="margin-top:14px;">
        <button class="btn btn-secondary" id="btn-check-updates">${s("refreshCcw")} Vérifier les mises à jour</button>
      </div>
    </div>
  `}function Ge(){g.querySelectorAll("[data-help]").forEach(e=>{e.addEventListener("click",()=>K(e.dataset.help))}),a("help-support-link").addEventListener("click",()=>K("contact")),a("btn-check-updates").addEventListener("click",()=>v(`Tu utilises déjà la dernière version (NovaMath v${Z}).`))}const W={account:[pe,ve],appearance:[be,he],training:[fe,ye],learning:[$e,Ee],data:[we,xe],chatbot:[ke,qe],security:[Ae,_e],language:[De,je],help:[Oe,Ge]};function m(){const[e,t]=W[k]||W.account;g.innerHTML=e(),t()}async function Ie(e){g=e.querySelector("#settings-panel"),F=e.querySelector("#settings-menu"),q=X();try{const{user:t}=await u.me();o=t}catch{window.location.href="/";return}H(),m(),o.is_guest||(u.getDataSummary().then(t=>{M=t,k==="data"&&m()}).catch(()=>{}),u.getSessions().then(t=>{R=t.sessions,k==="security"&&m()}).catch(()=>{}),u.getCookieConsent().then(t=>{E=t,k==="data"&&m()}).catch(()=>{})),ne()}ie(e=>{e.detail.category!=="language"&&e.detail.category!=="*"||!g||!F||(q=X(),H(),m())});const He=`
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
`;let T=null;function Ue(){if(T)return T;const e=document.createElement("div");e.className="settings-shell",e.innerHTML=He;const t=I({id:"settings-popup-overlay",title:L("settings.title"),bodyEl:e,size:"xl",onClose:()=>{T=null}});return T=t,Ie(e),t}function Ye(e){e&&e.addEventListener("click",()=>Ue())}export{Qe as P,Xe as a,Ye as b,Ze as f,We as n,Ke as p,Je as r};
