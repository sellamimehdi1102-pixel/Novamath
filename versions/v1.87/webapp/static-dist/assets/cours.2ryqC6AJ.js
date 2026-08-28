import{a as N}from"./api.BbDKMC-Z.js";import"./scroll-reveal.DylWvSAA.js";/* empty css             *//* empty css              */import{g as xe,a as de,f as ue,r as z,t as he,b as fe,n as L,d as be}from"./searchUtils.DCMPZK1B.js";/* empty css                 */import"./sidebar.3Kg47kBm.js";import"./command-palette.lekfm-sk.js";import{i as ye,b as we,j as ke}from"./i18n.uGFp-Woa.js";import{b as Ee}from"./settingsPopup.D2O5o0bJ.js";import{g as R,i as $,I as Ce,f as qe}from"./theme.C9IkBjKZ.js";import{a as Y}from"./mathrender.C9lrWfgK.js";import{f as F}from"./animations.8K65AECr.js";const Me=620,Se=460,Le=34,Re=120,Z=50,re=30,ie=30,J=50;function Ie(e){const[s,t,o,n]=e.viewBox;let i=Math.min((Me-Z-re)/o,(Se-ie-J)/n);return i=Math.max(Le,Math.min(Re,i)),{xmin:s,ymin:t,w:o,h:n,unit:i,width:o*i+Z+re,height:n*i+ie+J}}function h(e,s,t){const o=Z+(s-e.xmin)*e.unit,n=e.height-J-(t-e.ymin)*e.unit;return[o,n]}function H(e,s){if(typeof s=="string"){const t=(e.points||[]).find(o=>o.label===s);return t?[t.x,t.y]:[0,0]}return[s.x,s.y]}function Ae(e){const{xmin:s,ymin:t,w:o,h:n}=e;let i="";for(let d=Math.ceil(s);d<=s+o;d++){const[r,c]=h(e,d,t),[l,a]=h(e,d,t+n);i+=`<line x1="${r}" y1="${c}" x2="${l}" y2="${a}" class="geom-grid-line"/>`}for(let d=Math.ceil(t);d<=t+n;d++){const[r,c]=h(e,s,d),[l,a]=h(e,s+o,d);i+=`<line x1="${r}" y1="${c}" x2="${l}" y2="${a}" class="geom-grid-line"/>`}return i}function Te(e){const{xmin:s,ymin:t,w:o,h:n}=e,i=o*.05,d=n*.05;let r="";for(let a=Math.ceil(s);a<=s+o;a++){if(a===0||a<s+i||a>s+o-i)continue;const[p,g]=h(e,a,0);r+=`<line x1="${p}" y1="${g-4}" x2="${p}" y2="${g+4}" class="geom-tick"/>`,r+=`<text x="${p}" y="${g+18}" class="geom-tick-label" text-anchor="middle">${a}</text>`}for(let a=Math.ceil(t);a<=t+n;a++){if(a===0||a<t+d||a>t+n-d)continue;const[p,g]=h(e,0,a);r+=`<line x1="${p-4}" y1="${g}" x2="${p+4}" y2="${g}" class="geom-tick"/>`,r+=`<text x="${p-9}" y="${g+4}" class="geom-tick-label" text-anchor="end">${a}</text>`}const[c,l]=h(e,0,0);return r+=`<text x="${c-9}" y="${l+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,r}function He(e,s){const{xmin:t,ymin:o,w:n,h:i}=e;if(t>0||t+n<0||o>0||o+i<0)return"";const[d,r]=h(e,t,0),[c,l]=h(e,t+n,0),[a,p]=h(e,0,o),[g,m]=h(e,0,o+i);let b=`
    <line x1="${d}" y1="${r}" x2="${c}" y2="${l}" class="geom-axis" marker-end="url(#${s})"/>
    <line x1="${a}" y1="${p}" x2="${g}" y2="${m}" class="geom-axis" marker-end="url(#${s})"/>
    <text x="${c-6}" y="${l-8}" class="geom-axis-label">x</text>
    <text x="${g+10}" y="${m+4}" class="geom-axis-label">y</text>
  `;return b+=Te(e),b}function ae(e,s){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${s}"/>
  </marker>`}function pe(e){const s=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${s}`,o=`geom-arrow-vector-${s}`,n=Ie(e);let i="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(i+=Ae(n)),e.axes&&(i+=He(n,t)),(e.curves||[]).forEach(r=>{const c=r.points.map(([l,a])=>h(n,l,a).join(",")).join(" ");i+=`<polyline points="${c}" class="geom-curve${r.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(r=>{const c=r.points.map(l=>h(n,...H(e,l)).join(",")).join(" ");i+=`<polygon points="${c}" class="geom-polygon"/>`}),(e.circles||[]).forEach(r=>{const[c,l]=h(n,...H(e,r.center));i+=`<circle cx="${c}" cy="${l}" r="${r.radius*n.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(r=>{const[c,l]=h(n,...H(e,r.center)),a=r.radius*n.unit,p=r.startDeg*Math.PI/180,g=r.endDeg*Math.PI/180,m=c+a*Math.cos(p),b=l-a*Math.sin(p),y=c+a*Math.cos(g),I=l-a*Math.sin(g),A=Math.abs(r.endDeg-r.startDeg)>180?1:0;if(i+=`<path d="M ${c} ${l} L ${m} ${b} A ${a} ${a} 0 ${A} 1 ${y} ${I} Z" class="geom-angle-arc"/>`,r.label){const q=(r.startDeg+r.endDeg)/2*(Math.PI/180),T=c+(a+12)*Math.cos(q),E=l-(a+12)*Math.sin(q);i+=`<text x="${T}" y="${E}" class="geom-label">${r.label}</text>`}}),(e.segments||[]).forEach(r=>{const[c,l]=h(n,...H(e,r.from)),[a,p]=h(n,...H(e,r.to));i+=`<line x1="${c}" y1="${l}" x2="${a}" y2="${p}" class="geom-segment${r.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(r=>{const[c,l]=h(n,...H(e,r.from)),[a,p]=h(n,...H(e,r.to));if(i+=`<line x1="${c}" y1="${l}" x2="${a}" y2="${p}" class="geom-vector" marker-end="url(#${o})"/>`,r.label){const g=(c+a)/2+8,m=(l+p)/2-8;i+=`<text x="${g}" y="${m}" class="geom-label geom-label--vector">${r.label}</text>`}}),(e.points||[]).forEach(r=>{const[c,l]=h(n,r.x,r.y);i+=`<circle cx="${c}" cy="${l}" r="4.5" class="geom-point"/>`,r.label&&(i+=`<text x="${c+9}" y="${l-9}" class="geom-label">${r.label}</text>`),(r.showCoords||e.showCoords)&&(i+=`<text x="${c+9}" y="${l-9+15}" class="geom-label geom-coord-label">(${r.x} ; ${r.y})</text>`)}),(e.texts||[]).forEach(r=>{const[c,l]=h(n,r.x,r.y);i+=`<text x="${c}" y="${l}" class="geom-label">${r.label}</text>`}),(e.angles||[]).forEach(r=>{const[c,l]=h(n,...H(e,r.vertex));i+=`<circle cx="${c}" cy="${l}" r="2.5" class="geom-point"/>`,r.label&&(i+=`<text x="${c+10}" y="${l+4}" class="geom-label">${r.label}</text>`)}),`
    <svg viewBox="0 0 ${n.width} ${n.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${ae(t,"geom-arrow-head geom-arrow-head--axis")}
        ${ae(o,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${i}
    </svg>
  `}function _e(e){const r=e.branches||[],c=r.length||1,l=320/c;let a="";return r.forEach((p,g)=>{const m=32+l*(g+.5),b=g<c/2;a+=`<line x1="48" y1="192" x2="264" y2="${m}" class="geom-tree-edge"/>`,a+=`<text x="${312/2}" y="${(192+m)/2-13}" class="geom-tree-proba">${p.proba||""}</text>`,a+=`<text x="254" y="${b?m-19:m+29}" class="geom-tree-label" text-anchor="end">${p.label}</text>`;const y=p.branches||[],I=y.length||1,A=54;y.forEach((q,T)=>{const E=m+(T-(I-1)/2)*A;a+=`<line x1="264" y1="${m}" x2="528" y2="${E}" class="geom-tree-edge"/>`,a+=`<text x="${792/2}" y="${(m+E)/2-13}" class="geom-tree-proba">${q.proba||""}</text>`,a+=`<text x="544" y="${E+6}" class="geom-tree-label">${q.label}</text>`})}),a+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',r.forEach((p,g)=>{const m=32+l*(g+.5);a+=`<circle cx="264" cy="${m}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${a}</svg>`}function je(e){const[r,c]=e.sets||["A","B"];let l=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${r}</text>
    <text x="336" y="147" class="geom-label">${c}</text>
  `;return e.overlapLabel&&(l+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${l}</svg>`}function Be(e){const i=e.labels||[],d=Math.max(i.length,1);let r="";return i.forEach((c,l)=>{const a=42+l*(160/Math.max(d-1,1));r+=`<circle cx="208" cy="224" r="${a}" class="geom-nested-circle"/>`,r+=`<text x="208" y="${224-a+24}" class="geom-label" text-anchor="middle">${c}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${r}</svg>`}function Pe(e){const{min:o,max:n}=e,i=32,d=416,r=(d-i)/(n-o||1),c=p=>i+(p-o)*r,l=72;let a=`<line x1="${i}" y1="${l}" x2="${d}" y2="${l}" class="geom-axis"/>`;if(e.highlight){const{from:p,to:g}=e.highlight;a+=`<line x1="${c(p)}" y1="${l}" x2="${c(g)}" y2="${l}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(p=>{const g=c(p.value);a+=`<circle cx="${g}" cy="${l}" r="8" class="${p.filled===!1?"geom-point--open":"geom-point"}"/>`,a+=`<text x="${g}" y="${l+30}" class="geom-label" text-anchor="middle">${p.label??p.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${a}</svg>`}function Ne(e){const o=e.bars||[],n=e.maxValue||Math.max(...o.map(a=>a.value),1),i=240,d=32,r=384/Math.max(o.length,1),c=r*.6;let l=`<line x1="32" y1="${i}" x2="416" y2="${i}" class="geom-axis"/>`;return o.forEach((a,p)=>{const g=(i-d)*a.value/n,m=32+p*r+(r-c)/2;l+=`<rect x="${m}" y="${i-g}" width="${c}" height="${g}" class="geom-bar"/>`,l+=`<text x="${m+c/2}" y="${i+26}" class="geom-label" text-anchor="middle">${a.label}</text>`,l+=`<text x="${m+c/2}" y="${i-g-10}" class="geom-label" text-anchor="middle">${a.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${l}</svg>`}function ze(e){const d=e.slices||[],r=d.reduce((a,p)=>a+p.value,0)||1;let c=-90,l="";return d.forEach((a,p)=>{const g=a.value/r*360,m=c*Math.PI/180,b=(c+g)*Math.PI/180,y=176+112*Math.cos(m),I=160+112*Math.sin(m),A=176+112*Math.cos(b),q=160+112*Math.sin(b),T=g>180?1:0;l+=`<path d="M 176 160 L ${y} ${I} A 112 112 0 ${T} 1 ${A} ${q} Z" class="geom-pie-slice geom-pie-slice--${p%5}"/>`;const E=(c+g/2)*Math.PI/180;l+=`<text x="${176+144*Math.cos(E)}" y="${160+144*Math.sin(E)+6}" class="geom-label" text-anchor="middle">${a.label}</text>`,c+=g}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${l}</svg>`}function Ue(e){const{min:o,q1:n,median:i,q3:d,max:r}=e,c=32,a=(416-c)/(r-o||1),p=y=>c+(y-o)*a,g=74,m=48;let b=`
    <line x1="${p(o)}" y1="${g}" x2="${p(n)}" y2="${g}" class="geom-segment"/>
    <line x1="${p(d)}" y1="${g}" x2="${p(r)}" y2="${g}" class="geom-segment"/>
    <line x1="${p(o)}" y1="${g-m/4}" x2="${p(o)}" y2="${g+m/4}" class="geom-segment"/>
    <line x1="${p(r)}" y1="${g-m/4}" x2="${p(r)}" y2="${g+m/4}" class="geom-segment"/>
    <rect x="${p(n)}" y="${g-m/2}" width="${Math.max(p(d)-p(n),1)}" height="${m}" class="geom-boxplot-box"/>
    <line x1="${p(i)}" y1="${g-m/2}" x2="${p(i)}" y2="${g+m/2}" class="geom-boxplot-median"/>
  `;return[o,n,i,d,r].forEach(y=>{b+=`<text x="${p(y)}" y="${g+m/2+29}" class="geom-label" text-anchor="middle">${y}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${b}</svg>`}const De={cube:`
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
  `},Fe={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function We(e){const s=De[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||Fe[e.shape]||"Solide"}">${s}</svg>`}const Xe={geom:pe,tree:_e,venn:je,"nested-sets":Be,numberline:Pe,bars:Ne,pie:ze,boxplot:Ue,solid:We};function Oe(e){return(Xe[e.kind]||pe)(e)}ye().then(()=>we());Ee(document.getElementById("settings-btn"));const Q=document.getElementById("cours-list-view"),f=document.getElementById("cours-reader-view"),B=document.getElementById("cours-grid"),Ge=2;let ge=!1;N.me().then(({user:e})=>{ge=!!e.is_guest}).catch(()=>{});const O=new Set;let U=[],K={};const G=new Map;let W="all";function Ve(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Ye(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",s=>{s.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(s=>{s.addEventListener("click",()=>{e.hidden=!0})})}function Ze(){Ye(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function ee(e){const s=K[e.id]||{},t=Object.values(s),o=t.filter(r=>r.status==="done").length,n=e.n_notions||0,i=n?Math.round(o/n*100):0,d=t.some(r=>r.status==="in_progress");return{doneCount:o,total:n,pct:i,anyInProgress:d}}const Je={ongoing:"Aucun cours en cours de lecture.",done:"Aucun cours terminé pour l'instant.",favorites:"Aucun favori pour l'instant — clique sur l'étoile d'un chapitre ou d'une notion pour l'ajouter."};function Qe(e,s){const t=`${e}|`;for(const o of s)if(o.startsWith(t))return!0;return!1}function Ke(e,s,t,o){const n=ee(e);switch(s){case"ongoing":return!(n.total>0&&n.doneCount===n.total)&&(n.anyInProgress||n.doneCount>0);case"done":return n.total>0&&n.doneCount===n.total;case"favorites":return t.has(e.id)||Qe(e.id,o);default:return!0}}var le;(le=document.getElementById("cours-filter-bar"))==null||le.addEventListener("click",e=>{const s=e.target.closest(".chapter-filter-pill");s&&(W=s.dataset.filter,document.querySelectorAll("#cours-filter-bar .chapter-filter-pill").forEach(t=>{t.classList.toggle("active",t===s),t.setAttribute("aria-selected",String(t===s))}),D())});function D(){const e=xe(R()),s=de(R()),t=U.filter(i=>Ke(i,W,e,s)),o=document.getElementById("cours-empty-filter");o&&(o.hidden=t.length!==0,o.textContent=Je[W]||"Aucun cours à afficher."),B.hidden=t.length===0,B.innerHTML="",t.forEach(i=>{const d=ee(i),r=e.has(i.id),c=document.createElement("article");c.className="chapter-card card card--interactive",c.dataset.id=i.id,c.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ve()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${r?" is-favorite":""}" aria-label="${r?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${r}">${ue()}</button>
        </div>
      </div>
      <h3>${z(i.title,i.notions_cours)||i.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${i.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${d.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${d.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${$("bookOpen")} ${i.n_notions} notion${i.n_notions>1?"s":""}</span>
        <span>${$("check")} ${d.doneCount}/${d.total} terminée${d.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${$("bookOpen")} ${d.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,c.querySelector(".cours-open-btn").addEventListener("click",()=>X(i.id)),c.querySelector(".chapter-favorite-btn").addEventListener("click",l=>{l.stopPropagation();const a=he(i.id,R()),p=l.currentTarget;p.classList.toggle("is-favorite",a),p.setAttribute("aria-pressed",String(a)),p.setAttribute("aria-label",a?"Retirer des favoris":"Ajouter aux favoris"),W==="favorites"&&!a&&D()}),B.appendChild(c)});const n=document.getElementById("cours-search-input");n!=null&&n.value&&ve(n.value)}function et(e){return e==="seconde"?"cours":`cours_${e}`}async function te(e){if(G.has(e))return G.get(e);const s=e.replace("Chapitre_",""),t=et(R()),o=await fetch(`data/${t}/chapitre_${s}.json`);if(!o.ok)throw new Error("Contenu introuvable pour "+e);const n=await o.json();return G.set(e,n),n}function tt(){Q.hidden=!1,f.hidden=!0,f.innerHTML=""}function st(){Q.hidden=!0,f.hidden=!1}async function X(e){if(ge&&!O.has(e)&&O.size>=Ge){Ze();return}O.add(e),f.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,st();const s=await te(e);me(e,s)}function ot(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}const nt=[[/racine|carr[ée]e?\b/,"compass"],[/puissance|exposant/,"zap"],[/premier|diviseur|multiple|pgcd|ppcm/,"layers"],[/ensemble.*nombre|nombre.*ensemble/,"database"],[/fonction|courbe|antécédent|image/,"barChart"],[/vecteur|translat|chasles/,"ruler"],[/probabilit|arbre|tirage|hasard|évènement|événement/,"sparkles"],[/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/,"compass"],[/[ée]quation|in[ée]quation|syst[èe]me/,"scale"],[/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/,"barChart"],[/suite/,"sliders"],[/d[ée]riv/,"zap"]];function rt(e){const s=`${e.id} ${e.title}`.toLowerCase();for(const[t,o]of nt)if(t.test(s))return o;return"bookOpen"}function it(e){const t=[e.intro,e.definition,e.explicationSimple,e.intuition,e.astuce,...(e.exemples||[]).flatMap(o=>[o.enonce,o.explication,o.conclusion,...(o.calcul||[]).map(n=>n.texte)]),...e.reglesImportantes||[],...e.remarques||[],...e.erreursFrequentes||[],...e.aRetenir||[]].filter(Boolean).join(" ").trim().split(/\s+/).filter(Boolean).length;return Math.max(3,Math.round(t/180))}function at(e){if(e.difficulte)return e.difficulte;const s={};return(e.exemples||[]).forEach(o=>{o.difficulte&&(s[o.difficulte]=(s[o.difficulte]||0)+1)}),Object.keys(s).sort((o,n)=>s[n]-s[o])[0]||"moyen"}function ct(e){const s=(e||"").toLowerCase();return s==="facile"?'<span class="badge badge--success">Facile</span>':s==="difficile"?'<span class="badge badge--danger">Difficile</span>':'<span class="badge badge--warning">Moyen</span>'}function me(e,s){const t=K[e]||{},o=U.find(d=>d.id===e),n=o?ee(o):null,i=de(R());f.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${$("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${z(s.title,s.notions.map(d=>d.title))||e.replace(/_/g," ")}</h1>
      ${n?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${n.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${n.doneCount}/${n.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${s.notions.map(d=>{const r=t[d.id],c=(r==null?void 0:r.status)||"todo",l=(d.exemples||[]).length,a=d.figure?1:0,p=d.objectif||(d.intro||"").split(`
`)[0]||"",g=r!=null&&r.quizTotal?Math.round(r.quizScore/r.quizTotal*100):50,m=i.has(`${e}|${d.id}`);return`
        <div class="card cours-notion-card" data-notion="${d.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${$(rt(d))}</div>
            <div class="cours-notion-card-badges">${ct(at(d))}${ot(c)}</div>
          </div>
          <div class="cours-notion-title-row">
            <h3>${d.title}</h3>
            <button type="button" class="chapter-favorite-btn${m?" is-favorite":""}" aria-label="${m?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${m}">${ue()}</button>
          </div>
          <p class="cours-notion-card-desc">${p}</p>
          <div class="cours-notion-meta">
            <span>${$("clock")} ${it(d)} min</span>
            <span>${$("penSquare")} ${l} exemple${l>1?"s":""}</span>
            ${a?`<span>${$("barChart")} ${a} graphique</span>`:""}
          </div>
          ${c==="in_progress"?`
          <div class="cours-notion-card-progress">
            <div class="progress-track"><div class="progress-fill" style="width:${g}%"></div></div>
          </div>`:""}
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${$("play")} ${c==="todo"?"Commencer":c==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,F(f),f.querySelector("#cours-back-to-grid").addEventListener("click",()=>{D(),tt()}),f.querySelectorAll(".cours-read-btn").forEach(d=>{d.addEventListener("click",r=>{const c=r.target.closest(".cours-notion-card").dataset.notion,l=s.notions.find(a=>a.id===c);se(e,s,l)})}),f.querySelectorAll(".cours-notion-card .chapter-favorite-btn").forEach(d=>{d.addEventListener("click",r=>{r.stopPropagation();const c=d.closest(".cours-notion-card").dataset.notion,l=fe(e,c,R());d.classList.toggle("is-favorite",l),d.setAttribute("aria-pressed",String(l)),d.setAttribute("aria-label",l?"Retirer des favoris":"Ajouter aux favoris")})})}const ce=["blue","purple","green","orange","pink"];function lt(e){return`<div class="cours-steps">${(e||[]).map((s,t)=>`
    <div class="cours-step cours-step--${s.couleur||ce[t%ce.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${$(s.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
  `).join("")}</div>`}function dt(e){const s=(e.calcul||[]).map((t,o,n)=>`
    <div class="cours-calc-row">
      ${t.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${o<n.length-1?`<div class="cours-calc-arrow">${Ce.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${$("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${s}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function ut(e){e.querySelectorAll("[data-text]").forEach(s=>{Y(s,decodeURIComponent(s.dataset.text)),s.removeAttribute("data-text")})}function pt(e,s){const t=e.notions.findIndex(i=>i.id===s.id),o=t>0?e.notions[t-1]:null,n=t<e.notions.length-1?e.notions[t+1]:null;return!o&&!n?"":`
    <div class="cours-notion-nav">
      ${o?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${o.id}">
        ${$("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${o.title}</span></span>
      </button>`:"<span></span>"}
      ${n?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${n.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${n.title}</span></span>
        ${$("arrowRight")}
      </button>`:""}
    </div>
  `}function se(e,s,t){var p,g,m,b,y,I,A,q,T,E,oe;function o(u){N.saveCourseProgress(e,t.id,u,R()).catch(()=>{})}function n(u,v,x,w){return`
      <div class="cours-box cours-figure-card cours-box--${u}">
        <div class="cours-box-header">${$(v)} <span>${x}</span></div>
        ${w}
      </div>
    `}function i(u){return`<ul class="cours-box-list">${u.map(v=>`<li data-text="${encodeURIComponent(v)}"></li>`).join("")}</ul>`}function d(u){var x,w,k,S,_;const v=[];return u.comprendre&&v.push(n("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(u.comprendre)}"></div>`)),(x=u.lecture)!=null&&x.length&&v.push(n("lecture","eye","Comment lire le graphique ?",i(u.lecture))),(w=u.observations)!=null&&w.length&&v.push(n("observations","penSquare","Ce que montre ce graphique",i(u.observations))),(k=u.etapes)!=null&&k.length&&v.push(n("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${u.etapes.map((j,ne)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${ne+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${j.titre||`Étape ${ne+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(j.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),u.astuce&&v.push(n("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(u.astuce)}"></div>`)),(S=u.pieges)!=null&&S.length&&v.push(n("attention","x","À ne pas confondre",i(u.pieges))),(_=u.aRetenir)!=null&&_.length&&v.push(n("aretenir","star","À retenir",i(u.aRetenir.slice(0,4)))),`
      ${u.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(u.resume)}"></p>`:""}
      <div class="cours-figure-cards">${v.join("")}</div>
    `}function r(u,v){var w,k;const x={};return(u.explicationSimple||u.intuition)&&(x.comprendre=u.explicationSimple||u.intuition),v.alt&&(x.observations=[v.alt]),u.astuce&&(x.astuce=u.astuce),(w=u.erreursFrequentes)!=null&&w.length&&(x.pieges=u.erreursFrequentes),(k=u.aRetenir)!=null&&k.length&&(x.aRetenir=u.aRetenir),x}function c(u,v){if(!u)return"";const x=u.explication||r(v,u),k=Object.keys(x).length>0?d(x):u.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(u.alt)}"></p>`:"";return`
      <div class="cours-figure-layout">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap">${Oe(u)}</div>
        </div>
        ${k?`<div class="cours-figure-text-col">${k}</div>`:""}
      </div>
    `}const l=!!(t.figure&&!t.figure.explication);f.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${$("arrowLeft")} ${z(s.title,s.notions.map(u=>u.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${t.title}</h1>
    <p class="cours-intro-text">${t.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${$("target")}</div>
      <p>${t.objectif||""}</p>
    </div>

    ${t.explicationSimple&&!l?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${$("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${$("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${c(t.figure,t)}

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${$("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}

    ${(p=t.exemplesConcrets)!=null&&p.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${$("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map(u=>`<li data-text="${encodeURIComponent(u)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(g=t.reglesImportantes)!=null&&g.length?`
    <div class="cours-section-label">${$("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(u=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(u)}"></div>`).join("")}
    </div>`:""}

    ${(m=t.remarques)!=null&&m.length?`
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${$("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${t.remarques.map(u=>`<li data-text="${encodeURIComponent(u)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(y=(b=t.methode)==null?void 0:b.etapes)!=null&&y.length?`
    <div class="cours-section-label">${$("compass")} ${t.methode.titre||"Méthode"}</div>
    ${lt(t.methode.etapes)}`:""}

    ${(I=t.exemples)!=null&&I.length?`
    <div class="cours-section-label">${$("penSquare")} Exemples</div>
    ${t.exemples.map(dt).join("")}`:""}

    ${(A=t.erreursFrequentes)!=null&&A.length&&!l?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${$("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(u=>`<li data-text="${encodeURIComponent(u)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce&&!l?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${$("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(q=t.aRetenir)!=null&&q.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${$("star")} Résumé — à retenir</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,6).map(u=>`<li data-text="${encodeURIComponent(u)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(T=t.quizExerciseIds)!=null&&T.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${$("check")} J'ai terminé cette leçon</button>
    </div>

    ${pt(s,t)}
  `,ut(f),F(f),f.querySelector("#cours-back-to-chapter").addEventListener("click",()=>me(e,s)),f.querySelectorAll(".cours-notion-nav-btn").forEach(u=>{u.addEventListener("click",()=>{const v=s.notions.find(x=>x.id===u.dataset.notion);v&&se(e,s,v)})}),o({status:"in_progress"}),(E=t.quizExerciseIds)!=null&&E.length?a(f.querySelector("#cours-quiz-zone")):(oe=f.querySelector("#cours-mark-done-btn"))==null||oe.addEventListener("click",()=>{o({status:"done"}),f.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${$("check")} Leçon terminée !</span>`});async function a(u){u.innerHTML='<div class="skeleton" style="height:140px;"></div>';let v;try{v=await Promise.all(t.quizExerciseIds.map(S=>N.exercise(S,R()).then(_=>_.exercise)))}catch{u.innerHTML="",o({status:"done"});return}let x=0,w=0;function k(){if(x>=v.length){u.innerHTML=`<div class="card cours-quiz-done">${$("check")} Mini-quiz terminé : <strong>${w}/${v.length}</strong> bonnes réponses.</div>`,F(u.querySelector(".cours-quiz-done")),o({status:"done",quizScore:w,quizTotal:v.length});return}const S=v[x],_=Math.round(x/v.length*100);u.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${$("lightbulb")} Mini-quiz — question ${x+1}/${v.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${_}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${$("check")} J'ai réussi</button>
          </div>
        </div>
      `,F(u.querySelector(".cours-quiz-card")),Y(u.querySelector("#cours-quiz-enonce"),S.enonce),u.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const j=u.querySelector("#cours-quiz-answer");j.hidden=!1,Y(j,`Réponse : ${S.answer}${S.hint?`
Indice : ${S.hint}`:""}`),u.querySelector("#cours-quiz-reveal").hidden=!0,u.querySelector("#cours-quiz-verdict").hidden=!1}),u.querySelector("#cours-quiz-fail").addEventListener("click",()=>{x+=1,k()}),u.querySelector("#cours-quiz-success").addEventListener("click",()=>{w+=1,x+=1,k()})}k()}}async function gt(e,s){await X(e);const t=await te(e),o=t.notions.find(n=>n.id===s);o&&se(e,t,o)}function mt(){B.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${$("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}let $e=[];function $t(){$e=U.flatMap(e=>{const s=z(e.title,e.notions_cours)||e.id.replace(/_/g," "),t={type:"chapter",chapterId:e.id,chapterTitle:s,notionTitle:null,norm:L(s)},o=(e.notions_cours||[]).map(n=>({type:"notion",chapterId:e.id,chapterTitle:s,notionTitle:n,norm:L(`${s} ${n}`),notionNorm:L(n)}));return[t,...o]})}function vt(e){const s=L(e);return s?$e.filter(t=>t.norm.includes(s)).sort((t,o)=>{const n=(t.notionNorm||t.norm).startsWith(s)?0:1,i=(o.notionNorm||o.norm).startsWith(s)?0:1;return n-i}).slice(0,20):[]}const M=document.getElementById("cours-search-input"),P=document.getElementById("cours-search-clear"),C=document.getElementById("cours-search-results");function ve(e){const s=L(e);B.querySelectorAll(".chapter-card").forEach(t=>{if(!s){t.classList.remove("is-search-dimmed");return}const o=U.find(d=>d.id===t.dataset.id),n=o?z(o.title,o.notions_cours)||o.id:"",i=L(n).includes(s)||((o==null?void 0:o.notions_cours)||[]).some(d=>L(d).includes(s));t.classList.toggle("is-search-dimmed",!i)})}function V(e){if(P&&(P.hidden=!e),ve(e),!e){C.hidden=!0,C.innerHTML="";return}const s=vt(e);if(C.hidden=!1,!s.length){C.innerHTML=`<div class="page-search-empty">Aucun résultat pour « ${e} ».</div>`;return}C.innerHTML=s.map((t,o)=>`
    <button type="button" class="page-search-item${o===0?" is-active":""}" role="option">
      <span class="title">${$(t.type==="chapter"?"bookOpen":"layers")}${t.type==="chapter"?t.chapterTitle:t.notionTitle}</span>
      <span class="subtitle">${t.type==="chapter"?"Chapitre":`${t.chapterTitle} — Notion`}</span>
    </button>
  `).join(""),s.forEach((t,o)=>{C.children[o].addEventListener("click",()=>xt(t))})}async function xt(e){if(M.value=e.type==="chapter"?e.chapterTitle:e.notionTitle,C.hidden=!0,await X(e.chapterId),e.type!=="notion")return;const t=(await te(e.chapterId)).notions.find(n=>L(n.title)===L(e.notionTitle));if(!t)return;const o=f.querySelector(`.cours-notion-card[data-notion="${CSS.escape(t.id)}"]`);o&&(o.scrollIntoView({behavior:"smooth",block:"center"}),o.classList.add("notion-row--highlight"),setTimeout(()=>o.classList.remove("notion-row--highlight"),1600))}if(M){const e=be(s=>V(s),250);M.addEventListener("input",()=>e(M.value)),M.addEventListener("keydown",s=>{if(s.key==="Escape"){M.value?(M.value="",V("")):M.blur();return}if(s.key==="Enter"){const t=C.querySelector(".page-search-item.is-active")||C.querySelector(".page-search-item");t==null||t.click();return}if(s.key==="ArrowDown"||s.key==="ArrowUp"){s.preventDefault();const t=[...C.querySelectorAll(".page-search-item")];if(!t.length)return;const o=t.findIndex(i=>i.classList.contains("is-active")),n=Math.max(0,Math.min(t.length-1,o+(s.key==="ArrowDown"?1:-1)));t.forEach(i=>i.classList.remove("is-active")),t[n].classList.add("is-active"),t[n].scrollIntoView({block:"nearest"})}}),P==null||P.addEventListener("click",()=>{M.value="",V(""),M.focus()}),document.addEventListener("click",s=>{!s.target.closest(".page-search")&&!s.target.closest(".page-search-results")&&(C.hidden=!0)})}async function ht(){const e=R();let s=!0;try{const c=(await qe()).find(l=>l.classLevel===e);s=c?c.hasCourses!==!1:!0}catch{s=!0}if(!s){mt();return}const[t,o]=await Promise.all([N.chapters(e),N.getCourseProgress(e).catch(()=>({}))]);U=t.chapters_meta||[],K=o||{},D(),$t();const n=new URLSearchParams(window.location.search),i=n.get("chapter"),d=n.get("notion");i&&d?gt(i,d):i&&X(i)}ht();ke(e=>{["appearance","*"].includes(e.detail.category)&&(Q.hidden||D())});
