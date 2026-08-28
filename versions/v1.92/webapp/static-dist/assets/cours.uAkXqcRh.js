import{a as P}from"./api.BbDKMC-Z.js";import"./scroll-reveal.DylWvSAA.js";/* empty css             *//* empty css              */import{g as fe,a as me,f as ge,r as z,t as ye,b as we,n as A,d as qe}from"./searchUtils.BqGWkRiJ.js";/* empty css                 */import"./sidebar.tK9v1U8p.js";import"./command-palette.CL2snDG8.js";import{i as Ee,b as ke,j as Ce}from"./i18n.BsXOP7sr.js";import{b as Se}from"./settingsPopup.BvZbqz1o.js";import{g as H,i as v,I as Me,f as Le}from"./theme.C9IkBjKZ.js";import{a as G}from"./mathrender.C9lrWfgK.js";import{f as V}from"./animations.8K65AECr.js";const Ie=620,Re=460,Ae=34,He=120,ee=50,ce=30,le=30,te=50;function Te(e){const[s,t,n,a]=e.viewBox;let i=Math.min((Ie-ee-ce)/n,(Re-le-te)/a);return i=Math.max(Ae,Math.min(He,i)),{xmin:s,ymin:t,w:n,h:a,unit:i,width:n*i+ee+ce,height:a*i+le+te}}function f(e,s,t){const n=ee+(s-e.xmin)*e.unit,a=e.height-te-(t-e.ymin)*e.unit;return[n,a]}function _(e,s){if(typeof s=="string"){const t=(e.points||[]).find(n=>n.label===s);return t?[t.x,t.y]:[0,0]}return[s.x,s.y]}function je(e){const{xmin:s,ymin:t,w:n,h:a}=e;let i="";for(let d=Math.ceil(s);d<=s+n;d++){const[o,l]=f(e,d,t),[u,c]=f(e,d,t+a);i+=`<line x1="${o}" y1="${l}" x2="${u}" y2="${c}" class="geom-grid-line"/>`}for(let d=Math.ceil(t);d<=t+a;d++){const[o,l]=f(e,s,d),[u,c]=f(e,s+n,d);i+=`<line x1="${o}" y1="${l}" x2="${u}" y2="${c}" class="geom-grid-line"/>`}return i}function _e(e){const{xmin:s,ymin:t,w:n,h:a}=e,i=n*.05,d=a*.05;let o="";for(let c=Math.ceil(s);c<=s+n;c++){if(c===0||c<s+i||c>s+n-i)continue;const[p,m]=f(e,c,0);o+=`<line x1="${p}" y1="${m-4}" x2="${p}" y2="${m+4}" class="geom-tick"/>`,o+=`<text x="${p}" y="${m+18}" class="geom-tick-label" text-anchor="middle">${c}</text>`}for(let c=Math.ceil(t);c<=t+a;c++){if(c===0||c<t+d||c>t+a-d)continue;const[p,m]=f(e,0,c);o+=`<line x1="${p-4}" y1="${m}" x2="${p+4}" y2="${m}" class="geom-tick"/>`,o+=`<text x="${p-9}" y="${m+4}" class="geom-tick-label" text-anchor="end">${c}</text>`}const[l,u]=f(e,0,0);return o+=`<text x="${l-9}" y="${u+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,o}function Ue(e,s){const{xmin:t,ymin:n,w:a,h:i}=e;if(t>0||t+a<0||n>0||n+i<0)return"";const[d,o]=f(e,t,0),[l,u]=f(e,t+a,0),[c,p]=f(e,0,n),[m,$]=f(e,0,n+i);let q=`
    <line x1="${d}" y1="${o}" x2="${l}" y2="${u}" class="geom-axis" marker-end="url(#${s})"/>
    <line x1="${c}" y1="${p}" x2="${m}" y2="${$}" class="geom-axis" marker-end="url(#${s})"/>
    <text x="${l-6}" y="${u-8}" class="geom-axis-label">x</text>
    <text x="${m+10}" y="${$+4}" class="geom-axis-label">y</text>
  `;return q+=_e(e),q}function de(e,s){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${s}"/>
  </marker>`}function ve(e){const s=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${s}`,n=`geom-arrow-vector-${s}`,a=Te(e);let i="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(i+=je(a)),e.axes&&(i+=Ue(a,t)),(e.curves||[]).forEach(o=>{const l=o.points.map(([u,c])=>f(a,u,c).join(",")).join(" ");i+=`<polyline points="${l}" class="geom-curve${o.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(o=>{const l=o.points.map(p=>f(a,..._(e,p)).join(",")).join(" "),u=o.variant?` geom-polygon--${o.variant}`:"",c=o.reveal?` reveal-${o.reveal}`:"";i+=`<polygon points="${l}" class="geom-polygon${u}${c}">${o.tooltip?`<title>${o.tooltip}</title>`:""}</polygon>`}),(e.circles||[]).forEach(o=>{const[l,u]=f(a,..._(e,o.center));i+=`<circle cx="${l}" cy="${u}" r="${o.radius*a.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(o=>{const[l,u]=f(a,..._(e,o.center)),c=o.radius*a.unit,p=o.startDeg*Math.PI/180,m=o.endDeg*Math.PI/180,$=l+c*Math.cos(p),q=u-c*Math.sin(p),k=l+c*Math.cos(m),T=u-c*Math.sin(m),j=Math.abs(o.endDeg-o.startDeg)>180?1:0,I=o.reveal?` reveal-${o.reveal}`:"";if(i+=`<path d="M ${l} ${u} L ${$} ${q} A ${c} ${c} 0 ${j} 1 ${k} ${T} Z" class="geom-angle-arc${I}">${o.tooltip?`<title>${o.tooltip}</title>`:""}</path>`,o.label){const R=(o.startDeg+o.endDeg)/2*(Math.PI/180),C=l+(c+12)*Math.cos(R),W=u-(c+12)*Math.sin(R);i+=`<text x="${C}" y="${W}" class="geom-label">${o.label}</text>`}}),(e.segments||[]).forEach(o=>{const[l,u]=f(a,..._(e,o.from)),[c,p]=f(a,..._(e,o.to)),m=o.variant?` geom-segment--${o.variant}`:"",$=o.reveal?` reveal-${o.reveal}`:"";i+=`<line x1="${l}" y1="${u}" x2="${c}" y2="${p}" class="geom-segment${o.dashed?" geom-segment--dashed":""}${m}${$}">${o.tooltip?`<title>${o.tooltip}</title>`:""}</line>`}),(e.vectors||[]).forEach(o=>{const[l,u]=f(a,..._(e,o.from)),[c,p]=f(a,..._(e,o.to));if(i+=`<line x1="${l}" y1="${u}" x2="${c}" y2="${p}" class="geom-vector" marker-end="url(#${n})"/>`,o.label){const m=(l+c)/2+8,$=(u+p)/2-8;i+=`<text x="${m}" y="${$}" class="geom-label geom-label--vector">${o.label}</text>`}}),(e.points||[]).forEach(o=>{const[l,u]=f(a,o.x,o.y);i+=`<circle cx="${l}" cy="${u}" r="4.5" class="geom-point">${o.tooltip?`<title>${o.tooltip}</title>`:""}</circle>`,o.label&&(i+=`<text x="${l+9}" y="${u-9}" class="geom-label">${o.label}</text>`),(o.showCoords||e.showCoords)&&(i+=`<text x="${l+9}" y="${u-9+15}" class="geom-label geom-coord-label">(${o.x} ; ${o.y})</text>`)}),(e.texts||[]).forEach(o=>{const[l,u]=f(a,o.x,o.y),c=o.weight?` geom-label--${o.weight}`:"",p=o.reveal?` reveal-${o.reveal}`:"",m=o.anchor?` text-anchor="${o.anchor}"`:"";i+=`<text x="${l}" y="${u}" class="geom-label${c}${p}"${m}>${o.label}</text>`}),(e.angles||[]).forEach(o=>{const[l,u]=f(a,..._(e,o.vertex));i+=`<circle cx="${l}" cy="${u}" r="2.5" class="geom-point"/>`,o.label&&(i+=`<text x="${l+10}" y="${u+4}" class="geom-label">${o.label}</text>`)}),`
    <svg viewBox="0 0 ${a.width} ${a.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${de(t,"geom-arrow-head geom-arrow-head--axis")}
        ${de(n,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${i}
    </svg>
  `}function Be(e){const o=e.branches||[],l=o.length||1,u=320/l;let c="";return o.forEach((p,m)=>{const $=32+u*(m+.5),q=m<l/2;c+=`<line x1="48" y1="192" x2="264" y2="${$}" class="geom-tree-edge"/>`,c+=`<text x="${312/2}" y="${(192+$)/2-13}" class="geom-tree-proba">${p.proba||""}</text>`,c+=`<text x="254" y="${q?$-19:$+29}" class="geom-tree-label" text-anchor="end">${p.label}</text>`;const k=p.branches||[],T=k.length||1,j=54;k.forEach((I,R)=>{const C=$+(R-(T-1)/2)*j;c+=`<line x1="264" y1="${$}" x2="528" y2="${C}" class="geom-tree-edge"/>`,c+=`<text x="${792/2}" y="${($+C)/2-13}" class="geom-tree-proba">${I.proba||""}</text>`,c+=`<text x="544" y="${C+6}" class="geom-tree-label">${I.label}</text>`})}),c+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',o.forEach((p,m)=>{const $=32+u*(m+.5);c+=`<circle cx="264" cy="${$}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${c}</svg>`}function Ne(e){const[o,l]=e.sets||["A","B"];let u=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${o}</text>
    <text x="336" y="147" class="geom-label">${l}</text>
  `;return e.overlapLabel&&(u+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${u}</svg>`}function Pe(e){const i=e.labels||[],d=Math.max(i.length,1);let o="";return i.forEach((l,u)=>{const c=42+u*(160/Math.max(d-1,1));o+=`<circle cx="208" cy="224" r="${c}" class="geom-nested-circle"/>`,o+=`<text x="208" y="${224-c+24}" class="geom-label" text-anchor="middle">${l}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${o}</svg>`}function ze(e){const{min:n,max:a}=e,i=32,d=416,o=(d-i)/(a-n||1),l=p=>i+(p-n)*o,u=72;let c=`<line x1="${i}" y1="${u}" x2="${d}" y2="${u}" class="geom-axis"/>`;if(e.highlight){const{from:p,to:m}=e.highlight;c+=`<line x1="${l(p)}" y1="${u}" x2="${l(m)}" y2="${u}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(p=>{const m=l(p.value);c+=`<circle cx="${m}" cy="${u}" r="8" class="${p.filled===!1?"geom-point--open":"geom-point"}"/>`,c+=`<text x="${m}" y="${u+30}" class="geom-label" text-anchor="middle">${p.label??p.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${c}</svg>`}function De(e){const n=e.bars||[],a=e.maxValue||Math.max(...n.map(c=>c.value),1),i=240,d=32,o=384/Math.max(n.length,1),l=o*.6;let u=`<line x1="32" y1="${i}" x2="416" y2="${i}" class="geom-axis"/>`;return n.forEach((c,p)=>{const m=(i-d)*c.value/a,$=32+p*o+(o-l)/2;u+=`<rect x="${$}" y="${i-m}" width="${l}" height="${m}" class="geom-bar"/>`,u+=`<text x="${$+l/2}" y="${i+26}" class="geom-label" text-anchor="middle">${c.label}</text>`,u+=`<text x="${$+l/2}" y="${i-m-10}" class="geom-label" text-anchor="middle">${c.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${u}</svg>`}function Fe(e){const d=e.slices||[],o=d.reduce((c,p)=>c+p.value,0)||1;let l=-90,u="";return d.forEach((c,p)=>{const m=c.value/o*360,$=l*Math.PI/180,q=(l+m)*Math.PI/180,k=176+112*Math.cos($),T=160+112*Math.sin($),j=176+112*Math.cos(q),I=160+112*Math.sin(q),R=m>180?1:0;u+=`<path d="M 176 160 L ${k} ${T} A 112 112 0 ${R} 1 ${j} ${I} Z" class="geom-pie-slice geom-pie-slice--${p%5}"/>`;const C=(l+m/2)*Math.PI/180;u+=`<text x="${176+144*Math.cos(C)}" y="${160+144*Math.sin(C)+6}" class="geom-label" text-anchor="middle">${c.label}</text>`,l+=m}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${u}</svg>`}function We(e){const{min:n,q1:a,median:i,q3:d,max:o}=e,l=32,c=(416-l)/(o-n||1),p=k=>l+(k-n)*c,m=74,$=48;let q=`
    <line x1="${p(n)}" y1="${m}" x2="${p(a)}" y2="${m}" class="geom-segment"/>
    <line x1="${p(d)}" y1="${m}" x2="${p(o)}" y2="${m}" class="geom-segment"/>
    <line x1="${p(n)}" y1="${m-$/4}" x2="${p(n)}" y2="${m+$/4}" class="geom-segment"/>
    <line x1="${p(o)}" y1="${m-$/4}" x2="${p(o)}" y2="${m+$/4}" class="geom-segment"/>
    <rect x="${p(a)}" y="${m-$/2}" width="${Math.max(p(d)-p(a),1)}" height="${$}" class="geom-boxplot-box"/>
    <line x1="${p(i)}" y1="${m-$/2}" x2="${p(i)}" y2="${m+$/2}" class="geom-boxplot-median"/>
  `;return[n,a,i,d,o].forEach(k=>{q+=`<text x="${p(k)}" y="${m+$/2+29}" class="geom-label" text-anchor="middle">${k}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${q}</svg>`}const Oe={cube:`
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
  `},Xe={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function Ge(e){const s=Oe[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||Xe[e.shape]||"Solide"}">${s}</svg>`}const Ve={geom:ve,tree:Be,venn:Ne,"nested-sets":Pe,numberline:ze,bars:De,pie:Fe,boxplot:We,solid:Ge};function Ye(e){return(Ve[e.kind]||ve)(e)}Ee().then(()=>ke());Se(document.getElementById("settings-btn"));const se=document.getElementById("cours-list-view"),b=document.getElementById("cours-reader-view"),B=document.getElementById("cours-grid"),Ze=2;let $e=!1;P.me().then(({user:e})=>{$e=!!e.is_guest}).catch(()=>{});const J=new Set;let D=[],oe={};const Q=new Map;let Y="all";function Je(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Qe(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",s=>{s.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(s=>{s.addEventListener("click",()=>{e.hidden=!0})})}function Ke(){Qe(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function ne(e){const s=oe[e.id]||{},t=Object.values(s),n=t.filter(o=>o.status==="done").length,a=e.n_notions||0,i=a?Math.round(n/a*100):0,d=t.some(o=>o.status==="in_progress");return{doneCount:n,total:a,pct:i,anyInProgress:d}}const et={ongoing:"Aucun cours en cours de lecture.",done:"Aucun cours terminé pour l'instant.",favorites:"Aucun favori pour l'instant — clique sur l'étoile d'un chapitre ou d'une notion pour l'ajouter."};function tt(e,s){const t=`${e}|`;for(const n of s)if(n.startsWith(t))return!0;return!1}function st(e,s,t,n){const a=ne(e);switch(s){case"ongoing":return!(a.total>0&&a.doneCount===a.total)&&(a.anyInProgress||a.doneCount>0);case"done":return a.total>0&&a.doneCount===a.total;case"favorites":return t.has(e.id)||tt(e.id,n);default:return!0}}var pe;(pe=document.getElementById("cours-filter-bar"))==null||pe.addEventListener("click",e=>{const s=e.target.closest(".chapter-filter-pill");s&&(Y=s.dataset.filter,document.querySelectorAll("#cours-filter-bar .chapter-filter-pill").forEach(t=>{t.classList.toggle("active",t===s),t.setAttribute("aria-selected",String(t===s))}),F())});function F(){const e=fe(H()),s=me(H()),t=D.filter(i=>st(i,Y,e,s)),n=document.getElementById("cours-empty-filter");n&&(n.hidden=t.length!==0,n.textContent=et[Y]||"Aucun cours à afficher."),B.hidden=t.length===0,B.innerHTML="",t.forEach(i=>{const d=ne(i),o=e.has(i.id),l=document.createElement("article");l.className="chapter-card card card--interactive",l.dataset.id=i.id,l.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Je()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${o?" is-favorite":""}" aria-label="${o?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${o}">${ge()}</button>
        </div>
      </div>
      <h3>${z(i.title,i.notions_cours)||i.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${i.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${d.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${d.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${v("bookOpen")} ${i.n_notions} notion${i.n_notions>1?"s":""}</span>
        <span>${v("check")} ${d.doneCount}/${d.total} terminée${d.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${v("bookOpen")} ${d.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,l.querySelector(".cours-open-btn").addEventListener("click",()=>Z(i.id)),l.querySelector(".chapter-favorite-btn").addEventListener("click",u=>{u.stopPropagation();const c=ye(i.id,H()),p=u.currentTarget;p.classList.toggle("is-favorite",c),p.setAttribute("aria-pressed",String(c)),p.setAttribute("aria-label",c?"Retirer des favoris":"Ajouter aux favoris"),Y==="favorites"&&!c&&F()}),B.appendChild(l)});const a=document.getElementById("cours-search-input");a!=null&&a.value&&be(a.value)}function ot(e){return e==="seconde"?"cours":`cours_${e}`}async function re(e){if(Q.has(e))return Q.get(e);const s=e.replace("Chapitre_",""),t=ot(H()),n=await fetch(`data/${t}/chapitre_${s}.json`);if(!n.ok)throw new Error("Contenu introuvable pour "+e);const a=await n.json();return Q.set(e,a),a}function nt(){se.hidden=!1,b.hidden=!0,b.innerHTML=""}function rt(){se.hidden=!0,b.hidden=!1}async function Z(e){if($e&&!J.has(e)&&J.size>=Ze){Ke();return}J.add(e),b.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,rt();const s=await re(e);he(e,s)}function at(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}const it=[[/racine|carr[ée]e?\b/,"compass"],[/puissance|exposant/,"zap"],[/premier|diviseur|multiple|pgcd|ppcm/,"layers"],[/ensemble.*nombre|nombre.*ensemble/,"database"],[/fonction|courbe|antécédent|image/,"barChart"],[/vecteur|translat|chasles/,"ruler"],[/probabilit|arbre|tirage|hasard|évènement|événement/,"sparkles"],[/angle|triangle|g[ée]om[ée]trie|solide|cube|sph[èe]re|cylindre|c[oô]ne/,"compass"],[/[ée]quation|in[ée]quation|syst[èe]me/,"scale"],[/statistique|moyenne|m[ée]diane|effectif|s[ée]rie/,"barChart"],[/suite/,"sliders"],[/d[ée]riv/,"zap"]];function ct(e){const s=`${e.id} ${e.title}`.toLowerCase();for(const[t,n]of it)if(t.test(s))return n;return"bookOpen"}function lt(e){const t=[e.intro,e.definition,e.explicationSimple,e.intuition,e.astuce,...(e.exemples||[]).flatMap(n=>[n.enonce,n.explication,n.conclusion,...(n.calcul||[]).map(a=>a.texte)]),...e.reglesImportantes||[],...e.remarques||[],...e.erreursFrequentes||[],...e.aRetenir||[]].filter(Boolean).join(" ").trim().split(/\s+/).filter(Boolean).length;return Math.max(3,Math.round(t/180))}function dt(e){if(e.difficulte)return e.difficulte;const s={};return(e.exemples||[]).forEach(n=>{n.difficulte&&(s[n.difficulte]=(s[n.difficulte]||0)+1)}),Object.keys(s).sort((n,a)=>s[a]-s[n])[0]||"moyen"}function ut(e){const s=(e||"").toLowerCase();return s==="facile"?'<span class="badge badge--success">Facile</span>':s==="difficile"?'<span class="badge badge--danger">Difficile</span>':'<span class="badge badge--warning">Moyen</span>'}function he(e,s){const t=oe[e]||{},n=D.find(d=>d.id===e),a=n?ne(n):null,i=me(H());b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${v("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${z(s.title,s.notions.map(d=>d.title))||e.replace(/_/g," ")}</h1>
      ${a?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${a.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${a.doneCount}/${a.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${s.notions.map(d=>{const o=t[d.id],l=(o==null?void 0:o.status)||"todo",u=(d.exemples||[]).length,c=d.figure?1:0,p=d.objectif||(d.intro||"").split(`
`)[0]||"",m=o!=null&&o.quizTotal?Math.round(o.quizScore/o.quizTotal*100):50,$=i.has(`${e}|${d.id}`);return`
        <div class="card cours-notion-card" data-notion="${d.id}">
          <div class="cours-notion-top">
            <div class="cours-notion-card-icon">${v(ct(d))}</div>
            <div class="cours-notion-card-badges">${ut(dt(d))}${at(l)}</div>
          </div>
          <div class="cours-notion-title-row">
            <h3>${d.title}</h3>
            <button type="button" class="chapter-favorite-btn${$?" is-favorite":""}" aria-label="${$?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${$}">${ge()}</button>
          </div>
          <p class="cours-notion-card-desc">${p}</p>
          <div class="cours-notion-meta">
            <span>${v("clock")} ${lt(d)} min</span>
            <span>${v("penSquare")} ${u} exemple${u>1?"s":""}</span>
            ${c?`<span>${v("barChart")} ${c} graphique</span>`:""}
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
  `,V(b),b.querySelector("#cours-back-to-grid").addEventListener("click",()=>{F(),nt()}),b.querySelectorAll(".cours-read-btn").forEach(d=>{d.addEventListener("click",o=>{const l=o.target.closest(".cours-notion-card").dataset.notion,u=s.notions.find(c=>c.id===l);ae(e,s,u)})}),b.querySelectorAll(".cours-notion-card .chapter-favorite-btn").forEach(d=>{d.addEventListener("click",o=>{o.stopPropagation();const l=d.closest(".cours-notion-card").dataset.notion,u=we(e,l,H());d.classList.toggle("is-favorite",u),d.setAttribute("aria-pressed",String(u)),d.setAttribute("aria-label",u?"Retirer des favoris":"Ajouter aux favoris")})})}const ue=["blue","purple","green","orange","pink"];function pt(e){return`<div class="cours-steps">${(e||[]).map((s,t)=>`
    <div class="cours-step cours-step--${s.couleur||ue[t%ue.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${v(s.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(s.texte)}"></div>
    </div>
  `).join("")}</div>`}function mt(e){const s=!!e.interactif,t=(e.calcul||[]).length,n=(e.calcul||[]).map((i,d,o)=>`
    <div class="cours-calc-row${s?" cours-calc-row--hidden":""}" data-calc-index="${d}">
      ${i.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${i.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(i.texte)}"></div>
    </div>
    ${d<o.length-1?`<div class="cours-calc-arrow${s?" cours-calc-row--hidden":""}" data-calc-index="${d}">${Me.arrowRight}</div>`:""}
  `).join(""),a=`
    <div class="cours-exemple-correction${s?" cours-exemple-correction--hidden":""}">
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.interpretation?`
      <div class="cours-exemple-subblock cours-exemple-interpretation">
        <span class="cours-exemple-subblock-label">${v("lightbulb")} Interprétation</span>
        <div data-text="${encodeURIComponent(e.interpretation)}"></div>
      </div>`:e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>`;return`
    <div class="card cours-exemple-card" data-total-steps="${t}" data-revealed="0">
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
      <div class="cours-calc-block">${n}</div>
      ${s&&t?`
      <div class="cours-exemple-controls">
        <button type="button" class="btn btn-ghost btn-sm cours-exemple-next-btn">${v("eye")} Voir l'étape suivante</button>
      </div>`:""}
      ${a}
    </div>
  `}function U(e,s){const t=(e.questionsEclair||[]).filter(n=>n.apres===s);return t.length?t.map(n=>`
    <div class="cours-question-eclair">
      <div class="cours-question-eclair-label">${v("helpCircle")} <span data-text="${encodeURIComponent(n.question)}"></span></div>
      ${n.piste?`
      <button type="button" class="cours-question-eclair-btn" data-piste="${encodeURIComponent(n.piste)}">${v("eye")} Voir une piste</button>
      <div class="cours-question-eclair-piste" hidden></div>`:""}
    </div>
  `).join(""):""}function gt(e){e.querySelectorAll("[data-text]").forEach(s=>{G(s,decodeURIComponent(s.dataset.text)),s.removeAttribute("data-text")})}function vt(e,s){const t=e.notions.findIndex(i=>i.id===s.id),n=t>0?e.notions[t-1]:null,a=t<e.notions.length-1?e.notions[t+1]:null;return!n&&!a?"":`
    <div class="cours-notion-nav">
      ${n?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${n.id}">
        ${v("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${n.title}</span></span>
      </button>`:"<span></span>"}
      ${a?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${a.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${a.title}</span></span>
        ${v("arrowRight")}
      </button>`:""}
    </div>
  `}function ae(e,s,t){var m,$,q,k,T,j,I,R,C,W,ie;function n(r){P.saveCourseProgress(e,t.id,r,H()).catch(()=>{})}function a(r,g,h,x){return`
      <div class="cours-box cours-figure-card cours-box--${r}">
        <div class="cours-box-header">${v(g)} <span>${h}</span></div>
        ${x}
      </div>
    `}function i(r){return`<ul class="cours-box-list">${r.map(g=>`<li data-text="${encodeURIComponent(g)}"></li>`).join("")}</ul>`}function d(r){var h,x,y,w,E;const g=[];return r.comprendre&&g.push(a("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(r.comprendre)}"></div>`)),(h=r.lecture)!=null&&h.length&&g.push(a("lecture","eye","Comment lire le graphique ?",i(r.lecture))),(x=r.observations)!=null&&x.length&&g.push(a("observations","penSquare","Ce que montre ce graphique",i(r.observations))),(y=r.etapes)!=null&&y.length&&g.push(a("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${r.etapes.map((S,O)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${O+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${S.titre||`Étape ${O+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(S.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),r.astuce&&g.push(a("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(r.astuce)}"></div>`)),(w=r.pieges)!=null&&w.length&&g.push(a("attention","x","À ne pas confondre",i(r.pieges))),(E=r.aRetenir)!=null&&E.length&&g.push(a("aretenir","star","À retenir",i(r.aRetenir.slice(0,4)))),`
      ${r.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(r.resume)}"></p>`:""}
      <div class="cours-figure-cards">${g.join("")}</div>
    `}function o(r,g){var x,y;const h={};return(r.explicationSimple||r.intuition)&&(h.comprendre=r.explicationSimple||r.intuition),g.alt&&(h.observations=[g.alt]),r.astuce&&(h.astuce=r.astuce),(x=r.erreursFrequentes)!=null&&x.length&&(h.pieges=r.erreursFrequentes),(y=r.aRetenir)!=null&&y.length&&(h.aRetenir=r.aRetenir),h}function l(r,g){var S;if(!r)return"";const h=r.explication||o(g,r),y=Object.keys(h).length>0?d(h):r.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(r.alt)}"></p>`:"",w=(S=r.steps)!=null&&S.length?`
      <div class="cours-figure-steps" role="tablist" aria-label="Étapes de la figure">
        ${r.steps.map((O,X)=>`<button type="button" class="cours-figure-step-btn${X===0?" is-active":""}" data-step="${X+1}" role="tab" aria-selected="${X===0}">${X+1}. ${O}</button>`).join("")}
      </div>
      <div class="cours-figure-nav">
        <button type="button" class="btn btn-ghost btn-sm cours-figure-prev-btn" data-total-steps="${r.steps.length}" disabled>${v("arrowLeft")} Précédent</button>
        <button type="button" class="btn btn-ghost btn-sm cours-figure-replay-btn">${v("rotate")} Rejouer l'animation</button>
        <button type="button" class="btn btn-ghost btn-sm cours-figure-next-btn" data-total-steps="${r.steps.length}">Suivant ${v("arrowRight")}</button>
      </div>`:"",E=r.relation?`<div class="cours-figure-relation reveal-3" data-text="${encodeURIComponent(r.relation)}"></div>`:"";return`
      <div class="cours-figure-layout${r.emphasis?" cours-figure-layout--xl":""}">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap${r.emphasis?" cours-figure-wrap--xl":""}" data-step="1">
            ${w}
            ${Ye(r)}
            ${E}
          </div>
        </div>
        ${y?`<div class="cours-figure-text-col">${y}</div>`:""}
      </div>
    `}const u=!!(t.figure&&!t.figure.explication);b.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${v("arrowLeft")} ${z(s.title,s.notions.map(r=>r.title))||e.replace(/_/g," ")}</button>
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
    ${U(t,"pourquoi")}

    ${t.explicationSimple&&!u?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${v("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${v("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${l(t.figure,t)}
    ${U(t,"figure")}

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${v("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}
    ${U(t,"intuition")}

    ${(m=t.exemplesConcrets)!=null&&m.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${v("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map(r=>`<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${($=t.reglesImportantes)!=null&&$.length?`
    <div class="cours-section-label">${v("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(r=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(r)}"></div>`).join("")}
    </div>`:""}

    ${(q=t.remarques)!=null&&q.length?`
    <div class="cours-box cours-box--remarque">
      <div class="cours-box-header">${v("info")} <span>Remarques</span></div>
      <ul class="cours-box-list">
        ${t.remarques.map(r=>`<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(T=(k=t.methode)==null?void 0:k.etapes)!=null&&T.length?`
    <div class="cours-section-label">${v("compass")} ${t.methode.titre||"Méthode"}</div>
    ${pt(t.methode.etapes)}`:""}
    ${U(t,"methode")}

    ${(j=t.exemples)!=null&&j.length?`
    <div class="cours-section-label">${v("penSquare")} Exemples</div>
    ${t.exemples.map(r=>mt(r)+U(t,`exemple:${r.id}`)).join("")}`:""}

    ${(I=t.erreursFrequentes)!=null&&I.length&&!u?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${v("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(r=>`<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce&&!u?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${v("lightbulb")} <span>Astuce NovaMath</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(R=t.aRetenir)!=null&&R.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${v("star")} ${t.resume?"À retenir":"Résumé — à retenir"}</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,6).map(r=>`<li data-text="${encodeURIComponent(r)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.resume?`
    <div class="card cours-resume-card">
      <div class="cours-resume-title">${v("trophy")} Résumé de la leçon</div>
      <p class="cours-resume-text" data-text="${encodeURIComponent(t.resume)}"></p>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(C=t.quizExerciseIds)!=null&&C.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${v("check")} J'ai terminé cette leçon</button>
    </div>

    ${vt(s,t)}
  `,gt(b),V(b),b.querySelector("#cours-back-to-chapter").addEventListener("click",()=>he(e,s));function c(r,g){const h=r.querySelectorAll(".cours-figure-step-btn").length,x=Math.max(1,Math.min(h,g));r.dataset.step=x,r.querySelectorAll(".cours-figure-step-btn").forEach(E=>{const S=Number(E.dataset.step)===x;E.classList.toggle("is-active",S),E.setAttribute("aria-selected",String(S))});const y=r.querySelector(".cours-figure-prev-btn"),w=r.querySelector(".cours-figure-next-btn");y&&(y.disabled=x===1),w&&(w.disabled=x===h)}if(b.querySelectorAll(".cours-figure-step-btn").forEach(r=>{r.addEventListener("click",()=>c(r.closest(".cours-figure-wrap"),Number(r.dataset.step)))}),b.querySelectorAll(".cours-figure-prev-btn").forEach(r=>{r.addEventListener("click",()=>{const g=r.closest(".cours-figure-wrap");c(g,Number(g.dataset.step)-1)})}),b.querySelectorAll(".cours-figure-next-btn").forEach(r=>{r.addEventListener("click",()=>{const g=r.closest(".cours-figure-wrap");c(g,Number(g.dataset.step)+1)})}),b.querySelectorAll(".cours-figure-replay-btn").forEach(r=>{r.addEventListener("click",()=>c(r.closest(".cours-figure-wrap"),1))}),b.querySelectorAll(".cours-exemple-next-btn").forEach(r=>{r.addEventListener("click",()=>{var y,w,E;const g=r.closest(".cours-exemple-card"),h=Number(g.dataset.totalSteps);let x=Number(g.dataset.revealed);x<h?(x+=1,g.dataset.revealed=x,(y=g.querySelector(`.cours-calc-row[data-calc-index="${x-1}"]`))==null||y.classList.remove("cours-calc-row--hidden"),(w=g.querySelector(`.cours-calc-arrow[data-calc-index="${x-1}"]`))==null||w.classList.remove("cours-calc-row--hidden"),r.innerHTML=x===h?`${v("check")} Voir la correction complète`:`${v("eye")} Voir l'étape suivante (${x}/${h})`):((E=g.querySelector(".cours-exemple-correction"))==null||E.classList.remove("cours-exemple-correction--hidden"),r.remove())})}),b.querySelectorAll(".cours-question-eclair-btn").forEach(r=>{r.addEventListener("click",()=>{const g=decodeURIComponent(r.dataset.piste),h=r.nextElementSibling;G(h,g),h.hidden=!1,r.remove()},{once:!0})}),t.uxAnimations&&"IntersectionObserver"in window){const r=b.querySelectorAll(".cours-box, .card, .cours-regle-card, .cours-question-eclair");r.forEach(h=>h.classList.add("cours-anim"));const g=new IntersectionObserver(h=>{h.forEach(x=>{x.isIntersecting&&(x.target.classList.add("is-visible"),g.unobserve(x.target))})},{threshold:.15});r.forEach(h=>g.observe(h))}b.querySelectorAll(".cours-notion-nav-btn").forEach(r=>{r.addEventListener("click",()=>{const g=s.notions.find(h=>h.id===r.dataset.notion);g&&ae(e,s,g)})}),n({status:"in_progress"}),(W=t.quizExerciseIds)!=null&&W.length?p(b.querySelector("#cours-quiz-zone")):(ie=b.querySelector("#cours-mark-done-btn"))==null||ie.addEventListener("click",()=>{n({status:"done"}),b.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${v("check")} Leçon terminée !</span>`});async function p(r){r.innerHTML='<div class="skeleton" style="height:140px;"></div>';let g;try{g=await Promise.all(t.quizExerciseIds.map(w=>P.exercise(w,H()).then(E=>E.exercise)))}catch{r.innerHTML="",n({status:"done"});return}let h=0,x=0;function y(){if(h>=g.length){r.innerHTML=`<div class="card cours-quiz-done">${v("check")} Mini-quiz terminé : <strong>${x}/${g.length}</strong> bonnes réponses.</div>`,V(r.querySelector(".cours-quiz-done")),n({status:"done",quizScore:x,quizTotal:g.length});return}const w=g[h],E=Math.round(h/g.length*100);r.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${v("lightbulb")} Mini-quiz — question ${h+1}/${g.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${E}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${v("check")} J'ai réussi</button>
          </div>
        </div>
      `,V(r.querySelector(".cours-quiz-card")),G(r.querySelector("#cours-quiz-enonce"),w.enonce),r.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const S=r.querySelector("#cours-quiz-answer");S.hidden=!1,G(S,`Réponse : ${w.answer}${w.hint?`
Indice : ${w.hint}`:""}`),r.querySelector("#cours-quiz-reveal").hidden=!0,r.querySelector("#cours-quiz-verdict").hidden=!1}),r.querySelector("#cours-quiz-fail").addEventListener("click",()=>{h+=1,y()}),r.querySelector("#cours-quiz-success").addEventListener("click",()=>{x+=1,h+=1,y()})}y()}}async function $t(e,s){await Z(e);const t=await re(e),n=t.notions.find(a=>a.id===s);n&&ae(e,t,n)}function ht(){B.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${v("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}let xe=[];function xt(){xe=D.flatMap(e=>{const s=z(e.title,e.notions_cours)||e.id.replace(/_/g," "),t={type:"chapter",chapterId:e.id,chapterTitle:s,notionTitle:null,norm:A(s)},n=(e.notions_cours||[]).map(a=>({type:"notion",chapterId:e.id,chapterTitle:s,notionTitle:a,norm:A(`${s} ${a}`),notionNorm:A(a)}));return[t,...n]})}function bt(e){const s=A(e);return s?xe.filter(t=>t.norm.includes(s)).sort((t,n)=>{const a=(t.notionNorm||t.norm).startsWith(s)?0:1,i=(n.notionNorm||n.norm).startsWith(s)?0:1;return a-i}).slice(0,20):[]}const L=document.getElementById("cours-search-input"),N=document.getElementById("cours-search-clear"),M=document.getElementById("cours-search-results");function be(e){const s=A(e);B.querySelectorAll(".chapter-card").forEach(t=>{if(!s){t.classList.remove("is-search-dimmed");return}const n=D.find(d=>d.id===t.dataset.id),a=n?z(n.title,n.notions_cours)||n.id:"",i=A(a).includes(s)||((n==null?void 0:n.notions_cours)||[]).some(d=>A(d).includes(s));t.classList.toggle("is-search-dimmed",!i)})}function K(e){if(N&&(N.hidden=!e),be(e),!e){M.hidden=!0,M.innerHTML="";return}const s=bt(e);if(M.hidden=!1,!s.length){M.innerHTML=`<div class="page-search-empty">Aucun résultat pour « ${e} ».</div>`;return}M.innerHTML=s.map((t,n)=>`
    <button type="button" class="page-search-item${n===0?" is-active":""}" role="option">
      <span class="title">${v(t.type==="chapter"?"bookOpen":"layers")}${t.type==="chapter"?t.chapterTitle:t.notionTitle}</span>
      <span class="subtitle">${t.type==="chapter"?"Chapitre":`${t.chapterTitle} — Notion`}</span>
    </button>
  `).join(""),s.forEach((t,n)=>{M.children[n].addEventListener("click",()=>ft(t))})}async function ft(e){if(L.value=e.type==="chapter"?e.chapterTitle:e.notionTitle,M.hidden=!0,await Z(e.chapterId),e.type!=="notion")return;const t=(await re(e.chapterId)).notions.find(a=>A(a.title)===A(e.notionTitle));if(!t)return;const n=b.querySelector(`.cours-notion-card[data-notion="${CSS.escape(t.id)}"]`);n&&(n.scrollIntoView({behavior:"smooth",block:"center"}),n.classList.add("notion-row--highlight"),setTimeout(()=>n.classList.remove("notion-row--highlight"),1600))}if(L){const e=qe(s=>K(s),250);L.addEventListener("input",()=>e(L.value)),L.addEventListener("keydown",s=>{if(s.key==="Escape"){L.value?(L.value="",K("")):L.blur();return}if(s.key==="Enter"){const t=M.querySelector(".page-search-item.is-active")||M.querySelector(".page-search-item");t==null||t.click();return}if(s.key==="ArrowDown"||s.key==="ArrowUp"){s.preventDefault();const t=[...M.querySelectorAll(".page-search-item")];if(!t.length)return;const n=t.findIndex(i=>i.classList.contains("is-active")),a=Math.max(0,Math.min(t.length-1,n+(s.key==="ArrowDown"?1:-1)));t.forEach(i=>i.classList.remove("is-active")),t[a].classList.add("is-active"),t[a].scrollIntoView({block:"nearest"})}}),N==null||N.addEventListener("click",()=>{L.value="",K(""),L.focus()}),document.addEventListener("click",s=>{!s.target.closest(".page-search")&&!s.target.closest(".page-search-results")&&(M.hidden=!0)})}async function yt(){const e=H();let s=!0;try{const l=(await Le()).find(u=>u.classLevel===e);s=l?l.hasCourses!==!1:!0}catch{s=!0}if(!s){ht();return}const[t,n]=await Promise.all([P.chapters(e),P.getCourseProgress(e).catch(()=>({}))]);D=t.chapters_meta||[],oe=n||{},F(),xt();const a=new URLSearchParams(window.location.search),i=a.get("chapter"),d=a.get("notion");i&&d?$t(i,d):i&&Z(i)}yt();Ce(e=>{["appearance","*"].includes(e.detail.category)&&(se.hidden||F())});
