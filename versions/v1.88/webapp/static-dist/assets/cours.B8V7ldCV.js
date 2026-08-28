import{a as U}from"./api.BbDKMC-Z.js";import"./scroll-reveal.DylWvSAA.js";/* empty css             *//* empty css              */import{g as xe,a as ue,f as pe,r as N,t as be,b as fe,n as L,d as ye}from"./searchUtils.IrA8jUbT.js";/* empty css                 */import"./sidebar.CxQo-1LJ.js";import"./command-palette.DoHNjMQQ.js";import{i as we,b as ke,j as Ce}from"./i18n.DqVHUC1g.js";import{b as Ee}from"./settingsPopup.B_vvAkzK.js";import{g as R,i as v,I as qe,f as Me}from"./theme.C9IkBjKZ.js";import{a as J}from"./mathrender.C9lrWfgK.js";import{f as X}from"./animations.8K65AECr.js";const Se=620,Le=460,Re=34,Ie=120,Q=50,ae=30,ie=30,K=50;function Ae(e){const[s,t,n,r]=e.viewBox;let a=Math.min((Se-Q-ae)/n,(Le-ie-K)/r);return a=Math.max(Re,Math.min(Ie,a)),{xmin:s,ymin:t,w:n,h:r,unit:a,width:n*a+Q+ae,height:r*a+ie+K}}function x(e,s,t){const n=Q+(s-e.xmin)*e.unit,r=e.height-K-(t-e.ymin)*e.unit;return[n,r]}function j(e,s){if(typeof s=="string"){const t=(e.points||[]).find(n=>n.label===s);return t?[t.x,t.y]:[0,0]}return[s.x,s.y]}function He(e){const{xmin:s,ymin:t,w:n,h:r}=e;let a="";for(let u=Math.ceil(s);u<=s+n;u++){const[o,l]=x(e,u,t),[d,i]=x(e,u,t+r);a+=`<line x1="${o}" y1="${l}" x2="${d}" y2="${i}" class="geom-grid-line"/>`}for(let u=Math.ceil(t);u<=t+r;u++){const[o,l]=x(e,s,u),[d,i]=x(e,s+n,u);a+=`<line x1="${o}" y1="${l}" x2="${d}" y2="${i}" class="geom-grid-line"/>`}return a}function Te(e){const{xmin:s,ymin:t,w:n,h:r}=e,a=n*.05,u=r*.05;let o="";for(let i=Math.ceil(s);i<=s+n;i++){if(i===0||i<s+a||i>s+n-a)continue;const[p,m]=x(e,i,0);o+=`<line x1="${p}" y1="${m-4}" x2="${p}" y2="${m+4}" class="geom-tick"/>`,o+=`<text x="${p}" y="${m+18}" class="geom-tick-label" text-anchor="middle">${i}</text>`}for(let i=Math.ceil(t);i<=t+r;i++){if(i===0||i<t+u||i>t+r-u)continue;const[p,m]=x(e,0,i);o+=`<line x1="${p-4}" y1="${m}" x2="${p+4}" y2="${m}" class="geom-tick"/>`,o+=`<text x="${p-9}" y="${m+4}" class="geom-tick-label" text-anchor="end">${i}</text>`}const[l,d]=x(e,0,0);return o+=`<text x="${l-9}" y="${d+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,o}function _e(e,s){const{xmin:t,ymin:n,w:r,h:a}=e;if(t>0||t+r<0||n>0||n+a<0)return"";const[u,o]=x(e,t,0),[l,d]=x(e,t+r,0),[i,p]=x(e,0,n),[m,g]=x(e,0,n+a);let f=`
    <line x1="${u}" y1="${o}" x2="${l}" y2="${d}" class="geom-axis" marker-end="url(#${s})"/>
    <line x1="${i}" y1="${p}" x2="${m}" y2="${g}" class="geom-axis" marker-end="url(#${s})"/>
    <text x="${l-6}" y="${d-8}" class="geom-axis-label">x</text>
    <text x="${m+10}" y="${g+4}" class="geom-axis-label">y</text>
  `;return f+=Te(e),f}function ce(e,s){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${s}"/>
  </marker>`}function me(e){const s=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${s}`,n=`geom-arrow-vector-${s}`,r=Ae(e);let a="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(a+=He(r)),e.axes&&(a+=_e(r,t)),(e.curves||[]).forEach(o=>{const l=o.points.map(([d,i])=>x(r,d,i).join(",")).join(" ");a+=`<polyline points="${l}" class="geom-curve${o.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(o=>{const l=o.points.map(p=>x(r,...j(e,p)).join(",")).join(" "),d=o.variant?` geom-polygon--${o.variant}`:"",i=o.reveal?` reveal-${o.reveal}`:"";a+=`<polygon points="${l}" class="geom-polygon${d}${i}"/>`}),(e.circles||[]).forEach(o=>{const[l,d]=x(r,...j(e,o.center));a+=`<circle cx="${l}" cy="${d}" r="${o.radius*r.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(o=>{const[l,d]=x(r,...j(e,o.center)),i=o.radius*r.unit,p=o.startDeg*Math.PI/180,m=o.endDeg*Math.PI/180,g=l+i*Math.cos(p),f=d-i*Math.sin(p),y=l+i*Math.cos(m),I=d-i*Math.sin(m),A=Math.abs(o.endDeg-o.startDeg)>180?1:0;if(a+=`<path d="M ${l} ${d} L ${g} ${f} A ${i} ${i} 0 ${A} 1 ${y} ${I} Z" class="geom-angle-arc"/>`,o.label){const M=(o.startDeg+o.endDeg)/2*(Math.PI/180),H=l+(i+12)*Math.cos(M),C=d-(i+12)*Math.sin(M);a+=`<text x="${H}" y="${C}" class="geom-label">${o.label}</text>`}}),(e.segments||[]).forEach(o=>{const[l,d]=x(r,...j(e,o.from)),[i,p]=x(r,...j(e,o.to));a+=`<line x1="${l}" y1="${d}" x2="${i}" y2="${p}" class="geom-segment${o.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(o=>{const[l,d]=x(r,...j(e,o.from)),[i,p]=x(r,...j(e,o.to));if(a+=`<line x1="${l}" y1="${d}" x2="${i}" y2="${p}" class="geom-vector" marker-end="url(#${n})"/>`,o.label){const m=(l+i)/2+8,g=(d+p)/2-8;a+=`<text x="${m}" y="${g}" class="geom-label geom-label--vector">${o.label}</text>`}}),(e.points||[]).forEach(o=>{const[l,d]=x(r,o.x,o.y);a+=`<circle cx="${l}" cy="${d}" r="4.5" class="geom-point"/>`,o.label&&(a+=`<text x="${l+9}" y="${d-9}" class="geom-label">${o.label}</text>`),(o.showCoords||e.showCoords)&&(a+=`<text x="${l+9}" y="${d-9+15}" class="geom-label geom-coord-label">(${o.x} ; ${o.y})</text>`)}),(e.texts||[]).forEach(o=>{const[l,d]=x(r,o.x,o.y),i=o.weight?` geom-label--${o.weight}`:"",p=o.reveal?` reveal-${o.reveal}`:"",m=o.anchor?` text-anchor="${o.anchor}"`:"";a+=`<text x="${l}" y="${d}" class="geom-label${i}${p}"${m}>${o.label}</text>`}),(e.angles||[]).forEach(o=>{const[l,d]=x(r,...j(e,o.vertex));a+=`<circle cx="${l}" cy="${d}" r="2.5" class="geom-point"/>`,o.label&&(a+=`<text x="${l+10}" y="${d+4}" class="geom-label">${o.label}</text>`)}),`
    <svg viewBox="0 0 ${r.width} ${r.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${ce(t,"geom-arrow-head geom-arrow-head--axis")}
        ${ce(n,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${a}
    </svg>
  `}function je(e){const o=e.branches||[],l=o.length||1,d=320/l;let i="";return o.forEach((p,m)=>{const g=32+d*(m+.5),f=m<l/2;i+=`<line x1="48" y1="192" x2="264" y2="${g}" class="geom-tree-edge"/>`,i+=`<text x="${312/2}" y="${(192+g)/2-13}" class="geom-tree-proba">${p.proba||""}</text>`,i+=`<text x="254" y="${f?g-19:g+29}" class="geom-tree-label" text-anchor="end">${p.label}</text>`;const y=p.branches||[],I=y.length||1,A=54;y.forEach((M,H)=>{const C=g+(H-(I-1)/2)*A;i+=`<line x1="264" y1="${g}" x2="528" y2="${C}" class="geom-tree-edge"/>`,i+=`<text x="${792/2}" y="${(g+C)/2-13}" class="geom-tree-proba">${M.proba||""}</text>`,i+=`<text x="544" y="${C+6}" class="geom-tree-label">${M.label}</text>`})}),i+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',o.forEach((p,m)=>{const g=32+d*(m+.5);i+=`<circle cx="264" cy="${g}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${i}</svg>`}function Be(e){const[o,l]=e.sets||["A","B"];let d=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${o}</text>
    <text x="336" y="147" class="geom-label">${l}</text>
  `;return e.overlapLabel&&(d+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${d}</svg>`}function Pe(e){const a=e.labels||[],u=Math.max(a.length,1);let o="";return a.forEach((l,d)=>{const i=42+d*(160/Math.max(u-1,1));o+=`<circle cx="208" cy="224" r="${i}" class="geom-nested-circle"/>`,o+=`<text x="208" y="${224-i+24}" class="geom-label" text-anchor="middle">${l}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${o}</svg>`}function Ue(e){const{min:n,max:r}=e,a=32,u=416,o=(u-a)/(r-n||1),l=p=>a+(p-n)*o,d=72;let i=`<line x1="${a}" y1="${d}" x2="${u}" y2="${d}" class="geom-axis"/>`;if(e.highlight){const{from:p,to:m}=e.highlight;i+=`<line x1="${l(p)}" y1="${d}" x2="${l(m)}" y2="${d}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(p=>{const m=l(p.value);i+=`<circle cx="${m}" cy="${d}" r="8" class="${p.filled===!1?"geom-point--open":"geom-point"}"/>`,i+=`<text x="${m}" y="${d+30}" class="geom-label" text-anchor="middle">${p.label??p.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${i}</svg>`}function Ne(e){const n=e.bars||[],r=e.maxValue||Math.max(...n.map(i=>i.value),1),a=240,u=32,o=384/Math.max(n.length,1),l=o*.6;let d=`<line x1="32" y1="${a}" x2="416" y2="${a}" class="geom-axis"/>`;return n.forEach((i,p)=>{const m=(a-u)*i.value/r,g=32+p*o+(o-l)/2;d+=`<rect x="${g}" y="${a-m}" width="${l}" height="${m}" class="geom-bar"/>`,d+=`<text x="${g+l/2}" y="${a+26}" class="geom-label" text-anchor="middle">${i.label}</text>`,d+=`<text x="${g+l/2}" y="${a-m-10}" class="geom-label" text-anchor="middle">${i.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${d}</svg>`}function ze(e){const u=e.slices||[],o=u.reduce((i,p)=>i+p.value,0)||1;let l=-90,d="";return u.forEach((i,p)=>{const m=i.value/o*360,g=l*Math.PI/180,f=(l+m)*Math.PI/180,y=176+112*Math.cos(g),I=160+112*Math.sin(g),A=176+112*Math.cos(f),M=160+112*Math.sin(f),H=m>180?1:0;d+=`<path d="M 176 160 L ${y} ${I} A 112 112 0 ${H} 1 ${A} ${M} Z" class="geom-pie-slice geom-pie-slice--${p%5}"/>`;const C=(l+m/2)*Math.PI/180;d+=`<text x="${176+144*Math.cos(C)}" y="${160+144*Math.sin(C)+6}" class="geom-label" text-anchor="middle">${i.label}</text>`,l+=m}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${d}</svg>`}function De(e){const{min:n,q1:r,median:a,q3:u,max:o}=e,l=32,i=(416-l)/(o-n||1),p=y=>l+(y-n)*i,m=74,g=48;let f=`
    <line x1="${p(n)}" y1="${m}" x2="${p(r)}" y2="${m}" class="geom-segment"/>
    <line x1="${p(u)}" y1="${m}" x2="${p(o)}" y2="${m}" class="geom-segment"/>
    <line x1="${p(n)}" y1="${m-g/4}" x2="${p(n)}" y2="${m+g/4}" class="geom-segment"/>
    <line x1="${p(o)}" y1="${m-g/4}" x2="${p(o)}" y2="${m+g/4}" class="geom-segment"/>
    <rect x="${p(r)}" y="${m-g/2}" width="${Math.max(p(u)-p(r),1)}" height="${g}" class="geom-boxplot-box"/>
    <line x1="${p(a)}" y1="${m-g/2}" x2="${p(a)}" y2="${m+g/2}" class="geom-boxplot-median"/>
  `;return[n,r,a,u,o].forEach(y=>{f+=`<text x="${p(y)}" y="${m+g/2+29}" class="geom-label" text-anchor="middle">${y}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${f}</svg>`}const Fe={cube:`
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
  `},We={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function Xe(e){const s=Fe[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||We[e.shape]||"Solide"}">${s}</svg>`}const Oe={geom:me,tree:je,venn:Be,"nested-sets":Pe,numberline:Ue,bars:Ne,pie:ze,boxplot:De,solid:Xe};function Ge(e){return(Oe[e.kind]||me)(e)}we().then(()=>ke());Ee(document.getElementById("settings-btn"));const ee=document.getElementById("cours-list-view"),b=document.getElementById("cours-reader-view"),B=document.getElementById("cours-grid"),Ve=2;let ge=!1;U.me().then(({user:e})=>{ge=!!e.is_guest}).catch(()=>{});const V=new Set;let z=[],te={};const Y=new Map;let O="all";function Ye(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Ze(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",s=>{s.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(s=>{s.addEventListener("click",()=>{e.hidden=!0})})}function Je(){Ze(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function se(e){const s=te[e.id]||{},t=Object.values(s),n=t.filter(o=>o.status==="done").length,r=e.n_notions||0,a=r?Math.round(n/r*100):0,u=t.some(o=>o.status==="in_progress");return{doneCount:n,total:r,pct:a,anyInProgress:u}}const Qe={ongoing:"Aucun cours en cours de lecture.",done:"Aucun cours terminé pour l'instant.",favorites:"Aucun favori pour l'instant — clique sur l'étoile d'un chapitre ou d'une notion pour l'ajouter."};function Ke(e,s){const t=`${e}|`;for(const n of s)if(n.startsWith(t))return!0;return!1}function et(e,s,t,n){const r=se(e);switch(s){case"ongoing":return!(r.total>0&&r.doneCount===r.total)&&(r.anyInProgress||r.doneCount>0);case"done":return r.total>0&&r.doneCount===r.total;case"favorites":return t.has(e.id)||Ke(e.id,n);default:return!0}}var de;(de=document.getElementById("cours-filter-bar"))==null||de.addEventListener("click",e=>{const s=e.target.closest(".chapter-filter-pill");s&&(O=s.dataset.filter,document.querySelectorAll("#cours-filter-bar .chapter-filter-pill").forEach(t=>{t.classList.toggle("active",t===s),t.setAttribute("aria-selected",String(t===s))}),D())});function D(){const e=xe(R()),s=ue(R()),t=z.filter(a=>et(a,O,e,s)),n=document.getElementById("cours-empty-filter");n&&(n.hidden=t.length!==0,n.textContent=Qe[O]||"Aucun cours à afficher."),B.hidden=t.length===0,B.innerHTML="",t.forEach(a=>{const u=se(a),o=e.has(a.id),l=document.createElement("article");l.className="chapter-card card card--interactive",l.dataset.id=a.id,l.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ye()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${o?" is-favorite":""}" aria-label="${o?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${o}">${pe()}</button>
        </div>
      </div>
      <h3>${N(a.title,a.notions_cours)||a.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${a.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${u.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${u.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${v("bookOpen")} ${a.n_notions} notion${a.n_notions>1?"s":""}</span>
        <span>${v("check")} ${u.doneCount}/${u.total} terminée${u.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${v("bookOpen")} ${u.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,l.querySelector(".cours-open-btn").addEventListener("click",()=>G(a.id)),l.querySelector(".chapter-favorite-btn").addEventListener("click",d=>{d.stopPropagation();const i=be(a.id,R()),p=d.currentTarget;p.classList.toggle("is-favorite",i),p.setAttribute("aria-pressed",String(i)),p.setAttribute("aria-label",i?"Retirer des favoris":"Ajouter aux favoris"),O==="favorites"&&!i&&D()}),B.appendChild(l)});const r=document.getElementById("cours-search-input");r!=null&&r.value&&he(r.value)}function tt(e){return e==="seconde"?"cours":`cours_${e}`}async function oe(e){if(Y.has(e))return Y.get(e);const s=e.replace("Chapitre_",""),t=tt(R()),n=await fetch(`data/${t}/chapitre_${s}.json`);if(!n.ok)throw new Error("Contenu introuvable pour "+e);const r=await n.json();return Y.set(e,r),r}function st(){ee.hidden=!1,b.hidden=!0,b.innerHTML=""}function ot(){ee.hidden=!0,b.hidden=!1}async function G(e){if(ge&&!V.has(e)&&V.size>=Ve){Je();return}V.add(e),b.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,ot();const s=await oe(e);ve(e,s)}function nt(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}const rt=[[/racine|carr[ée]e?\b/,"compass"],[/puissance|exposant/,"zap"],[/premier|diviseur|multiple|pgcd|ppcm/,"layers"],[/ensemble.*nombre|nombre.*ensemble/,"database"],[/fonction|courbe|antécédent|image/,"barChart"],[/vecteur|translat|chasles/,"ruler"],[/probabilit|arbre|tirage|hasard|évènement|événement/,"sparkles"],[/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/,"compass"],[/[ée]quation|in[ée]quation|syst[èe]me/,"scale"],[/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/,"barChart"],[/suite/,"sliders"],[/d[ée]riv/,"zap"]];function at(e){const s=`${e.id} ${e.title}`.toLowerCase();for(const[t,n]of rt)if(t.test(s))return n;return"bookOpen"}function it(e){const t=[e.intro,e.definition,e.explicationSimple,e.intuition,e.astuce,...(e.exemples||[]).flatMap(n=>[n.enonce,n.explication,n.conclusion,...(n.calcul||[]).map(r=>r.texte)]),...e.reglesImportantes||[],...e.remarques||[],...e.erreursFrequentes||[],...e.aRetenir||[]].filter(Boolean).join(" ").trim().split(/\s+/).filter(Boolean).length;return Math.max(3,Math.round(t/180))}function ct(e){if(e.difficulte)return e.difficulte;const s={};return(e.exemples||[]).forEach(n=>{n.difficulte&&(s[n.difficulte]=(s[n.difficulte]||0)+1)}),Object.keys(s).sort((n,r)=>s[r]-s[n])[0]||"moyen"}function lt(e){const s=(e||"").toLowerCase();return s==="facile"?'<span class="badge badge--success">Facile</span>':s==="difficile"?'<span class="badge badge--danger">Difficile</span>':'<span class="badge badge--warning">Moyen</span>'}function ve(e,s){const t=te[e]||{},n=z.find(u=>u.id===e),r=n?se(n):null,a=ue(R());b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${v("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${N(s.title,s.notions.map(u=>u.title))||e.replace(/_/g," ")}</h1>
      ${r?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${r.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${r.doneCount}/${r.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${s.notions.map(u=>{const o=t[u.id],l=(o==null?void 0:o.status)||"todo",d=(u.exemples||[]).length,i=u.figure?1:0,p=u.objectif||(u.intro||"").split(`
`)[0]||"",m=o!=null&&o.quizTotal?Math.round(o.quizScore/o.quizTotal*100):50,g=a.has(`${e}|${u.id}`);return`
        <div class="card cours-notion-card" data-notion="${u.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${v(at(u))}</div>
            <div class="cours-notion-card-badges">${lt(ct(u))}${nt(l)}</div>
          </div>
          <div class="cours-notion-title-row">
            <h3>${u.title}</h3>
            <button type="button" class="chapter-favorite-btn${g?" is-favorite":""}" aria-label="${g?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${g}">${pe()}</button>
          </div>
          <p class="cours-notion-card-desc">${p}</p>
          <div class="cours-notion-meta">
            <span>${v("clock")} ${it(u)} min</span>
            <span>${v("penSquare")} ${d} exemple${d>1?"s":""}</span>
            ${i?`<span>${v("barChart")} ${i} graphique</span>`:""}
          </div>
          ${l==="in_progress"?`
          <div class="cours-notion-card-progress">
            <div class="progress-track"><div class="progress-fill" style="width:${m}%"></div></div>
          </div>`:""}
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${v("play")} ${l==="todo"?"Commencer":l==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,X(b),b.querySelector("#cours-back-to-grid").addEventListener("click",()=>{D(),st()}),b.querySelectorAll(".cours-read-btn").forEach(u=>{u.addEventListener("click",o=>{const l=o.target.closest(".cours-notion-card").dataset.notion,d=s.notions.find(i=>i.id===l);ne(e,s,d)})}),b.querySelectorAll(".cours-notion-card .chapter-favorite-btn").forEach(u=>{u.addEventListener("click",o=>{o.stopPropagation();const l=u.closest(".cours-notion-card").dataset.notion,d=fe(e,l,R());u.classList.toggle("is-favorite",d),u.setAttribute("aria-pressed",String(d)),u.setAttribute("aria-label",d?"Retirer des favoris":"Ajouter aux favoris")})})}const le=["blue","purple","green","orange","pink"];function dt(e){return`<div class="cours-steps">${(e||[]).map((s,t)=>`
    <div class="cours-step cours-step--${s.couleur||le[t%le.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${v(s.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
  `).join("")}</div>`}function ut(e){const s=(e.calcul||[]).map((t,n,r)=>`
    <div class="cours-calc-row">
      ${t.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${n<r.length-1?`<div class="cours-calc-arrow">${qe.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${v("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.analyse?`
      <div class="cours-exemple-subblock">
        <span class="cours-exemple-subblock-label">${v("eye")} Analyse</span>
        <div data-text="${encodeURIComponent(e.analyse)}"></div>
      </div>`:""}
      ${e.choixMethode?`
      <div class="cours-exemple-subblock">
        <span class="cours-exemple-subblock-label">${v("compass")} Méthode choisie</span>
        <div data-text="${encodeURIComponent(e.choixMethode)}"></div>
      </div>`:""}
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${s}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.interpretation?`
      <div class="cours-exemple-subblock cours-exemple-interpretation">
        <span class="cours-exemple-subblock-label">${v("lightbulb")} Interprétation</span>
        <div data-text="${encodeURIComponent(e.interpretation)}"></div>
      </div>`:e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function pt(e){e.querySelectorAll("[data-text]").forEach(s=>{J(s,decodeURIComponent(s.dataset.text)),s.removeAttribute("data-text")})}function mt(e,s){const t=e.notions.findIndex(a=>a.id===s.id),n=t>0?e.notions[t-1]:null,r=t<e.notions.length-1?e.notions[t+1]:null;return!n&&!r?"":`
    <div class="cours-notion-nav">
      ${n?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${n.id}">
        ${v("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${n.title}</span></span>
      </button>`:"<span></span>"}
      ${r?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${r.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${r.title}</span></span>
        ${v("arrowRight")}
      </button>`:""}
    </div>
  `}function ne(e,s,t){var p,m,g,f,y,I,A,M,H,C,re;function n(c){U.saveCourseProgress(e,t.id,c,R()).catch(()=>{})}function r(c,$,h,w){return`
      <div class="cours-box cours-figure-card cours-box--${c}">
        <div class="cours-box-header">${v($)} <span>${h}</span></div>
        ${w}
      </div>
    `}function a(c){return`<ul class="cours-box-list">${c.map($=>`<li data-text="${encodeURIComponent($)}"></li>`).join("")}</ul>`}function u(c){var h,w,k,E,T;const $=[];return c.comprendre&&$.push(r("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(c.comprendre)}"></div>`)),(h=c.lecture)!=null&&h.length&&$.push(r("lecture","eye","Comment lire le graphique ?",a(c.lecture))),(w=c.observations)!=null&&w.length&&$.push(r("observations","penSquare","Ce que montre ce graphique",a(c.observations))),(k=c.etapes)!=null&&k.length&&$.push(r("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${c.etapes.map((_,F)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${F+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${_.titre||`Étape ${F+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(_.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),c.astuce&&$.push(r("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(c.astuce)}"></div>`)),(E=c.pieges)!=null&&E.length&&$.push(r("attention","x","À ne pas confondre",a(c.pieges))),(T=c.aRetenir)!=null&&T.length&&$.push(r("aretenir","star","À retenir",a(c.aRetenir.slice(0,4)))),`
      ${c.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(c.resume)}"></p>`:""}
      <div class="cours-figure-cards">${$.join("")}</div>
    `}function o(c,$){var w,k;const h={};return(c.explicationSimple||c.intuition)&&(h.comprendre=c.explicationSimple||c.intuition),$.alt&&(h.observations=[$.alt]),c.astuce&&(h.astuce=c.astuce),(w=c.erreursFrequentes)!=null&&w.length&&(h.pieges=c.erreursFrequentes),(k=c.aRetenir)!=null&&k.length&&(h.aRetenir=c.aRetenir),h}function l(c,$){var _;if(!c)return"";const h=c.explication||o($,c),k=Object.keys(h).length>0?u(h):c.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(c.alt)}"></p>`:"",E=(_=c.steps)!=null&&_.length?`
      <div class="cours-figure-steps" role="tablist" aria-label="Étapes de la figure">
        ${c.steps.map((F,W)=>`<button type="button" class="cours-figure-step-btn${W===0?" is-active":""}" data-step="${W+1}" role="tab" aria-selected="${W===0}">${W+1}. ${F}</button>`).join("")}
      </div>`:"",T=c.relation?`<div class="cours-figure-relation reveal-3" data-text="${encodeURIComponent(c.relation)}"></div>`:"";return`
      <div class="cours-figure-layout${c.emphasis?" cours-figure-layout--xl":""}">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap${c.emphasis?" cours-figure-wrap--xl":""}" data-step="1">
            ${E}
            ${Ge(c)}
            ${T}
          </div>
        </div>
        ${k?`<div class="cours-figure-text-col">${k}</div>`:""}
      </div>
    `}const d=!!(t.figure&&!t.figure.explication);b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${v("arrowLeft")} ${N(s.title,s.notions.map(c=>c.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${t.title}</h1>
    <p class="cours-intro-text">${t.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${v("target")}</div>
      <p>${t.objectif||""}</p>
    </div>

    ${t.pourquoi?`
    <div class="cours-box cours-box--pourquoi">
      <div class="cours-box-header">${v("sparkles")} <span>Pourquoi apprend-on cela ?</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.pourquoi)}"></div>
    </div>`:""}

    ${t.explicationSimple&&!d?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${v("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${v("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${l(t.figure,t)}

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${v("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}

    ${(p=t.exemplesConcrets)!=null&&p.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${v("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(m=t.reglesImportantes)!=null&&m.length?`
    <div class="cours-section-label">${v("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(c=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(c)}"></div>`).join("")}
    </div>`:""}

    ${(g=t.remarques)!=null&&g.length?`
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${v("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${t.remarques.map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(y=(f=t.methode)==null?void 0:f.etapes)!=null&&y.length?`
    <div class="cours-section-label">${v("compass")} ${t.methode.titre||"Méthode"}</div>
    ${dt(t.methode.etapes)}`:""}

    ${(I=t.exemples)!=null&&I.length?`
    <div class="cours-section-label">${v("penSquare")} Exemples</div>
    ${t.exemples.map(ut).join("")}`:""}

    ${(A=t.erreursFrequentes)!=null&&A.length&&!d?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${v("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce&&!d?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${v("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(M=t.aRetenir)!=null&&M.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${v("star")} ${t.resume?"À retenir":"Résumé — à retenir"}</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,6).map(c=>`<li data-text="${encodeURIComponent(c)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.resume?`
    <div class="card cours-resume-card">
      <div class="cours-resume-title">${v("trophy")} Résumé de la leçon</div>
      <p class="cours-resume-text" data-text="${encodeURIComponent(t.resume)}"></p>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(H=t.quizExerciseIds)!=null&&H.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${v("check")} J'ai terminé cette leçon</button>
    </div>

    ${mt(s,t)}
  `,pt(b),X(b),b.querySelector("#cours-back-to-chapter").addEventListener("click",()=>ve(e,s)),b.querySelectorAll(".cours-figure-step-btn").forEach(c=>{c.addEventListener("click",()=>{const $=c.closest(".cours-figure-wrap");$.dataset.step=c.dataset.step,$.querySelectorAll(".cours-figure-step-btn").forEach(h=>{h.classList.toggle("is-active",h===c),h.setAttribute("aria-selected",String(h===c))})})}),b.querySelectorAll(".cours-notion-nav-btn").forEach(c=>{c.addEventListener("click",()=>{const $=s.notions.find(h=>h.id===c.dataset.notion);$&&ne(e,s,$)})}),n({status:"in_progress"}),(C=t.quizExerciseIds)!=null&&C.length?i(b.querySelector("#cours-quiz-zone")):(re=b.querySelector("#cours-mark-done-btn"))==null||re.addEventListener("click",()=>{n({status:"done"}),b.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${v("check")} Leçon terminée !</span>`});async function i(c){c.innerHTML='<div class="skeleton" style="height:140px;"></div>';let $;try{$=await Promise.all(t.quizExerciseIds.map(E=>U.exercise(E,R()).then(T=>T.exercise)))}catch{c.innerHTML="",n({status:"done"});return}let h=0,w=0;function k(){if(h>=$.length){c.innerHTML=`<div class="card cours-quiz-done">${v("check")} Mini-quiz terminé : <strong>${w}/${$.length}</strong> bonnes réponses.</div>`,X(c.querySelector(".cours-quiz-done")),n({status:"done",quizScore:w,quizTotal:$.length});return}const E=$[h],T=Math.round(h/$.length*100);c.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${v("lightbulb")} Mini-quiz — question ${h+1}/${$.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${T}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${v("check")} J'ai réussi</button>
          </div>
        </div>
      `,X(c.querySelector(".cours-quiz-card")),J(c.querySelector("#cours-quiz-enonce"),E.enonce),c.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const _=c.querySelector("#cours-quiz-answer");_.hidden=!1,J(_,`Réponse : ${E.answer}${E.hint?`
Indice : ${E.hint}`:""}`),c.querySelector("#cours-quiz-reveal").hidden=!0,c.querySelector("#cours-quiz-verdict").hidden=!1}),c.querySelector("#cours-quiz-fail").addEventListener("click",()=>{h+=1,k()}),c.querySelector("#cours-quiz-success").addEventListener("click",()=>{w+=1,h+=1,k()})}k()}}async function gt(e,s){await G(e);const t=await oe(e),n=t.notions.find(r=>r.id===s);n&&ne(e,t,n)}function vt(){B.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${v("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}let $e=[];function $t(){$e=z.flatMap(e=>{const s=N(e.title,e.notions_cours)||e.id.replace(/_/g," "),t={type:"chapter",chapterId:e.id,chapterTitle:s,notionTitle:null,norm:L(s)},n=(e.notions_cours||[]).map(r=>({type:"notion",chapterId:e.id,chapterTitle:s,notionTitle:r,norm:L(`${s} ${r}`),notionNorm:L(r)}));return[t,...n]})}function ht(e){const s=L(e);return s?$e.filter(t=>t.norm.includes(s)).sort((t,n)=>{const r=(t.notionNorm||t.norm).startsWith(s)?0:1,a=(n.notionNorm||n.norm).startsWith(s)?0:1;return r-a}).slice(0,20):[]}const S=document.getElementById("cours-search-input"),P=document.getElementById("cours-search-clear"),q=document.getElementById("cours-search-results");function he(e){const s=L(e);B.querySelectorAll(".chapter-card").forEach(t=>{if(!s){t.classList.remove("is-search-dimmed");return}const n=z.find(u=>u.id===t.dataset.id),r=n?N(n.title,n.notions_cours)||n.id:"",a=L(r).includes(s)||((n==null?void 0:n.notions_cours)||[]).some(u=>L(u).includes(s));t.classList.toggle("is-search-dimmed",!a)})}function Z(e){if(P&&(P.hidden=!e),he(e),!e){q.hidden=!0,q.innerHTML="";return}const s=ht(e);if(q.hidden=!1,!s.length){q.innerHTML=`<div class="page-search-empty">Aucun résultat pour « ${e} ».</div>`;return}q.innerHTML=s.map((t,n)=>`
    <button type="button" class="page-search-item${n===0?" is-active":""}" role="option">
      <span class="title">${v(t.type==="chapter"?"bookOpen":"layers")}${t.type==="chapter"?t.chapterTitle:t.notionTitle}</span>
      <span class="subtitle">${t.type==="chapter"?"Chapitre":`${t.chapterTitle} — Notion`}</span>
    </button>
  `).join(""),s.forEach((t,n)=>{q.children[n].addEventListener("click",()=>xt(t))})}async function xt(e){if(S.value=e.type==="chapter"?e.chapterTitle:e.notionTitle,q.hidden=!0,await G(e.chapterId),e.type!=="notion")return;const t=(await oe(e.chapterId)).notions.find(r=>L(r.title)===L(e.notionTitle));if(!t)return;const n=b.querySelector(`.cours-notion-card[data-notion="${CSS.escape(t.id)}"]`);n&&(n.scrollIntoView({behavior:"smooth",block:"center"}),n.classList.add("notion-row--highlight"),setTimeout(()=>n.classList.remove("notion-row--highlight"),1600))}if(S){const e=ye(s=>Z(s),250);S.addEventListener("input",()=>e(S.value)),S.addEventListener("keydown",s=>{if(s.key==="Escape"){S.value?(S.value="",Z("")):S.blur();return}if(s.key==="Enter"){const t=q.querySelector(".page-search-item.is-active")||q.querySelector(".page-search-item");t==null||t.click();return}if(s.key==="ArrowDown"||s.key==="ArrowUp"){s.preventDefault();const t=[...q.querySelectorAll(".page-search-item")];if(!t.length)return;const n=t.findIndex(a=>a.classList.contains("is-active")),r=Math.max(0,Math.min(t.length-1,n+(s.key==="ArrowDown"?1:-1)));t.forEach(a=>a.classList.remove("is-active")),t[r].classList.add("is-active"),t[r].scrollIntoView({block:"nearest"})}}),P==null||P.addEventListener("click",()=>{S.value="",Z(""),S.focus()}),document.addEventListener("click",s=>{!s.target.closest(".page-search")&&!s.target.closest(".page-search-results")&&(q.hidden=!0)})}async function bt(){const e=R();let s=!0;try{const l=(await Me()).find(d=>d.classLevel===e);s=l?l.hasCourses!==!1:!0}catch{s=!0}if(!s){vt();return}const[t,n]=await Promise.all([U.chapters(e),U.getCourseProgress(e).catch(()=>({}))]);z=t.chapters_meta||[],te=n||{},D(),$t();const r=new URLSearchParams(window.location.search),a=r.get("chapter"),u=r.get("notion");a&&u?gt(a,u):a&&G(a)}bt();Ce(e=>{["appearance","*"].includes(e.detail.category)&&(ee.hidden||D())});
