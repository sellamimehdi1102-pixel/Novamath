import{a as H}from"./api.D9MhFfTx.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as j}from"./chapterTitleByNotions.B33dvngo.js";/* empty css                 */import"./sidebar.BvZUJ-kt.js";import"./command-palette.D-Pi3ruP.js";import{i as oe,b as ne,l as ie}from"./i18n.Bmd5GSU8.js";import{b as ce}from"./settingsPopup.CNWEonKJ.js";import{g as A,f as re,i as x,I as ae}from"./theme.DpqEKRmI.js";import{a as _}from"./mathrender.C9lrWfgK.js";import{f as I}from"./animations.C6RSdq0t.js";const le=620,de=460,ue=34,ge=120,z=50,V=30,F=30,B=50;function me(e){const[o,t,a,i]=e.viewBox;let n=Math.min((le-z-V)/a,(de-F-B)/i);return n=Math.max(ue,Math.min(ge,n)),{xmin:o,ymin:t,w:a,h:i,unit:n,width:a*n+z+V,height:i*n+F+B}}function v(e,o,t){const a=z+(o-e.xmin)*e.unit,i=e.height-B-(t-e.ymin)*e.unit;return[a,i]}function E(e,o){if(typeof o=="string"){const t=(e.points||[]).find(a=>a.label===o);return t?[t.x,t.y]:[0,0]}return[o.x,o.y]}function $e(e){const{xmin:o,ymin:t,w:a,h:i}=e;let n="";for(let m=Math.ceil(o);m<=o+a;m++){const[s,r]=v(e,m,t),[l,c]=v(e,m,t+i);n+=`<line x1="${s}" y1="${r}" x2="${l}" y2="${c}" class="geom-grid-line"/>`}for(let m=Math.ceil(t);m<=t+i;m++){const[s,r]=v(e,o,m),[l,c]=v(e,o+a,m);n+=`<line x1="${s}" y1="${r}" x2="${l}" y2="${c}" class="geom-grid-line"/>`}return n}function pe(e){const{xmin:o,ymin:t,w:a,h:i}=e,n=a*.05,m=i*.05;let s="";for(let c=Math.ceil(o);c<=o+a;c++){if(c===0||c<o+n||c>o+a-n)continue;const[u,g]=v(e,c,0);s+=`<line x1="${u}" y1="${g-4}" x2="${u}" y2="${g+4}" class="geom-tick"/>`,s+=`<text x="${u}" y="${g+18}" class="geom-tick-label" text-anchor="middle">${c}</text>`}for(let c=Math.ceil(t);c<=t+i;c++){if(c===0||c<t+m||c>t+i-m)continue;const[u,g]=v(e,0,c);s+=`<line x1="${u-4}" y1="${g}" x2="${u+4}" y2="${g}" class="geom-tick"/>`,s+=`<text x="${u-9}" y="${g+4}" class="geom-tick-label" text-anchor="end">${c}</text>`}const[r,l]=v(e,0,0);return s+=`<text x="${r-9}" y="${l+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,s}function xe(e,o){const{xmin:t,ymin:a,w:i,h:n}=e;if(t>0||t+i<0||a>0||a+n<0)return"";const[m,s]=v(e,t,0),[r,l]=v(e,t+i,0),[c,u]=v(e,0,a),[g,$]=v(e,0,a+n);let b=`
    <line x1="${m}" y1="${s}" x2="${r}" y2="${l}" class="geom-axis" marker-end="url(#${o})"/>
    <line x1="${c}" y1="${u}" x2="${g}" y2="${$}" class="geom-axis" marker-end="url(#${o})"/>
    <text x="${r-6}" y="${l-8}" class="geom-axis-label">x</text>
    <text x="${g+10}" y="${$+4}" class="geom-axis-label">y</text>
  `;return b+=pe(e),b}function Z(e,o){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${o}"/>
  </marker>`}function J(e){const o=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${o}`,a=`geom-arrow-vector-${o}`,i=me(e);let n="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(n+=$e(i)),e.axes&&(n+=xe(i,t)),(e.curves||[]).forEach(s=>{const r=s.points.map(([l,c])=>v(i,l,c).join(",")).join(" ");n+=`<polyline points="${r}" class="geom-curve${s.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(s=>{const r=s.points.map(l=>v(i,...E(e,l)).join(",")).join(" ");n+=`<polygon points="${r}" class="geom-polygon"/>`}),(e.circles||[]).forEach(s=>{const[r,l]=v(i,...E(e,s.center));n+=`<circle cx="${r}" cy="${l}" r="${s.radius*i.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(s=>{const[r,l]=v(i,...E(e,s.center)),c=s.radius*i.unit,u=s.startDeg*Math.PI/180,g=s.endDeg*Math.PI/180,$=r+c*Math.cos(u),b=l-c*Math.sin(u),y=r+c*Math.cos(g),k=l-c*Math.sin(g),q=Math.abs(s.endDeg-s.startDeg)>180?1:0;if(n+=`<path d="M ${r} ${l} L ${$} ${b} A ${c} ${c} 0 ${q} 1 ${y} ${k} Z" class="geom-angle-arc"/>`,s.label){const w=(s.startDeg+s.endDeg)/2*(Math.PI/180),d=r+(c+12)*Math.cos(w),p=l-(c+12)*Math.sin(w);n+=`<text x="${d}" y="${p}" class="geom-label">${s.label}</text>`}}),(e.segments||[]).forEach(s=>{const[r,l]=v(i,...E(e,s.from)),[c,u]=v(i,...E(e,s.to));n+=`<line x1="${r}" y1="${l}" x2="${c}" y2="${u}" class="geom-segment${s.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(s=>{const[r,l]=v(i,...E(e,s.from)),[c,u]=v(i,...E(e,s.to));if(n+=`<line x1="${r}" y1="${l}" x2="${c}" y2="${u}" class="geom-vector" marker-end="url(#${a})"/>`,s.label){const g=(r+c)/2+8,$=(l+u)/2-8;n+=`<text x="${g}" y="${$}" class="geom-label geom-label--vector">${s.label}</text>`}}),(e.points||[]).forEach(s=>{const[r,l]=v(i,s.x,s.y);n+=`<circle cx="${r}" cy="${l}" r="4.5" class="geom-point"/>`,s.label&&(n+=`<text x="${r+9}" y="${l-9}" class="geom-label">${s.label}</text>`),(s.showCoords||e.showCoords)&&(n+=`<text x="${r+9}" y="${l-9+15}" class="geom-label geom-coord-label">(${s.x} ; ${s.y})</text>`)}),(e.texts||[]).forEach(s=>{const[r,l]=v(i,s.x,s.y);n+=`<text x="${r}" y="${l}" class="geom-label">${s.label}</text>`}),(e.angles||[]).forEach(s=>{const[r,l]=v(i,...E(e,s.vertex));n+=`<circle cx="${r}" cy="${l}" r="2.5" class="geom-point"/>`,s.label&&(n+=`<text x="${r+10}" y="${l+4}" class="geom-label">${s.label}</text>`)}),`
    <svg viewBox="0 0 ${i.width} ${i.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${Z(t,"geom-arrow-head geom-arrow-head--axis")}
        ${Z(a,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${n}
    </svg>
  `}function ve(e){const s=e.branches||[],r=s.length||1,l=320/r;let c="";return s.forEach((u,g)=>{const $=32+l*(g+.5),b=g<r/2;c+=`<line x1="48" y1="192" x2="264" y2="${$}" class="geom-tree-edge"/>`,c+=`<text x="${312/2}" y="${(192+$)/2-13}" class="geom-tree-proba">${u.proba||""}</text>`,c+=`<text x="254" y="${b?$-19:$+29}" class="geom-tree-label" text-anchor="end">${u.label}</text>`;const y=u.branches||[],k=y.length||1,q=54;y.forEach((w,d)=>{const p=$+(d-(k-1)/2)*q;c+=`<line x1="264" y1="${$}" x2="528" y2="${p}" class="geom-tree-edge"/>`,c+=`<text x="${792/2}" y="${($+p)/2-13}" class="geom-tree-proba">${w.proba||""}</text>`,c+=`<text x="544" y="${p+6}" class="geom-tree-label">${w.label}</text>`})}),c+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',s.forEach((u,g)=>{const $=32+l*(g+.5);c+=`<circle cx="264" cy="${$}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${c}</svg>`}function he(e){const[s,r]=e.sets||["A","B"];let l=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${s}</text>
    <text x="336" y="147" class="geom-label">${r}</text>
  `;return e.overlapLabel&&(l+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${l}</svg>`}function be(e){const n=e.labels||[],m=Math.max(n.length,1);let s="";return n.forEach((r,l)=>{const c=42+l*(160/Math.max(m-1,1));s+=`<circle cx="208" cy="224" r="${c}" class="geom-nested-circle"/>`,s+=`<text x="208" y="${224-c+24}" class="geom-label" text-anchor="middle">${r}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${s}</svg>`}function ye(e){const{min:a,max:i}=e,n=32,m=416,s=(m-n)/(i-a||1),r=u=>n+(u-a)*s,l=72;let c=`<line x1="${n}" y1="${l}" x2="${m}" y2="${l}" class="geom-axis"/>`;if(e.highlight){const{from:u,to:g}=e.highlight;c+=`<line x1="${r(u)}" y1="${l}" x2="${r(g)}" y2="${l}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(u=>{const g=r(u.value);c+=`<circle cx="${g}" cy="${l}" r="8" class="${u.filled===!1?"geom-point--open":"geom-point"}"/>`,c+=`<text x="${g}" y="${l+30}" class="geom-label" text-anchor="middle">${u.label??u.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${c}</svg>`}function fe(e){const a=e.bars||[],i=e.maxValue||Math.max(...a.map(c=>c.value),1),n=240,m=32,s=384/Math.max(a.length,1),r=s*.6;let l=`<line x1="32" y1="${n}" x2="416" y2="${n}" class="geom-axis"/>`;return a.forEach((c,u)=>{const g=(n-m)*c.value/i,$=32+u*s+(s-r)/2;l+=`<rect x="${$}" y="${n-g}" width="${r}" height="${g}" class="geom-bar"/>`,l+=`<text x="${$+r/2}" y="${n+26}" class="geom-label" text-anchor="middle">${c.label}</text>`,l+=`<text x="${$+r/2}" y="${n-g-10}" class="geom-label" text-anchor="middle">${c.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${l}</svg>`}function we(e){const m=e.slices||[],s=m.reduce((c,u)=>c+u.value,0)||1;let r=-90,l="";return m.forEach((c,u)=>{const g=c.value/s*360,$=r*Math.PI/180,b=(r+g)*Math.PI/180,y=176+112*Math.cos($),k=160+112*Math.sin($),q=176+112*Math.cos(b),w=160+112*Math.sin(b),d=g>180?1:0;l+=`<path d="M 176 160 L ${y} ${k} A 112 112 0 ${d} 1 ${q} ${w} Z" class="geom-pie-slice geom-pie-slice--${u%5}"/>`;const p=(r+g/2)*Math.PI/180;l+=`<text x="${176+144*Math.cos(p)}" y="${160+144*Math.sin(p)+6}" class="geom-label" text-anchor="middle">${c.label}</text>`,r+=g}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${l}</svg>`}function Ce(e){const{min:a,q1:i,median:n,q3:m,max:s}=e,r=32,c=(416-r)/(s-a||1),u=y=>r+(y-a)*c,g=74,$=48;let b=`
    <line x1="${u(a)}" y1="${g}" x2="${u(i)}" y2="${g}" class="geom-segment"/>
    <line x1="${u(m)}" y1="${g}" x2="${u(s)}" y2="${g}" class="geom-segment"/>
    <line x1="${u(a)}" y1="${g-$/4}" x2="${u(a)}" y2="${g+$/4}" class="geom-segment"/>
    <line x1="${u(s)}" y1="${g-$/4}" x2="${u(s)}" y2="${g+$/4}" class="geom-segment"/>
    <rect x="${u(i)}" y="${g-$/2}" width="${Math.max(u(m)-u(i),1)}" height="${$}" class="geom-boxplot-box"/>
    <line x1="${u(n)}" y1="${g-$/2}" x2="${u(n)}" y2="${g+$/2}" class="geom-boxplot-median"/>
  `;return[a,i,n,m,s].forEach(y=>{b+=`<text x="${u(y)}" y="${g+$/2+29}" class="geom-label" text-anchor="middle">${y}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${b}</svg>`}const ke={cube:`
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
  `},qe={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function Me(e){const o=ke[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||qe[e.shape]||"Solide"}">${o}</svg>`}const Ee={geom:J,tree:ve,venn:he,"nested-sets":be,numberline:ye,bars:fe,pie:we,boxplot:Ce,solid:Me};function Se(e){return(Ee[e.kind]||J)(e)}oe().then(()=>ne());ce(document.getElementById("settings-btn"));const D=document.getElementById("cours-list-view"),h=document.getElementById("cours-reader-view"),U=document.getElementById("cours-grid"),Le=2;let K=!1;H.me().then(({user:e})=>{K=!!e.is_guest}).catch(()=>{});const T=new Set;let W=[],X={};const P=new Map;function Re(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function He(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",o=>{o.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(o=>{o.addEventListener("click",()=>{e.hidden=!0})})}function Ie(){He(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function ee(e){const o=X[e.id]||{},t=Object.values(o),a=t.filter(s=>s.status==="done").length,i=e.n_notions||0,n=i?Math.round(a/i*100):0,m=t.some(s=>s.status==="in_progress");return{doneCount:a,total:i,pct:n,anyInProgress:m}}function N(){U.innerHTML="",W.forEach(e=>{const o=ee(e),t=document.createElement("article");t.className="chapter-card card card--interactive",t.dataset.id=e.id,t.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Re()}</div>
      </div>
      <h3>${j(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${e.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Lecture</span><span>${o.pct}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${o.pct}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${x("bookOpen")} ${e.n_notions} notion${e.n_notions>1?"s":""}</span>
        <span>${x("check")} ${o.doneCount}/${o.total} terminée${o.doneCount>1?"s":""}</span>
      </div>
      <button class="btn btn-primary btn-sm cours-open-btn" type="button">
        ${x("bookOpen")} ${o.anyInProgress?"Continuer":"Ouvrir"}
      </button>
    `,t.querySelector(".cours-open-btn").addEventListener("click",()=>G(e.id)),U.appendChild(t)})}function Ae(e){return e==="seconde"?"cours":`cours_${e}`}async function te(e){if(P.has(e))return P.get(e);const o=e.replace("Chapitre_",""),t=Ae(A()),a=await fetch(`data/${t}/chapitre_${o}.json`);if(!a.ok)throw new Error("Contenu introuvable pour "+e);const i=await a.json();return P.set(e,i),i}function Te(){D.hidden=!1,h.hidden=!0,h.innerHTML=""}function Pe(){D.hidden=!0,h.hidden=!1}async function G(e){if(K&&!T.has(e)&&T.size>=Le){Ie();return}T.add(e),h.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,Pe();const o=await te(e);se(e,o)}function _e(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}function se(e,o){const t=X[e]||{},a=W.find(n=>n.id===e),i=a?ee(a):null;h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${x("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${j(o.title,o.notions.map(n=>n.title))||e.replace(/_/g," ")}</h1>
      ${i?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${i.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${i.doneCount}/${i.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${o.notions.map(n=>{var s,r;const m=((s=t[n.id])==null?void 0:s.status)||"todo";return`
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <h3>${n.title}</h3>
            ${_e(m)}
          </div>
          <div class="cours-notion-meta">
            <span>${(n.exemples||[]).length} exemple${(n.exemples||[]).length>1?"s":""}</span>
            ${(r=t[n.id])!=null&&r.quizTotal?`<span>Quiz : ${t[n.id].quizScore}/${t[n.id].quizTotal}</span>`:""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${x("play")} ${m==="todo"?"Commencer":m==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,I(h),h.querySelector("#cours-back-to-grid").addEventListener("click",()=>{N(),Te()}),h.querySelectorAll(".cours-read-btn").forEach(n=>{n.addEventListener("click",m=>{const s=m.target.closest(".cours-notion-card").dataset.notion,r=o.notions.find(l=>l.id===s);O(e,o,r)})})}const Q=["blue","purple","green","orange","pink"];function ze(e){return`<div class="cours-steps">${(e||[]).map((o,t)=>`
    <div class="cours-step cours-step--${o.couleur||Q[t%Q.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${x(o.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(o.texte)}"></div>
    </div>
  `).join("")}</div>`}function Be(e){const o=(e.calcul||[]).map((t,a,i)=>`
    <div class="cours-calc-row">
      ${t.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${a<i.length-1?`<div class="cours-calc-arrow">${ae.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${x("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${o}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function Ue(e){e.querySelectorAll("[data-text]").forEach(o=>{_(o,decodeURIComponent(o.dataset.text)),o.removeAttribute("data-text")})}function je(e,o){const t=e.notions.findIndex(n=>n.id===o.id),a=t>0?e.notions[t-1]:null,i=t<e.notions.length-1?e.notions[t+1]:null;return!a&&!i?"":`
    <div class="cours-notion-nav">
      ${a?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${a.id}">
        ${x("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${a.title}</span></span>
      </button>`:"<span></span>"}
      ${i?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${i.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${i.title}</span></span>
        ${x("arrowRight")}
      </button>`:""}
    </div>
  `}function O(e,o,t){var l,c,u,g,$,b,y,k,q,w;function a(d){H.saveCourseProgress(e,t.id,d,A()).catch(()=>{})}function i(d,p,f,M){return`
      <div class="cours-box cours-figure-card cours-box--${d}">
        <div class="cours-box-header">${x(p)} <span>${f}</span></div>
        ${M}
      </div>
    `}function n(d){return`<ul class="cours-box-list">${d.map(p=>`<li data-text="${encodeURIComponent(p)}"></li>`).join("")}</ul>`}function m(d){var f,M,S,C,L;const p=[];return d.comprendre&&p.push(i("simple","lightbulb","Ce qu'il faut comprendre",`<div class="cours-box-body" data-text="${encodeURIComponent(d.comprendre)}"></div>`)),(f=d.lecture)!=null&&f.length&&p.push(i("lecture","eye","Comment lire le graphique ?",n(d.lecture))),(M=d.observations)!=null&&M.length&&p.push(i("observations","penSquare","Ce que montre ce graphique",n(d.observations))),(S=d.etapes)!=null&&S.length&&p.push(i("etapes","compass","Comment faire le calcul ?",`
        <div class="cours-figure-etapes">
          ${d.etapes.map((R,Y)=>`
            <div class="cours-figure-etape">
              <span class="cours-figure-etape-num">${Y+1}</span>
              <div>
                <div class="cours-figure-etape-titre">${R.titre||`Étape ${Y+1}`}</div>
                <div class="cours-figure-etape-texte" data-text="${encodeURIComponent(R.texte)}"></div>
              </div>
            </div>
          `).join("")}
        </div>
      `)),d.astuce&&p.push(i("astuce","lightbulb","Astuce NovaMath",`<div class="cours-box-body" data-text="${encodeURIComponent(d.astuce)}"></div>`)),(C=d.pieges)!=null&&C.length&&p.push(i("attention","x","À ne pas confondre",n(d.pieges))),(L=d.aRetenir)!=null&&L.length&&p.push(i("aretenir","star","À retenir",n(d.aRetenir.slice(0,4)))),`
      ${d.resume?`<p class="cours-figure-resume" data-text="${encodeURIComponent(d.resume)}"></p>`:""}
      <div class="cours-figure-cards">${p.join("")}</div>
    `}function s(d){if(!d)return"";const p=d.explication?m(d.explication):d.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(d.alt)}"></p>`:"";return`
      <div class="cours-figure-layout">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap">${Se(d)}</div>
        </div>
        ${p?`<div class="cours-figure-text-col">${p}</div>`:""}
      </div>
    `}h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${x("arrowLeft")} ${j(o.title,o.notions.map(d=>d.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${t.title}</h1>
    <p class="cours-intro-text">${t.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${x("target")}</div>
      <p>${t.objectif||""}</p>
    </div>

    ${t.explicationSimple?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${x("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${x("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${s(t.figure)}

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${x("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}

    ${(l=t.exemplesConcrets)!=null&&l.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${x("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(c=t.reglesImportantes)!=null&&c.length?`
    <div class="cours-section-label">${x("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(d=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(d)}"></div>`).join("")}
    </div>`:""}

    ${(g=(u=t.methode)==null?void 0:u.etapes)!=null&&g.length?`
    <div class="cours-section-label">${x("compass")} ${t.methode.titre||"Méthode"}</div>
    ${ze(t.methode.etapes)}`:""}

    ${($=t.exemples)!=null&&$.length?`
    <div class="cours-section-label">${x("penSquare")} Exemples</div>
    ${t.exemples.map(Be).join("")}`:""}

    ${(b=t.erreursFrequentes)!=null&&b.length?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${x("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${x("lightbulb")} <span>Astuce</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(y=t.aRetenir)!=null&&y.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${x("star")} À retenir</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,5).map(d=>`<li data-text="${encodeURIComponent(d)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(k=t.quizExerciseIds)!=null&&k.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${x("check")} J'ai terminé cette leçon</button>
    </div>

    ${je(o,t)}
  `,Ue(h),I(h),h.querySelector("#cours-back-to-chapter").addEventListener("click",()=>se(e,o)),h.querySelectorAll(".cours-notion-nav-btn").forEach(d=>{d.addEventListener("click",()=>{const p=o.notions.find(f=>f.id===d.dataset.notion);p&&O(e,o,p)})}),a({status:"in_progress"}),(q=t.quizExerciseIds)!=null&&q.length?r(h.querySelector("#cours-quiz-zone")):(w=h.querySelector("#cours-mark-done-btn"))==null||w.addEventListener("click",()=>{a({status:"done"}),h.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${x("check")} Leçon terminée !</span>`});async function r(d){d.innerHTML='<div class="skeleton" style="height:140px;"></div>';let p;try{p=await Promise.all(t.quizExerciseIds.map(C=>H.exercise(C,A()).then(L=>L.exercise)))}catch{d.innerHTML="",a({status:"done"});return}let f=0,M=0;function S(){if(f>=p.length){d.innerHTML=`<div class="card cours-quiz-done">${x("check")} Mini-quiz terminé : <strong>${M}/${p.length}</strong> bonnes réponses.</div>`,I(d.querySelector(".cours-quiz-done")),a({status:"done",quizScore:M,quizTotal:p.length});return}const C=p[f],L=Math.round(f/p.length*100);d.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${x("lightbulb")} Mini-quiz — question ${f+1}/${p.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${L}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${x("check")} J'ai réussi</button>
          </div>
        </div>
      `,I(d.querySelector(".cours-quiz-card")),_(d.querySelector("#cours-quiz-enonce"),C.enonce),d.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const R=d.querySelector("#cours-quiz-answer");R.hidden=!1,_(R,`Réponse : ${C.answer}${C.hint?`
Indice : ${C.hint}`:""}`),d.querySelector("#cours-quiz-reveal").hidden=!0,d.querySelector("#cours-quiz-verdict").hidden=!1}),d.querySelector("#cours-quiz-fail").addEventListener("click",()=>{f+=1,S()}),d.querySelector("#cours-quiz-success").addEventListener("click",()=>{M+=1,f+=1,S()})}S()}}async function De(e,o){await G(e);const t=await te(e),a=t.notions.find(i=>i.id===o);a&&O(e,t,a)}function We(){U.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${x("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function Xe(){const e=A();let o=!0;try{const r=(await re()).find(l=>l.classLevel===e);o=r?r.hasCourses!==!1:!0}catch{o=!0}if(!o){We();return}const[t,a]=await Promise.all([H.chapters(e),H.getCourseProgress(e).catch(()=>({}))]);W=t.chapters_meta||[],X=a||{},N();const i=new URLSearchParams(window.location.search),n=i.get("chapter"),m=i.get("notion");n&&m?De(n,m):n&&G(n)}Xe();ie(e=>{["appearance","*"].includes(e.detail.category)&&(D.hidden||N())});
