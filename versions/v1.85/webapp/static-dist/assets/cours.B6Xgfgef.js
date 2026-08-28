import{a as A}from"./api.DlOwEDsY.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as N}from"./chapterTitleByNotions.B33dvngo.js";/* empty css                 */import"./sidebar.KwnHgx5Y.js";import"./command-palette.Cpe_rG6b.js";import{i as re,b as ae,l as ce}from"./i18n.DL1tH7oD.js";import{b as le}from"./settingsPopup.Brn01din.js";import{g as _,f as de,i as $,I as ue}from"./theme.3Ba6cpxV.js";import{a as P}from"./mathrender.C9lrWfgK.js";import{f as T}from"./animations.BG9-j6JA.js";const pe=620,me=460,ge=34,$e=120,z=50,J=30,Q=30,U=50;function xe(e){const[t,s,r,i]=e.viewBox;let n=Math.min((pe-z-J)/r,(me-Q-U)/i);return n=Math.max(ge,Math.min($e,n)),{xmin:t,ymin:s,w:r,h:i,unit:n,width:r*n+z+J,height:i*n+Q+U}}function h(e,t,s){const r=z+(t-e.xmin)*e.unit,i=e.height-U-(s-e.ymin)*e.unit;return[r,i]}function L(e,t){if(typeof t=="string"){const s=(e.points||[]).find(r=>r.label===t);return s?[s.x,s.y]:[0,0]}return[t.x,t.y]}function ve(e){const{xmin:t,ymin:s,w:r,h:i}=e;let n="";for(let m=Math.ceil(t);m<=t+r;m++){const[o,d]=h(e,m,s),[c,a]=h(e,m,s+i);n+=`<line x1="${o}" y1="${d}" x2="${c}" y2="${a}" class="geom-grid-line"/>`}for(let m=Math.ceil(s);m<=s+i;m++){const[o,d]=h(e,t,m),[c,a]=h(e,t+r,m);n+=`<line x1="${o}" y1="${d}" x2="${c}" y2="${a}" class="geom-grid-line"/>`}return n}function he(e){const{xmin:t,ymin:s,w:r,h:i}=e,n=r*.05,m=i*.05;let o="";for(let a=Math.ceil(t);a<=t+r;a++){if(a===0||a<t+n||a>t+r-n)continue;const[u,p]=h(e,a,0);o+=`<line x1="${u}" y1="${p-4}" x2="${u}" y2="${p+4}" class="geom-tick"/>`,o+=`<text x="${u}" y="${p+18}" class="geom-tick-label" text-anchor="middle">${a}</text>`}for(let a=Math.ceil(s);a<=s+i;a++){if(a===0||a<s+m||a>s+i-m)continue;const[u,p]=h(e,0,a);o+=`<line x1="${u-4}" y1="${p}" x2="${u+4}" y2="${p}" class="geom-tick"/>`,o+=`<text x="${u-9}" y="${p+4}" class="geom-tick-label" text-anchor="end">${a}</text>`}const[d,c]=h(e,0,0);return o+=`<text x="${d-9}" y="${c+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,o}function be(e,t){const{xmin:s,ymin:r,w:i,h:n}=e;if(s>0||s+i<0||r>0||r+n<0)return"";const[m,o]=h(e,s,0),[d,c]=h(e,s+i,0),[a,u]=h(e,0,r),[p,g]=h(e,0,r+n);let y=`
    <line x1="${m}" y1="${o}" x2="${d}" y2="${c}" class="geom-axis" marker-end="url(#${t})"/>
    <line x1="${a}" y1="${u}" x2="${p}" y2="${g}" class="geom-axis" marker-end="url(#${t})"/>
    <text x="${d-6}" y="${c-8}" class="geom-axis-label">x</text>
    <text x="${p+10}" y="${g+4}" class="geom-axis-label">y</text>
  `;return y+=he(e),y}function K(e,t){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${t}"/>
  </marker>`}function se(e){const t=Math.random().toString(36).slice(2,8),s=`geom-arrow-axis-${t}`,r=`geom-arrow-vector-${t}`,i=xe(e);let n="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(n+=ve(i)),e.axes&&(n+=be(i,s)),(e.curves||[]).forEach(o=>{const d=o.points.map(([c,a])=>h(i,c,a).join(",")).join(" ");n+=`<polyline points="${d}" class="geom-curve${o.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(o=>{const d=o.points.map(c=>h(i,...L(e,c)).join(",")).join(" ");n+=`<polygon points="${d}" class="geom-polygon"/>`}),(e.circles||[]).forEach(o=>{const[d,c]=h(i,...L(e,o.center));n+=`<circle cx="${d}" cy="${c}" r="${o.radius*i.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(o=>{const[d,c]=h(i,...L(e,o.center)),a=o.radius*i.unit,u=o.startDeg*Math.PI/180,p=o.endDeg*Math.PI/180,g=d+a*Math.cos(u),y=c-a*Math.sin(u),f=d+a*Math.cos(p),E=c-a*Math.sin(p),S=Math.abs(o.endDeg-o.startDeg)>180?1:0;if(n+=`<path d="M ${d} ${c} L ${g} ${y} A ${a} ${a} 0 ${S} 1 ${f} ${E} Z" class="geom-angle-arc"/>`,o.label){const k=(o.startDeg+o.endDeg)/2*(Math.PI/180),R=d+(a+12)*Math.cos(k),C=c-(a+12)*Math.sin(k);n+=`<text x="${R}" y="${C}" class="geom-label">${o.label}</text>`}}),(e.segments||[]).forEach(o=>{const[d,c]=h(i,...L(e,o.from)),[a,u]=h(i,...L(e,o.to));n+=`<line x1="${d}" y1="${c}" x2="${a}" y2="${u}" class="geom-segment${o.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(o=>{const[d,c]=h(i,...L(e,o.from)),[a,u]=h(i,...L(e,o.to));if(n+=`<line x1="${d}" y1="${c}" x2="${a}" y2="${u}" class="geom-vector" marker-end="url(#${r})"/>`,o.label){const p=(d+a)/2+8,g=(c+u)/2-8;n+=`<text x="${p}" y="${g}" class="geom-label geom-label--vector">${o.label}</text>`}}),(e.points||[]).forEach(o=>{const[d,c]=h(i,o.x,o.y);n+=`<circle cx="${d}" cy="${c}" r="4.5" class="geom-point"/>`,o.label&&(n+=`<text x="${d+9}" y="${c-9}" class="geom-label">${o.label}</text>`),(o.showCoords||e.showCoords)&&(n+=`<text x="${d+9}" y="${c-9+15}" class="geom-label geom-coord-label">(${o.x} ; ${o.y})</text>`)}),(e.texts||[]).forEach(o=>{const[d,c]=h(i,o.x,o.y);n+=`<text x="${d}" y="${c}" class="geom-label">${o.label}</text>`}),(e.angles||[]).forEach(o=>{const[d,c]=h(i,...L(e,o.vertex));n+=`<circle cx="${d}" cy="${c}" r="2.5" class="geom-point"/>`,o.label&&(n+=`<text x="${d+10}" y="${c+4}" class="geom-label">${o.label}</text>`)}),`
    <svg viewBox="0 0 ${i.width} ${i.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${K(s,"geom-arrow-head geom-arrow-head--axis")}
        ${K(r,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${n}
    </svg>
  `}function ye(e){const o=e.branches||[],d=o.length||1,c=320/d;let a="";return o.forEach((u,p)=>{const g=32+c*(p+.5),y=p<d/2;a+=`<line x1="48" y1="192" x2="264" y2="${g}" class="geom-tree-edge"/>`,a+=`<text x="${312/2}" y="${(192+g)/2-13}" class="geom-tree-proba">${u.proba||""}</text>`,a+=`<text x="254" y="${y?g-19:g+29}" class="geom-tree-label" text-anchor="end">${u.label}</text>`;const f=u.branches||[],E=f.length||1,S=54;f.forEach((k,R)=>{const C=g+(R-(E-1)/2)*S;a+=`<line x1="264" y1="${g}" x2="528" y2="${C}" class="geom-tree-edge"/>`,a+=`<text x="${792/2}" y="${(g+C)/2-13}" class="geom-tree-proba">${k.proba||""}</text>`,a+=`<text x="544" y="${C+6}" class="geom-tree-label">${k.label}</text>`})}),a+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',o.forEach((u,p)=>{const g=32+c*(p+.5);a+=`<circle cx="264" cy="${g}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${a}</svg>`}function fe(e){const[o,d]=e.sets||["A","B"];let c=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${o}</text>
    <text x="336" y="147" class="geom-label">${d}</text>
  `;return e.overlapLabel&&(c+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${c}</svg>`}function we(e){const n=e.labels||[],m=Math.max(n.length,1);let o="";return n.forEach((d,c)=>{const a=42+c*(160/Math.max(m-1,1));o+=`<circle cx="208" cy="224" r="${a}" class="geom-nested-circle"/>`,o+=`<text x="208" y="${224-a+24}" class="geom-label" text-anchor="middle">${d}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${o}</svg>`}function qe(e){const{min:r,max:i}=e,n=32,m=416,o=(m-n)/(i-r||1),d=u=>n+(u-r)*o,c=72;let a=`<line x1="${n}" y1="${c}" x2="${m}" y2="${c}" class="geom-axis"/>`;if(e.highlight){const{from:u,to:p}=e.highlight;a+=`<line x1="${d(u)}" y1="${c}" x2="${d(p)}" y2="${c}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(u=>{const p=d(u.value);a+=`<circle cx="${p}" cy="${c}" r="8" class="${u.filled===!1?"geom-point--open":"geom-point"}"/>`,a+=`<text x="${p}" y="${c+30}" class="geom-label" text-anchor="middle">${u.label??u.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${a}</svg>`}function Ce(e){const r=e.bars||[],i=e.maxValue||Math.max(...r.map(a=>a.value),1),n=240,m=32,o=384/Math.max(r.length,1),d=o*.6;let c=`<line x1="32" y1="${n}" x2="416" y2="${n}" class="geom-axis"/>`;return r.forEach((a,u)=>{const p=(n-m)*a.value/i,g=32+u*o+(o-d)/2;c+=`<rect x="${g}" y="${n-p}" width="${d}" height="${p}" class="geom-bar"/>`,c+=`<text x="${g+d/2}" y="${n+26}" class="geom-label" text-anchor="middle">${a.label}</text>`,c+=`<text x="${g+d/2}" y="${n-p-10}" class="geom-label" text-anchor="middle">${a.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${c}</svg>`}function ke(e){const m=e.slices||[],o=m.reduce((a,u)=>a+u.value,0)||1;let d=-90,c="";return m.forEach((a,u)=>{const p=a.value/o*360,g=d*Math.PI/180,y=(d+p)*Math.PI/180,f=176+112*Math.cos(g),E=160+112*Math.sin(g),S=176+112*Math.cos(y),k=160+112*Math.sin(y),R=p>180?1:0;c+=`<path d="M 176 160 L ${f} ${E} A 112 112 0 ${R} 1 ${S} ${k} Z" class="geom-pie-slice geom-pie-slice--${u%5}"/>`;const C=(d+p/2)*Math.PI/180;c+=`<text x="${176+144*Math.cos(C)}" y="${160+144*Math.sin(C)+6}" class="geom-label" text-anchor="middle">${a.label}</text>`,d+=p}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${c}</svg>`}function Me(e){const{min:r,q1:i,median:n,q3:m,max:o}=e,d=32,a=(416-d)/(o-r||1),u=f=>d+(f-r)*a,p=74,g=48;let y=`
    <line x1="${u(r)}" y1="${p}" x2="${u(i)}" y2="${p}" class="geom-segment"/>
    <line x1="${u(m)}" y1="${p}" x2="${u(o)}" y2="${p}" class="geom-segment"/>
    <line x1="${u(r)}" y1="${p-g/4}" x2="${u(r)}" y2="${p+g/4}" class="geom-segment"/>
    <line x1="${u(o)}" y1="${p-g/4}" x2="${u(o)}" y2="${p+g/4}" class="geom-segment"/>
    <rect x="${u(i)}" y="${p-g/2}" width="${Math.max(u(m)-u(i),1)}" height="${g}" class="geom-boxplot-box"/>
    <line x1="${u(n)}" y1="${p-g/2}" x2="${u(n)}" y2="${p+g/2}" class="geom-boxplot-median"/>
  `;return[r,i,n,m,o].forEach(f=>{y+=`<text x="${u(f)}" y="${p+g/2+29}" class="geom-label" text-anchor="middle">${f}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${y}</svg>`}const Ee={cube:`
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
  `},Se={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function Re(e){const t=Ee[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||Se[e.shape]||"Solide"}">${t}</svg>`}const Le={geom:se,tree:ye,venn:fe,"nested-sets":we,numberline:qe,bars:Ce,pie:ke,boxplot:Me,solid:Re};function Ie(e){return(Le[e.kind]||se)(e)}re().then(()=>ae());le(document.getElementById("settings-btn"));const W=document.getElementById("cours-list-view"),b=document.getElementById("cours-reader-view"),D=document.getElementById("cours-grid"),He=2;let te=!1;A.me().then(({user:e})=>{te=!!e.is_guest}).catch(()=>{});const j=new Set;let X=[],O={};const B=new Map;function Ae(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Te(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",t=>{t.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(t=>{t.addEventListener("click",()=>{e.hidden=!0})})}function _e(){Te(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function oe(e){const t=O[e.id]||{},s=Object.values(t),r=s.filter(o=>o.status==="done").length,i=e.n_notions||0,n=i?Math.round(r/i*100):0,m=s.some(o=>o.status==="in_progress");return{doneCount:r,total:i,pct:n,anyInProgress:m}}function F(){D.innerHTML="",X.forEach(e=>{const t=oe(e),s=document.createElement("article");s.className="chapter-card card card--interactive",s.dataset.id=e.id,s.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ae()}</div>
      </div>
      <h3>${N(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
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
    `,s.querySelector(".cours-open-btn").addEventListener("click",()=>G(e.id)),D.appendChild(s)})}function je(e){return e==="seconde"?"cours":`cours_${e}`}async function ne(e){if(B.has(e))return B.get(e);const t=e.replace("Chapitre_",""),s=je(_()),r=await fetch(`data/${s}/chapitre_${t}.json`);if(!r.ok)throw new Error("Contenu introuvable pour "+e);const i=await r.json();return B.set(e,i),i}function Be(){W.hidden=!1,b.hidden=!0,b.innerHTML=""}function Pe(){W.hidden=!0,b.hidden=!1}async function G(e){if(te&&!j.has(e)&&j.size>=He){_e();return}j.add(e),b.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,Pe();const t=await ne(e);ie(e,t)}function ze(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}const Ue=[[/racine|carr[ée]e?\b/,"compass"],[/puissance|exposant/,"zap"],[/premier|diviseur|multiple|pgcd|ppcm/,"layers"],[/ensemble.*nombre|nombre.*ensemble/,"database"],[/fonction|courbe|antécédent|image/,"barChart"],[/vecteur|translat|chasles/,"ruler"],[/probabilit|arbre|tirage|hasard|évènement|événement/,"sparkles"],[/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/,"compass"],[/[ée]quation|in[ée]quation|syst[èe]me/,"scale"],[/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/,"barChart"],[/suite/,"sliders"],[/d[ée]riv/,"zap"]];function De(e){const t=`${e.id} ${e.title}`.toLowerCase();for(const[s,r]of Ue)if(s.test(t))return r;return"bookOpen"}function Ne(e){const s=[e.intro,e.definition,e.explicationSimple,e.intuition,e.astuce,...(e.exemples||[]).flatMap(r=>[r.enonce,r.explication,r.conclusion,...(r.calcul||[]).map(i=>i.texte)]),...e.reglesImportantes||[],...e.remarques||[],...e.erreursFrequentes||[],...e.aRetenir||[]].filter(Boolean).join(" ").trim().split(/\s+/).filter(Boolean).length;return Math.max(3,Math.round(s/180))}function We(e){if(e.difficulte)return e.difficulte;const t={};return(e.exemples||[]).forEach(r=>{r.difficulte&&(t[r.difficulte]=(t[r.difficulte]||0)+1)}),Object.keys(t).sort((r,i)=>t[i]-t[r])[0]||"moyen"}function Xe(e){const t=(e||"").toLowerCase();return t==="facile"?'<span class="badge badge--success">Facile</span>':t==="difficile"?'<span class="badge badge--danger">Difficile</span>':'<span class="badge badge--warning">Moyen</span>'}function ie(e,t){const s=O[e]||{},r=X.find(n=>n.id===e),i=r?oe(r):null;b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${$("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${N(t.title,t.notions.map(n=>n.title))||e.replace(/_/g," ")}</h1>
      ${i?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${i.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${i.doneCount}/${i.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${t.notions.map(n=>{const m=s[n.id],o=(m==null?void 0:m.status)||"todo",d=(n.exemples||[]).length,c=n.figure?1:0,a=n.objectif||(n.intro||"").split(`
`)[0]||"",u=m!=null&&m.quizTotal?Math.round(m.quizScore/m.quizTotal*100):50;return`
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${$(De(n))}</div>
            <div class="cours-notion-card-badges">${Xe(We(n))}${ze(o)}</div>
          </div>
          <h3>${n.title}</h3>
          <p class="cours-notion-card-desc">${a}</p>
          <div class="cours-notion-meta">
            <span>${$("clock")} ${Ne(n)} min</span>
            <span>${$("penSquare")} ${d} exemple${d>1?"s":""}</span>
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
  `,T(b),b.querySelector("#cours-back-to-grid").addEventListener("click",()=>{F(),Be()}),b.querySelectorAll(".cours-read-btn").forEach(n=>{n.addEventListener("click",m=>{const o=m.target.closest(".cours-notion-card").dataset.notion,d=t.notions.find(c=>c.id===o);Y(e,t,d)})})}const ee=["blue","purple","green","orange","pink"];function Oe(e){return`<div class="cours-steps">${(e||[]).map((t,s)=>`
    <div class="cours-step cours-step--${t.couleur||ee[s%ee.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${$(t.icone||"check")}</span>
        <span class="cours-step-index">${s+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
  `).join("")}</div>`}function Fe(e){const t=(e.calcul||[]).map((s,r,i)=>`
    <div class="cours-calc-row">
      ${s.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${s.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
    ${r<i.length-1?`<div class="cours-calc-arrow">${ue.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${$("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${t}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function Ge(e){e.querySelectorAll("[data-text]").forEach(t=>{P(t,decodeURIComponent(t.dataset.text)),t.removeAttribute("data-text")})}function Ye(e,t){const s=e.notions.findIndex(n=>n.id===t.id),r=s>0?e.notions[s-1]:null,i=s<e.notions.length-1?e.notions[s+1]:null;return!r&&!i?"":`
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
  `}function Y(e,t,s){var u,p,g,y,f,E,S,k,R,C,V;function r(l){A.saveCourseProgress(e,s.id,l,_()).catch(()=>{})}function i(l,x,v,w){return`
      <div class="cours-box cours-figure-card cours-box--${l}">
        <div class="cours-box-header">${$(x)} <span>${v}</span></div>
        ${w}
      </div>
    `}function n(l){return`<ul class="cours-box-list">${l.map(x=>`<li data-text="${encodeURIComponent(x)}"></li>`).join("")}</ul>`}function m(l){var v,w,q,M,I;const x=[];return l.comprendre&&x.push(i("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(l.comprendre)}"></div>`)),(v=l.lecture)!=null&&v.length&&x.push(i("lecture","eye","Comment lire le graphique ?",n(l.lecture))),(w=l.observations)!=null&&w.length&&x.push(i("observations","penSquare","Ce que montre ce graphique",n(l.observations))),(q=l.etapes)!=null&&q.length&&x.push(i("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${l.etapes.map((H,Z)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${Z+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${H.titre||`Étape ${Z+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(H.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),l.astuce&&x.push(i("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(l.astuce)}"></div>`)),(M=l.pieges)!=null&&M.length&&x.push(i("attention","x","À ne pas confondre",n(l.pieges))),(I=l.aRetenir)!=null&&I.length&&x.push(i("aretenir","star","À retenir",n(l.aRetenir.slice(0,4)))),`
      ${l.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(l.resume)}"></p>`:""}
      <div class="cours-figure-cards">${x.join("")}</div>
    `}function o(l,x){var w,q;const v={};return(l.explicationSimple||l.intuition)&&(v.comprendre=l.explicationSimple||l.intuition),x.alt&&(v.observations=[x.alt]),l.astuce&&(v.astuce=l.astuce),(w=l.erreursFrequentes)!=null&&w.length&&(v.pieges=l.erreursFrequentes),(q=l.aRetenir)!=null&&q.length&&(v.aRetenir=l.aRetenir),v}function d(l,x){if(!l)return"";const v=l.explication||o(x,l),q=Object.keys(v).length>0?m(v):l.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(l.alt)}"></p>`:"";return`
      <div class="cours-figure-layout">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap">${Ie(l)}</div>
        </div>
        ${q?`<div class="cours-figure-text-col">${q}</div>`:""}
      </div>
    `}const c=!!(s.figure&&!s.figure.explication);b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${$("arrowLeft")} ${N(t.title,t.notions.map(l=>l.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${s.title}</h1>
    <p class="cours-intro-text">${s.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${$("target")}</div>
      <p>${s.objectif||""}</p>
    </div>

    ${s.explicationSimple&&!c?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${$("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${$("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.definition||"")}"></div>
    </div>

    ${d(s.figure,s)}

    ${s.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${$("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.intuition)}"></div>
    </div>`:""}

    ${(u=s.exemplesConcrets)!=null&&u.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${$("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${s.exemplesConcrets.map(l=>`<li data-text="${encodeURIComponent(l)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(p=s.reglesImportantes)!=null&&p.length?`
    <div class="cours-section-label">${$("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${s.reglesImportantes.map(l=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(l)}"></div>`).join("")}
    </div>`:""}

    ${(g=s.remarques)!=null&&g.length?`
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${$("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${s.remarques.map(l=>`<li data-text="${encodeURIComponent(l)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(f=(y=s.methode)==null?void 0:y.etapes)!=null&&f.length?`
    <div class="cours-section-label">${$("compass")} ${s.methode.titre||"Méthode"}</div>
    ${Oe(s.methode.etapes)}`:""}

    ${(E=s.exemples)!=null&&E.length?`
    <div class="cours-section-label">${$("penSquare")} Exemples</div>
    ${s.exemples.map(Fe).join("")}`:""}

    ${(S=s.erreursFrequentes)!=null&&S.length&&!c?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${$("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${s.erreursFrequentes.map(l=>`<li data-text="${encodeURIComponent(l)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${s.astuce&&!c?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${$("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(s.astuce)}"></div>
    </div>`:""}

    ${(k=s.aRetenir)!=null&&k.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${$("star")} Résumé — à retenir</div>
      <ul class="cours-aretenir-list">
        ${s.aRetenir.slice(0,6).map(l=>`<li data-text="${encodeURIComponent(l)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(R=s.quizExerciseIds)!=null&&R.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${$("check")} J'ai terminé cette leçon</button>
    </div>

    ${Ye(t,s)}
  `,Ge(b),T(b),b.querySelector("#cours-back-to-chapter").addEventListener("click",()=>ie(e,t)),b.querySelectorAll(".cours-notion-nav-btn").forEach(l=>{l.addEventListener("click",()=>{const x=t.notions.find(v=>v.id===l.dataset.notion);x&&Y(e,t,x)})}),r({status:"in_progress"}),(C=s.quizExerciseIds)!=null&&C.length?a(b.querySelector("#cours-quiz-zone")):(V=b.querySelector("#cours-mark-done-btn"))==null||V.addEventListener("click",()=>{r({status:"done"}),b.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${$("check")} Leçon terminée !</span>`});async function a(l){l.innerHTML='<div class="skeleton" style="height:140px;"></div>';let x;try{x=await Promise.all(s.quizExerciseIds.map(M=>A.exercise(M,_()).then(I=>I.exercise)))}catch{l.innerHTML="",r({status:"done"});return}let v=0,w=0;function q(){if(v>=x.length){l.innerHTML=`<div class="card cours-quiz-done">${$("check")} Mini-quiz terminé : <strong>${w}/${x.length}</strong> bonnes réponses.</div>`,T(l.querySelector(".cours-quiz-done")),r({status:"done",quizScore:w,quizTotal:x.length});return}const M=x[v],I=Math.round(v/x.length*100);l.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${$("lightbulb")} Mini-quiz — question ${v+1}/${x.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${I}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${$("check")} J'ai réussi</button>
          </div>
        </div>
      `,T(l.querySelector(".cours-quiz-card")),P(l.querySelector("#cours-quiz-enonce"),M.enonce),l.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const H=l.querySelector("#cours-quiz-answer");H.hidden=!1,P(H,`Réponse : ${M.answer}${M.hint?`
Indice : ${M.hint}`:""}`),l.querySelector("#cours-quiz-reveal").hidden=!0,l.querySelector("#cours-quiz-verdict").hidden=!1}),l.querySelector("#cours-quiz-fail").addEventListener("click",()=>{v+=1,q()}),l.querySelector("#cours-quiz-success").addEventListener("click",()=>{w+=1,v+=1,q()})}q()}}async function Ve(e,t){await G(e);const s=await ne(e),r=s.notions.find(i=>i.id===t);r&&Y(e,s,r)}function Ze(){D.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${$("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function Je(){const e=_();let t=!0;try{const d=(await de()).find(c=>c.classLevel===e);t=d?d.hasCourses!==!1:!0}catch{t=!0}if(!t){Ze();return}const[s,r]=await Promise.all([A.chapters(e),A.getCourseProgress(e).catch(()=>({}))]);X=s.chapters_meta||[],O=r||{},F();const i=new URLSearchParams(window.location.search),n=i.get("chapter"),m=i.get("notion");n&&m?Ve(n,m):n&&G(n)}Je();ce(e=>{["appearance","*"].includes(e.detail.category)&&(W.hidden||F())});
