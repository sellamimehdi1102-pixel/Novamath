import{a as H}from"./api.DlOwEDsY.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as D}from"./chapterTitleByNotions.B33dvngo.js";/* empty css                 */import"./sidebar.CcaruqBd.js";import"./command-palette.BW-AozPS.js";import{i as ne,b as ie,l as re}from"./i18n.k284iSwh.js";import{b as ae}from"./settingsPopup.DCnnzMux.js";import{g as T,f as ce,i as $,I as le}from"./theme.3Ba6cpxV.js";import{a as P}from"./mathrender.C9lrWfgK.js";import{f as A}from"./animations.BG9-j6JA.js";const de=620,ue=460,me=34,pe=120,j=50,V=30,Z=30,z=50;function ge(e){const[t,s,r,i]=e.viewBox;let n=Math.min((de-j-V)/r,(ue-Z-z)/i);return n=Math.max(me,Math.min(pe,n)),{xmin:t,ymin:s,w:r,h:i,unit:n,width:r*n+j+V,height:i*n+Z+z}}function v(e,t,s){const r=j+(t-e.xmin)*e.unit,i=e.height-z-(s-e.ymin)*e.unit;return[r,i]}function S(e,t){if(typeof t=="string"){const s=(e.points||[]).find(r=>r.label===t);return s?[s.x,s.y]:[0,0]}return[t.x,t.y]}function $e(e){const{xmin:t,ymin:s,w:r,h:i}=e;let n="";for(let p=Math.ceil(t);p<=t+r;p++){const[o,l]=v(e,p,s),[c,a]=v(e,p,s+i);n+=`<line x1="${o}" y1="${l}" x2="${c}" y2="${a}" class="geom-grid-line"/>`}for(let p=Math.ceil(s);p<=s+i;p++){const[o,l]=v(e,t,p),[c,a]=v(e,t+r,p);n+=`<line x1="${o}" y1="${l}" x2="${c}" y2="${a}" class="geom-grid-line"/>`}return n}function xe(e){const{xmin:t,ymin:s,w:r,h:i}=e,n=r*.05,p=i*.05;let o="";for(let a=Math.ceil(t);a<=t+r;a++){if(a===0||a<t+n||a>t+r-n)continue;const[u,m]=v(e,a,0);o+=`<line x1="${u}" y1="${m-4}" x2="${u}" y2="${m+4}" class="geom-tick"/>`,o+=`<text x="${u}" y="${m+18}" class="geom-tick-label" text-anchor="middle">${a}</text>`}for(let a=Math.ceil(s);a<=s+i;a++){if(a===0||a<s+p||a>s+i-p)continue;const[u,m]=v(e,0,a);o+=`<line x1="${u-4}" y1="${m}" x2="${u+4}" y2="${m}" class="geom-tick"/>`,o+=`<text x="${u-9}" y="${m+4}" class="geom-tick-label" text-anchor="end">${a}</text>`}const[l,c]=v(e,0,0);return o+=`<text x="${l-9}" y="${c+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,o}function ve(e,t){const{xmin:s,ymin:r,w:i,h:n}=e;if(s>0||s+i<0||r>0||r+n<0)return"";const[p,o]=v(e,s,0),[l,c]=v(e,s+i,0),[a,u]=v(e,0,r),[m,g]=v(e,0,r+n);let b=`
    <line x1="${p}" y1="${o}" x2="${l}" y2="${c}" class="geom-axis" marker-end="url(#${t})"/>
    <line x1="${a}" y1="${u}" x2="${m}" y2="${g}" class="geom-axis" marker-end="url(#${t})"/>
    <text x="${l-6}" y="${c-8}" class="geom-axis-label">x</text>
    <text x="${m+10}" y="${g+4}" class="geom-axis-label">y</text>
  `;return b+=xe(e),b}function J(e,t){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${t}"/>
  </marker>`}function K(e){const t=Math.random().toString(36).slice(2,8),s=`geom-arrow-axis-${t}`,r=`geom-arrow-vector-${t}`,i=ge(e);let n="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(n+=$e(i)),e.axes&&(n+=ve(i,s)),(e.curves||[]).forEach(o=>{const l=o.points.map(([c,a])=>v(i,c,a).join(",")).join(" ");n+=`<polyline points="${l}" class="geom-curve${o.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(o=>{const l=o.points.map(c=>v(i,...S(e,c)).join(",")).join(" ");n+=`<polygon points="${l}" class="geom-polygon"/>`}),(e.circles||[]).forEach(o=>{const[l,c]=v(i,...S(e,o.center));n+=`<circle cx="${l}" cy="${c}" r="${o.radius*i.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(o=>{const[l,c]=v(i,...S(e,o.center)),a=o.radius*i.unit,u=o.startDeg*Math.PI/180,m=o.endDeg*Math.PI/180,g=l+a*Math.cos(u),b=c-a*Math.sin(u),y=l+a*Math.cos(m),C=c-a*Math.sin(m),k=Math.abs(o.endDeg-o.startDeg)>180?1:0;if(n+=`<path d="M ${l} ${c} L ${g} ${b} A ${a} ${a} 0 ${k} 1 ${y} ${C} Z" class="geom-angle-arc"/>`,o.label){const w=(o.startDeg+o.endDeg)/2*(Math.PI/180),M=l+(a+12)*Math.cos(w),d=c-(a+12)*Math.sin(w);n+=`<text x="${M}" y="${d}" class="geom-label">${o.label}</text>`}}),(e.segments||[]).forEach(o=>{const[l,c]=v(i,...S(e,o.from)),[a,u]=v(i,...S(e,o.to));n+=`<line x1="${l}" y1="${c}" x2="${a}" y2="${u}" class="geom-segment${o.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(o=>{const[l,c]=v(i,...S(e,o.from)),[a,u]=v(i,...S(e,o.to));if(n+=`<line x1="${l}" y1="${c}" x2="${a}" y2="${u}" class="geom-vector" marker-end="url(#${r})"/>`,o.label){const m=(l+a)/2+8,g=(c+u)/2-8;n+=`<text x="${m}" y="${g}" class="geom-label geom-label--vector">${o.label}</text>`}}),(e.points||[]).forEach(o=>{const[l,c]=v(i,o.x,o.y);n+=`<circle cx="${l}" cy="${c}" r="4.5" class="geom-point"/>`,o.label&&(n+=`<text x="${l+9}" y="${c-9}" class="geom-label">${o.label}</text>`),(o.showCoords||e.showCoords)&&(n+=`<text x="${l+9}" y="${c-9+15}" class="geom-label geom-coord-label">(${o.x} ; ${o.y})</text>`)}),(e.texts||[]).forEach(o=>{const[l,c]=v(i,o.x,o.y);n+=`<text x="${l}" y="${c}" class="geom-label">${o.label}</text>`}),(e.angles||[]).forEach(o=>{const[l,c]=v(i,...S(e,o.vertex));n+=`<circle cx="${l}" cy="${c}" r="2.5" class="geom-point"/>`,o.label&&(n+=`<text x="${l+10}" y="${c+4}" class="geom-label">${o.label}</text>`)}),`
    <svg viewBox="0 0 ${i.width} ${i.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${J(s,"geom-arrow-head geom-arrow-head--axis")}
        ${J(r,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${n}
    </svg>
  `}function he(e){const o=e.branches||[],l=o.length||1,c=320/l;let a="";return o.forEach((u,m)=>{const g=32+c*(m+.5),b=m<l/2;a+=`<line x1="48" y1="192" x2="264" y2="${g}" class="geom-tree-edge"/>`,a+=`<text x="${312/2}" y="${(192+g)/2-13}" class="geom-tree-proba">${u.proba||""}</text>`,a+=`<text x="254" y="${b?g-19:g+29}" class="geom-tree-label" text-anchor="end">${u.label}</text>`;const y=u.branches||[],C=y.length||1,k=54;y.forEach((w,M)=>{const d=g+(M-(C-1)/2)*k;a+=`<line x1="264" y1="${g}" x2="528" y2="${d}" class="geom-tree-edge"/>`,a+=`<text x="${792/2}" y="${(g+d)/2-13}" class="geom-tree-proba">${w.proba||""}</text>`,a+=`<text x="544" y="${d+6}" class="geom-tree-label">${w.label}</text>`})}),a+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',o.forEach((u,m)=>{const g=32+c*(m+.5);a+=`<circle cx="264" cy="${g}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${a}</svg>`}function be(e){const[o,l]=e.sets||["A","B"];let c=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${o}</text>
    <text x="336" y="147" class="geom-label">${l}</text>
  `;return e.overlapLabel&&(c+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${c}</svg>`}function ye(e){const n=e.labels||[],p=Math.max(n.length,1);let o="";return n.forEach((l,c)=>{const a=42+c*(160/Math.max(p-1,1));o+=`<circle cx="208" cy="224" r="${a}" class="geom-nested-circle"/>`,o+=`<text x="208" y="${224-a+24}" class="geom-label" text-anchor="middle">${l}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${o}</svg>`}function fe(e){const{min:r,max:i}=e,n=32,p=416,o=(p-n)/(i-r||1),l=u=>n+(u-r)*o,c=72;let a=`<line x1="${n}" y1="${c}" x2="${p}" y2="${c}" class="geom-axis"/>`;if(e.highlight){const{from:u,to:m}=e.highlight;a+=`<line x1="${l(u)}" y1="${c}" x2="${l(m)}" y2="${c}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(u=>{const m=l(u.value);a+=`<circle cx="${m}" cy="${c}" r="8" class="${u.filled===!1?"geom-point--open":"geom-point"}"/>`,a+=`<text x="${m}" y="${c+30}" class="geom-label" text-anchor="middle">${u.label??u.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${a}</svg>`}function we(e){const r=e.bars||[],i=e.maxValue||Math.max(...r.map(a=>a.value),1),n=240,p=32,o=384/Math.max(r.length,1),l=o*.6;let c=`<line x1="32" y1="${n}" x2="416" y2="${n}" class="geom-axis"/>`;return r.forEach((a,u)=>{const m=(n-p)*a.value/i,g=32+u*o+(o-l)/2;c+=`<rect x="${g}" y="${n-m}" width="${l}" height="${m}" class="geom-bar"/>`,c+=`<text x="${g+l/2}" y="${n+26}" class="geom-label" text-anchor="middle">${a.label}</text>`,c+=`<text x="${g+l/2}" y="${n-m-10}" class="geom-label" text-anchor="middle">${a.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${c}</svg>`}function qe(e){const p=e.slices||[],o=p.reduce((a,u)=>a+u.value,0)||1;let l=-90,c="";return p.forEach((a,u)=>{const m=a.value/o*360,g=l*Math.PI/180,b=(l+m)*Math.PI/180,y=176+112*Math.cos(g),C=160+112*Math.sin(g),k=176+112*Math.cos(b),w=160+112*Math.sin(b),M=m>180?1:0;c+=`<path d="M 176 160 L ${y} ${C} A 112 112 0 ${M} 1 ${k} ${w} Z" class="geom-pie-slice geom-pie-slice--${u%5}"/>`;const d=(l+m/2)*Math.PI/180;c+=`<text x="${176+144*Math.cos(d)}" y="${160+144*Math.sin(d)+6}" class="geom-label" text-anchor="middle">${a.label}</text>`,l+=m}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${c}</svg>`}function Ce(e){const{min:r,q1:i,median:n,q3:p,max:o}=e,l=32,a=(416-l)/(o-r||1),u=y=>l+(y-r)*a,m=74,g=48;let b=`
    <line x1="${u(r)}" y1="${m}" x2="${u(i)}" y2="${m}" class="geom-segment"/>
    <line x1="${u(p)}" y1="${m}" x2="${u(o)}" y2="${m}" class="geom-segment"/>
    <line x1="${u(r)}" y1="${m-g/4}" x2="${u(r)}" y2="${m+g/4}" class="geom-segment"/>
    <line x1="${u(o)}" y1="${m-g/4}" x2="${u(o)}" y2="${m+g/4}" class="geom-segment"/>
    <rect x="${u(i)}" y="${m-g/2}" width="${Math.max(u(p)-u(i),1)}" height="${g}" class="geom-boxplot-box"/>
    <line x1="${u(n)}" y1="${m-g/2}" x2="${u(n)}" y2="${m+g/2}" class="geom-boxplot-median"/>
  `;return[r,i,n,p,o].forEach(y=>{b+=`<text x="${u(y)}" y="${m+g/2+29}" class="geom-label" text-anchor="middle">${y}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${b}</svg>`}const ke={cube:`
    <polygon points="64,112 208,112 208,256 64,256" class="geom-solid-face"/>
    <polygon points="64,112 120,64 264,64 208,112" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="208,112 264,64 264,208 208,256" class="geom-solid-face geom-solid-face--side"/>
  `,pave:`
    <polygon points="48,128 240,128 240,256 48,256" class="geom-solid-face"/>
    <polygon points="48,128 96,80 288,80 240,128" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="240,128 288,80 288,208 240,256" class="geom-solid-face geom-solid-face--side"/>
  `,cylindre:`
    <ellipse cx="160" cy="88" rx="88" ry="29" class="geom-solid-face geom-solid-face--top"/>
    <line x1="72" y1="88" x2="72" y2="240" class="geom-segment"/>
    <line x1="248" y1="88" x2="248" y2="240" class="geom-segment"/>
    <path d="M 72 240 A 88 29 0 0 0 248 240" class="geom-solid-face"/>
  `,cone:`
    <ellipse cx="160" cy="240" rx="88" ry="26" class="geom-solid-face"/>
    <line x1="72" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="248" y1="240" x2="160" y2="56" class="geom-segment"/>
  `,sphere:`
    <circle cx="160" cy="160" r="96" class="geom-circle"/>
    <ellipse cx="160" cy="160" rx="96" ry="29" class="geom-solid-face--wire"/>
    <ellipse cx="160" cy="160" rx="32" ry="96" class="geom-solid-face--wire"/>
  `,pyramide:`
    <polygon points="56,240 264,240 192,264 32,264" class="geom-solid-face"/>
    <line x1="56" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="264" y1="240" x2="160" y2="56" class="geom-segment"/>
    <line x1="192" y1="264" x2="160" y2="56" class="geom-segment geom-segment--dashed"/>
    <line x1="32" y1="264" x2="160" y2="56" class="geom-segment"/>
  `,prisme:`
    <polygon points="64,256 176,256 144,160 32,160" class="geom-solid-face"/>
    <polygon points="32,160 144,160 208,96 96,96" class="geom-solid-face geom-solid-face--top"/>
    <polygon points="176,256 144,160 208,96 240,192" class="geom-solid-face geom-solid-face--side"/>
  `},Me={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function Ee(e){const t=ke[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||Me[e.shape]||"Solide"}">${t}</svg>`}const Se={geom:K,tree:he,venn:be,"nested-sets":ye,numberline:fe,bars:we,pie:qe,boxplot:Ce,solid:Ee};function Le(e){return(Se[e.kind]||K)(e)}ne().then(()=>ie());ae(document.getElementById("settings-btn"));const N=document.getElementById("cours-list-view"),h=document.getElementById("cours-reader-view"),U=document.getElementById("cours-grid"),Re=2;let ee=!1;H.me().then(({user:e})=>{ee=!!e.is_guest}).catch(()=>{});const _=new Set;let W=[],X={};const B=new Map;function Ie(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function He(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",t=>{t.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(t=>{t.addEventListener("click",()=>{e.hidden=!0})})}function Ae(){He(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function se(e){const t=X[e.id]||{},s=Object.values(t),r=s.filter(o=>o.status==="done").length,i=e.n_notions||0,n=i?Math.round(r/i*100):0,p=s.some(o=>o.status==="in_progress");return{doneCount:r,total:i,pct:n,anyInProgress:p}}function O(){U.innerHTML="",W.forEach(e=>{const t=se(e),s=document.createElement("article");s.className="chapter-card card card--interactive",s.dataset.id=e.id,s.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ie()}</div>
      </div>
      <h3>${D(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${e.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${t.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${t.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${$("bookOpen")} ${e.n_notions} notion${e.n_notions>1?"s":""}</span>
        <span>${$("check")} ${t.doneCount}/${t.total} terminée${t.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${$("bookOpen")} ${t.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,s.querySelector(".cours-open-btn").addEventListener("click",()=>G(e.id)),U.appendChild(s)})}function Te(e){return e==="seconde"?"cours":`cours_${e}`}async function te(e){if(B.has(e))return B.get(e);const t=e.replace("Chapitre_",""),s=Te(T()),r=await fetch(`data/${s}/chapitre_${t}.json`);if(!r.ok)throw new Error("Contenu introuvable pour "+e);const i=await r.json();return B.set(e,i),i}function _e(){N.hidden=!1,h.hidden=!0,h.innerHTML=""}function Be(){N.hidden=!0,h.hidden=!1}async function G(e){if(ee&&!_.has(e)&&_.size>=Re){Ae();return}_.add(e),h.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,Be();const t=await te(e);oe(e,t)}function Pe(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}const je=[[/racine|carr[ée]e?\b/,"compass"],[/puissance|exposant/,"zap"],[/premier|diviseur|multiple|pgcd|ppcm/,"layers"],[/ensemble.*nombre|nombre.*ensemble/,"database"],[/fonction|courbe|antécédent|image/,"barChart"],[/vecteur|translat|chasles/,"ruler"],[/probabilit|arbre|tirage|hasard|évènement|événement/,"sparkles"],[/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/,"compass"],[/[ée]quation|in[ée]quation|syst[èe]me/,"scale"],[/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/,"barChart"],[/suite/,"sliders"],[/d[ée]riv/,"zap"]];function ze(e){const t=`${e.id} ${e.title}`.toLowerCase();for(const[s,r]of je)if(s.test(t))return r;return"bookOpen"}function Ue(e){const s=[e.intro,e.definition,e.explicationSimple,e.intuition,e.astuce,...(e.exemples||[]).flatMap(r=>[r.enonce,r.explication,r.conclusion,...(r.calcul||[]).map(i=>i.texte)]),...e.reglesImportantes||[],...e.remarques||[],...e.erreursFrequentes||[],...e.aRetenir||[]].filter(Boolean).join(" ").trim().split(/\s+/).filter(Boolean).length;return Math.max(3,Math.round(s/180))}function De(e){if(e.difficulte)return e.difficulte;const t={};return(e.exemples||[]).forEach(r=>{r.difficulte&&(t[r.difficulte]=(t[r.difficulte]||0)+1)}),Object.keys(t).sort((r,i)=>t[i]-t[r])[0]||"moyen"}function Ne(e){const t=(e||"").toLowerCase();return t==="facile"?'<span class="badge badge--success">Facile</span>':t==="difficile"?'<span class="badge badge--danger">Difficile</span>':'<span class="badge badge--warning">Moyen</span>'}function oe(e,t){const s=X[e]||{},r=W.find(n=>n.id===e),i=r?se(r):null;h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${$("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${D(t.title,t.notions.map(n=>n.title))||e.replace(/_/g," ")}</h1>
      ${i?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${i.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${i.doneCount}/${i.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${t.notions.map(n=>{const p=s[n.id],o=(p==null?void 0:p.status)||"todo",l=(n.exemples||[]).length,c=n.figure?1:0,a=n.objectif||(n.intro||"").split(`
`)[0]||"",u=p!=null&&p.quizTotal?Math.round(p.quizScore/p.quizTotal*100):50;return`
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${$(ze(n))}</div>
            <div class="cours-notion-card-badges">${Ne(De(n))}${Pe(o)}</div>
          </div>
          <h3>${n.title}</h3>
          <p class="cours-notion-card-desc">${a}</p>
          <div class="cours-notion-meta">
            <span>${$("clock")} ${Ue(n)} min</span>
            <span>${$("penSquare")} ${l} exemple${l>1?"s":""}</span>
            ${c?`<span>${$("barChart")} ${c} graphique</span>`:""}
          </div>
          ${o==="in_progress"?`
          <div class="cours-notion-card-progress">
            <div class="progress-track"><div class="progress-fill" style="width:${u}%"></div></div>
          </div>`:""}
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${$("play")} ${o==="todo"?"Commencer":o==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,A(h),h.querySelector("#cours-back-to-grid").addEventListener("click",()=>{O(),_e()}),h.querySelectorAll(".cours-read-btn").forEach(n=>{n.addEventListener("click",p=>{const o=p.target.closest(".cours-notion-card").dataset.notion,l=t.notions.find(c=>c.id===o);F(e,t,l)})})}const Q=["blue","purple","green","orange","pink"];function We(e){return`<div class="cours-steps">${(e||[]).map((t,s)=>`
    <div class="cours-step cours-step--${t.couleur||Q[s%Q.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${$(t.icone||"check")}</span>
        <span class="cours-step-index">${s+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
  `).join("")}</div>`}function Xe(e){const t=(e.calcul||[]).map((s,r,i)=>`
    <div class="cours-calc-row">
      ${s.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${s.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
    ${r<i.length-1?`<div class="cours-calc-arrow">${le.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${$("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${t}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function Oe(e){e.querySelectorAll("[data-text]").forEach(t=>{P(t,decodeURIComponent(t.dataset.text)),t.removeAttribute("data-text")})}function Ge(e,t){const s=e.notions.findIndex(n=>n.id===t.id),r=s>0?e.notions[s-1]:null,i=s<e.notions.length-1?e.notions[s+1]:null;return!r&&!i?"":`
    <div class="cours-notion-nav">
      ${r?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${r.id}">
        ${$("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${r.title}</span></span>
      </button>`:"<span></span>"}
      ${i?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${i.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${i.title}</span></span>
        ${$("arrowRight")}
      </button>`:""}
    </div>
  `}function F(e,t,s){var c,a,u,m,g,b,y,C,k,w,M;function r(d){H.saveCourseProgress(e,s.id,d,T()).catch(()=>{})}function i(d,x,f,E){return`
      <div class="cours-box cours-figure-card cours-box--${d}">
        <div class="cours-box-header">${$(x)} <span>${f}</span></div>
        ${E}
      </div>
    `}function n(d){return`<ul class="cours-box-list">${d.map(x=>`<li data-text="${encodeURIComponent(x)}"></li>`).join("")}</ul>`}function p(d){var f,E,L,q,R;const x=[];return d.comprendre&&x.push(i("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(d.comprendre)}"></div>`)),(f=d.lecture)!=null&&f.length&&x.push(i("lecture","eye","Comment lire le graphique ?",n(d.lecture))),(E=d.observations)!=null&&E.length&&x.push(i("observations","penSquare","Ce que montre ce graphique",n(d.observations))),(L=d.etapes)!=null&&L.length&&x.push(i("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${d.etapes.map((I,Y)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${Y+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${I.titre||`Étape ${Y+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(I.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),d.astuce&&x.push(i("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(d.astuce)}"></div>`)),(q=d.pieges)!=null&&q.length&&x.push(i("attention","x","À ne pas confondre",n(d.pieges))),(R=d.aRetenir)!=null&&R.length&&x.push(i("aretenir","star","À retenir",n(d.aRetenir.slice(0,4)))),`
      ${d.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(d.resume)}"></p>`:""}
      <div class="cours-figure-cards">${x.join("")}</div>
    `}function o(d){if(!d)return"";const x=d.explication?p(d.explication):d.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(d.alt)}"></p>`:"";return`
      <div class="cours-figure-layout">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap">${Le(d)}</div>
        </div>
        ${x?`<div class="cours-figure-text-col">${x}</div>`:""}
      </div>
    `}h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${$("arrowLeft")} ${D(t.title,t.notions.map(d=>d.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${s.title}</h1>
    <p class="cours-intro-text">${s.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${$("target")}</div>
      <p>${s.objectif||""}</p>
    </div>

    ${s.explicationSimple?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${$("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${$("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.definition||"")}"></div>
    </div>

    ${o(s.figure)}

    ${s.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${$("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.intuition)}"></div>
    </div>`:""}

    ${(c=s.exemplesConcrets)!=null&&c.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${$("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${s.exemplesConcrets.map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(a=s.reglesImportantes)!=null&&a.length?`
    <div class="cours-section-label">${$("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${s.reglesImportantes.map(d=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(d)}"></div>`).join("")}
    </div>`:""}

    ${(u=s.remarques)!=null&&u.length?`
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${$("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${s.remarques.map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(g=(m=s.methode)==null?void 0:m.etapes)!=null&&g.length?`
    <div class="cours-section-label">${$("compass")} ${s.methode.titre||"Méthode"}</div>
    ${We(s.methode.etapes)}`:""}

    ${(b=s.exemples)!=null&&b.length?`
    <div class="cours-section-label">${$("penSquare")} Exemples</div>
    ${s.exemples.map(Xe).join("")}`:""}

    ${(y=s.erreursFrequentes)!=null&&y.length?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${$("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${s.erreursFrequentes.map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${s.astuce?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${$("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.astuce)}"></div>
    </div>`:""}

    ${(C=s.aRetenir)!=null&&C.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${$("star")} Résumé — à retenir</div>
      <ul class="cours-aretenir-list">
        ${s.aRetenir.slice(0,6).map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(k=s.quizExerciseIds)!=null&&k.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${$("check")} J'ai terminé cette leçon</button>
    </div>

    ${Ge(t,s)}
  `,Oe(h),A(h),h.querySelector("#cours-back-to-chapter").addEventListener("click",()=>oe(e,t)),h.querySelectorAll(".cours-notion-nav-btn").forEach(d=>{d.addEventListener("click",()=>{const x=t.notions.find(f=>f.id===d.dataset.notion);x&&F(e,t,x)})}),r({status:"in_progress"}),(w=s.quizExerciseIds)!=null&&w.length?l(h.querySelector("#cours-quiz-zone")):(M=h.querySelector("#cours-mark-done-btn"))==null||M.addEventListener("click",()=>{r({status:"done"}),h.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${$("check")} Leçon terminée !</span>`});async function l(d){d.innerHTML='<div class="skeleton" style="height:140px;"></div>';let x;try{x=await Promise.all(s.quizExerciseIds.map(q=>H.exercise(q,T()).then(R=>R.exercise)))}catch{d.innerHTML="",r({status:"done"});return}let f=0,E=0;function L(){if(f>=x.length){d.innerHTML=`<div class="card cours-quiz-done">${$("check")} Mini-quiz terminé : <strong>${E}/${x.length}</strong> bonnes réponses.</div>`,A(d.querySelector(".cours-quiz-done")),r({status:"done",quizScore:E,quizTotal:x.length});return}const q=x[f],R=Math.round(f/x.length*100);d.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${$("lightbulb")} Mini-quiz — question ${f+1}/${x.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${R}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${$("check")} J'ai réussi</button>
          </div>
        </div>
      `,A(d.querySelector(".cours-quiz-card")),P(d.querySelector("#cours-quiz-enonce"),q.enonce),d.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const I=d.querySelector("#cours-quiz-answer");I.hidden=!1,P(I,`Réponse : ${q.answer}${q.hint?`
Indice : ${q.hint}`:""}`),d.querySelector("#cours-quiz-reveal").hidden=!0,d.querySelector("#cours-quiz-verdict").hidden=!1}),d.querySelector("#cours-quiz-fail").addEventListener("click",()=>{f+=1,L()}),d.querySelector("#cours-quiz-success").addEventListener("click",()=>{E+=1,f+=1,L()})}L()}}async function Fe(e,t){await G(e);const s=await te(e),r=s.notions.find(i=>i.id===t);r&&F(e,s,r)}function Ye(){U.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${$("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function Ve(){const e=T();let t=!0;try{const l=(await ce()).find(c=>c.classLevel===e);t=l?l.hasCourses!==!1:!0}catch{t=!0}if(!t){Ye();return}const[s,r]=await Promise.all([H.chapters(e),H.getCourseProgress(e).catch(()=>({}))]);W=s.chapters_meta||[],X=r||{},O();const i=new URLSearchParams(window.location.search),n=i.get("chapter"),p=i.get("notion");n&&p?Fe(n,p):n&&G(n)}Ve();re(e=>{["appearance","*"].includes(e.detail.category)&&(N.hidden||O())});
