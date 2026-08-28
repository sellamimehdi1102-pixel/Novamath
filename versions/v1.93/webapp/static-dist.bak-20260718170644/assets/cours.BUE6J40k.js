import{a as y}from"./api.BAG-rd0x.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as T}from"./chapterTitleByNotions.CaHmVStm.js";/* empty css                 */import"./sidebar.BCM6rExI.js";import"./command-palette.BEhH-ESM.js";import{i as Q,b as Z,l as J}from"./i18n.p3FnEZbd.js";import{b as X}from"./settingsPopup.DNRCNxru.js";import{g as C,f as W,i as l,I as Y}from"./theme.CdfXyWq_.js";import{a as R}from"./mathrender.C9lrWfgK.js";import{f as q}from"./animations.C_a-7GOx.js";const k=28,x=260;function p(e,s,t){const[n,r,o,i]=e.viewBox,a=(x-2*k)/Math.max(o,i),d=k+(s-n)*a,u=x-k-(t-r)*a;return[d,u]}function $(e,s){if(typeof s=="string"){const t=(e.points||[]).find(n=>n.label===s);return t?[t.x,t.y]:[0,0]}return[s.x,s.y]}function K(e){const[s,t,n,r]=e.viewBox;let o="";for(let i=Math.ceil(s);i<=s+n;i++){const[a,d]=p(e,i,t),[u,g]=p(e,i,t+r);o+=`<line x1="${a}" y1="${d}" x2="${u}" y2="${g}" class="geom-grid-line"/>`}for(let i=Math.ceil(t);i<=t+r;i++){const[a,d]=p(e,s,i),[u,g]=p(e,s+n,i);o+=`<line x1="${a}" y1="${d}" x2="${u}" y2="${g}" class="geom-grid-line"/>`}return o}function ee(e){const[s,t,n,r]=e.viewBox;if(s>0||s+n<0||t>0||t+r<0)return"";const[o,i]=p(e,s,0),[a,d]=p(e,s+n,0),[u,g]=p(e,0,t),[f,w]=p(e,0,t+r);return`
    <line x1="${o}" y1="${i}" x2="${a}" y2="${d}" class="geom-axis"/>
    <line x1="${u}" y1="${g}" x2="${f}" y2="${w}" class="geom-axis"/>
  `}function te(e){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="geom-arrow-head"/>
  </marker>`}function se(e){const s=`geom-arrow-${Math.random().toString(36).slice(2,8)}`;let t="";return e.grid&&(t+=K(e)),e.axes&&(t+=ee(e)),(e.polygons||[]).forEach(n=>{const r=n.points.map(o=>p(e,...$(e,o)).join(",")).join(" ");t+=`<polygon points="${r}" class="geom-polygon"/>`}),(e.circles||[]).forEach(n=>{const[r,o]=p(e,...$(e,n.center)),i=(x-2*k)/Math.max(e.viewBox[2],e.viewBox[3]);t+=`<circle cx="${r}" cy="${o}" r="${n.radius*i}" class="geom-circle"/>`}),(e.segments||[]).forEach(n=>{const[r,o]=p(e,...$(e,n.from)),[i,a]=p(e,...$(e,n.to));t+=`<line x1="${r}" y1="${o}" x2="${i}" y2="${a}" class="geom-segment${n.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(n=>{const[r,o]=p(e,...$(e,n.from)),[i,a]=p(e,...$(e,n.to));if(t+=`<line x1="${r}" y1="${o}" x2="${i}" y2="${a}" class="geom-vector" marker-end="url(#${s})"/>`,n.label){const d=(r+i)/2+8,u=(o+a)/2-8;t+=`<text x="${d}" y="${u}" class="geom-label geom-label--vector">${n.label}</text>`}}),(e.points||[]).forEach(n=>{const[r,o]=p(e,n.x,n.y);t+=`<circle cx="${r}" cy="${o}" r="3.5" class="geom-point"/>`,n.label&&(t+=`<text x="${r+8}" y="${o-8}" class="geom-label">${n.label}</text>`)}),(e.angles||[]).forEach(n=>{const[r,o]=p(e,...$(e,n.vertex));t+=`<circle cx="${r}" cy="${o}" r="2.5" class="geom-point"/>`,n.label&&(t+=`<text x="${r+10}" y="${o+4}" class="geom-label">${n.label}</text>`)}),`
    <svg viewBox="0 0 ${x} ${x}" class="geom-figure" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>${te(s)}</defs>
      ${t}
    </svg>
  `}Q().then(()=>Z());X(document.getElementById("settings-btn"));const H=document.getElementById("cours-list-view"),v=document.getElementById("cours-reader-view"),A=document.getElementById("cours-grid"),ne=2;let D=!1;y.me().then(({user:e})=>{D=!!e.is_guest}).catch(()=>{});const M=new Set;let I=[],j={};const z=new Map;function oe(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function re(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",s=>{s.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(s=>{s.addEventListener("click",()=>{e.hidden=!0})})}function ie(){re(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function G(e){const s=j[e.id]||{},t=Object.values(s),n=t.filter(a=>a.status==="done").length,r=e.n_notions||0,o=r?Math.round(n/r*100):0,i=t.some(a=>a.status==="in_progress");return{doneCount:n,total:r,pct:o,anyInProgress:i}}function _(){A.innerHTML="",I.forEach(e=>{const s=G(e),t=document.createElement("article");t.className="chapter-card card card--interactive",t.dataset.id=e.id,t.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${oe()}</div>
      </div>
      <h3>${T(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${e.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${s.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${s.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${l("bookOpen")} ${e.n_notions} notion${e.n_notions>1?"s":""}</span>
        <span>${l("check")} ${s.doneCount}/${s.total} terminée${s.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${l("bookOpen")} ${s.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,t.querySelector(".cours-open-btn").addEventListener("click",()=>B(e.id)),A.appendChild(t)})}function ae(e){return e==="seconde"?"cours":`cours_${e}`}async function F(e){if(z.has(e))return z.get(e);const s=e.replace("Chapitre_",""),t=ae(C()),n=await fetch(`data/${t}/chapitre_${s}.json`);if(!n.ok)throw new Error("Contenu introuvable pour "+e);const r=await n.json();return z.set(e,r),r}function ce(){H.hidden=!1,v.hidden=!0,v.innerHTML=""}function le(){H.hidden=!0,v.hidden=!1}async function B(e){if(D&&!M.has(e)&&M.size>=ne){ie();return}M.add(e),v.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,le();const s=await F(e);V(e,s)}function de(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}function V(e,s){const t=j[e]||{},n=I.find(o=>o.id===e),r=n?G(n):null;v.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${l("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${T(s.title,s.notions.map(o=>o.title))||e.replace(/_/g," ")}</h1>
      ${r?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${r.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${r.doneCount}/${r.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${s.notions.map(o=>{var a,d;const i=((a=t[o.id])==null?void 0:a.status)||"todo";return`
        <div class="card cours-notion-card" data-notion="${o.id}">
          <div class="cours-notion-top">
            <h3>${o.title}</h3>
            ${de(i)}
          </div>
          <div class="cours-notion-meta">
            <span>${(o.exemples||[]).length} exemple${(o.exemples||[]).length>1?"s":""}</span>
            ${(d=t[o.id])!=null&&d.quizTotal?`<span>Quiz : ${t[o.id].quizScore}/${t[o.id].quizTotal}</span>`:""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${l("play")} ${i==="todo"?"Commencer":i==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,q(v),v.querySelector("#cours-back-to-grid").addEventListener("click",()=>{_(),ce()}),v.querySelectorAll(".cours-read-btn").forEach(o=>{o.addEventListener("click",i=>{const a=i.target.closest(".cours-notion-card").dataset.notion,d=s.notions.find(u=>u.id===a);P(e,s,d)})})}const O=["blue","purple","green","orange","pink"];function ue(e){return`<div class="cours-steps">${(e||[]).map((s,t)=>`
    <div class="cours-step cours-step--${s.couleur||O[t%O.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${l(s.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
  `).join("")}</div>`}function pe(e){const s=(e.calcul||[]).map((t,n,r)=>`
    <div class="cours-calc-row">
      <div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${n<r.length-1?`<div class="cours-calc-arrow">${Y.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${l("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      <div class="cours-calc-block">${s}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
    </div>
  `}function ve(e){e.querySelectorAll("[data-text]").forEach(s=>{R(s,decodeURIComponent(s.dataset.text)),s.removeAttribute("data-text")})}function me(e,s){const t=e.notions.findIndex(o=>o.id===s.id),n=t>0?e.notions[t-1]:null,r=t<e.notions.length-1?e.notions[t+1]:null;return!n&&!r?"":`
    <div class="cours-notion-nav">
      ${n?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${n.id}">
        ${l("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${n.title}</span></span>
      </button>`:"<span></span>"}
      ${r?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${r.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${r.title}</span></span>
        ${l("arrowRight")}
      </button>`:""}
    </div>
  `}function P(e,s,t){var o,i,a,d,u,g,f,w,U;function n(c){y.saveCourseProgress(e,t.id,c,C()).catch(()=>{})}v.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${l("arrowLeft")} ${T(s.title,s.notions.map(c=>c.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${t.title}</h1>
    <p class="cours-intro-text">${t.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${l("target")}</div>
      <p>${t.objectif||""}</p>
    </div>

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${l("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${t.figure?`<div class="cours-figure-wrap">${se(t.figure)}${t.figure.alt?`<div class="cours-figure-caption">${t.figure.alt}</div>`:""}</div>`:""}

    ${(o=t.reglesImportantes)!=null&&o.length?`
    <div class="cours-section-label">${l("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(c=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(c)}"></div>`).join("")}
    </div>`:""}

    ${(a=(i=t.methode)==null?void 0:i.etapes)!=null&&a.length?`
    <div class="cours-section-label">${l("compass")} ${t.methode.titre||"Méthode"}</div>
    ${ue(t.methode.etapes)}`:""}

    ${(d=t.exemples)!=null&&d.length?`
    <div class="cours-section-label">${l("penSquare")} Exemples</div>
    ${t.exemples.map(pe).join("")}`:""}

    ${(u=t.erreursFrequentes)!=null&&u.length?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${l("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${l("lightbulb")} <span>Astuce</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(g=t.aRetenir)!=null&&g.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${l("star")} À retenir</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,5).map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(f=t.quizExerciseIds)!=null&&f.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${l("check")} J'ai terminé cette leçon</button>
    </div>

    ${me(s,t)}
  `,ve(v),q(v),v.querySelector("#cours-back-to-chapter").addEventListener("click",()=>V(e,s)),v.querySelectorAll(".cours-notion-nav-btn").forEach(c=>{c.addEventListener("click",()=>{const m=s.notions.find(h=>h.id===c.dataset.notion);m&&P(e,s,m)})}),n({status:"in_progress"}),(w=t.quizExerciseIds)!=null&&w.length?r(v.querySelector("#cours-quiz-zone")):(U=v.querySelector("#cours-mark-done-btn"))==null||U.addEventListener("click",()=>{n({status:"done"}),v.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${l("check")} Leçon terminée !</span>`});async function r(c){c.innerHTML='<div class="skeleton" style="height:140px;"></div>';let m;try{m=await Promise.all(t.quizExerciseIds.map(b=>y.exercise(b,C()).then(L=>L.exercise)))}catch{c.innerHTML="",n({status:"done"});return}let h=0,E=0;function S(){if(h>=m.length){c.innerHTML=`<div class="card cours-quiz-done">${l("check")} Mini-quiz terminé : <strong>${E}/${m.length}</strong> bonnes réponses.</div>`,q(c.querySelector(".cours-quiz-done")),n({status:"done",quizScore:E,quizTotal:m.length});return}const b=m[h],L=Math.round(h/m.length*100);c.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${l("lightbulb")} Mini-quiz — question ${h+1}/${m.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${L}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${l("check")} J'ai réussi</button>
          </div>
        </div>
      `,q(c.querySelector(".cours-quiz-card")),R(c.querySelector("#cours-quiz-enonce"),b.enonce),c.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const N=c.querySelector("#cours-quiz-answer");N.hidden=!1,R(N,`Réponse : ${b.answer}${b.hint?`
Indice : ${b.hint}`:""}`),c.querySelector("#cours-quiz-reveal").hidden=!0,c.querySelector("#cours-quiz-verdict").hidden=!1}),c.querySelector("#cours-quiz-fail").addEventListener("click",()=>{h+=1,S()}),c.querySelector("#cours-quiz-success").addEventListener("click",()=>{E+=1,h+=1,S()})}S()}}async function ge(e,s){await B(e);const t=await F(e),n=t.notions.find(r=>r.id===s);n&&P(e,t,n)}function he(){A.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${l("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function $e(){const e=C();let s=!0;try{const d=(await W()).find(u=>u.classLevel===e);s=d?d.hasCourses!==!1:!0}catch{s=!0}if(!s){he();return}const[t,n]=await Promise.all([y.chapters(e),y.getCourseProgress(e).catch(()=>({}))]);I=t.chapters_meta||[],j=n||{},_();const r=new URLSearchParams(window.location.search),o=r.get("chapter"),i=r.get("notion");o&&i?ge(o,i):o&&B(o)}$e();J(e=>{["appearance","*"].includes(e.detail.category)&&(H.hidden||_())});
