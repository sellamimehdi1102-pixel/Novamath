import{a as C}from"./api.D9MhFfTx.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as _}from"./chapterTitleByNotions.B33dvngo.js";/* empty css                 */import"./sidebar.DRZiOWhe.js";import"./command-palette.DL4e3WSo.js";import{i as K,b as ee,l as te}from"./i18n.D7gBkq1-.js";import{b as se}from"./settingsPopup.N73osWXp.js";import{g as S,f as oe,i as x,I as ne}from"./theme.DpqEKRmI.js";import{a as A}from"./mathrender.C9lrWfgK.js";import{f as E}from"./animations.C6RSdq0t.js";const ce=620,ie=460,re=34,ae=120,I=50,N=30,G=30,T=50;function le(e){const[o,t,a,c]=e.viewBox;let n=Math.min((ce-I-N)/a,(ie-G-T)/c);return n=Math.max(re,Math.min(ae,n)),{xmin:o,ymin:t,w:a,h:c,unit:n,width:a*n+I+N,height:c*n+G+T}}function p(e,o,t){const a=I+(o-e.xmin)*e.unit,c=e.height-T-(t-e.ymin)*e.unit;return[a,c]}function M(e,o){if(typeof o=="string"){const t=(e.points||[]).find(a=>a.label===o);return t?[t.x,t.y]:[0,0]}return[o.x,o.y]}function de(e){const{xmin:o,ymin:t,w:a,h:c}=e;let n="";for(let g=Math.ceil(o);g<=o+a;g++){const[s,r]=p(e,g,t),[l,i]=p(e,g,t+c);n+=`<line x1="${s}" y1="${r}" x2="${l}" y2="${i}" class="geom-grid-line"/>`}for(let g=Math.ceil(t);g<=t+c;g++){const[s,r]=p(e,o,g),[l,i]=p(e,o+a,g);n+=`<line x1="${s}" y1="${r}" x2="${l}" y2="${i}" class="geom-grid-line"/>`}return n}function ue(e){const{xmin:o,ymin:t,w:a,h:c}=e,n=a*.05,g=c*.05;let s="";for(let i=Math.ceil(o);i<=o+a;i++){if(i===0||i<o+n||i>o+a-n)continue;const[d,u]=p(e,i,0);s+=`<line x1="${d}" y1="${u-4}" x2="${d}" y2="${u+4}" class="geom-tick"/>`,s+=`<text x="${d}" y="${u+18}" class="geom-tick-label" text-anchor="middle">${i}</text>`}for(let i=Math.ceil(t);i<=t+c;i++){if(i===0||i<t+g||i>t+c-g)continue;const[d,u]=p(e,0,i);s+=`<line x1="${d-4}" y1="${u}" x2="${d+4}" y2="${u}" class="geom-tick"/>`,s+=`<text x="${d-9}" y="${u+4}" class="geom-tick-label" text-anchor="end">${i}</text>`}const[r,l]=p(e,0,0);return s+=`<text x="${r-9}" y="${l+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,s}function ge(e,o){const{xmin:t,ymin:a,w:c,h:n}=e;if(t>0||t+c<0||a>0||a+n<0)return"";const[g,s]=p(e,t,0),[r,l]=p(e,t+c,0),[i,d]=p(e,0,a),[u,$]=p(e,0,a+n);let b=`
    <line x1="${g}" y1="${s}" x2="${r}" y2="${l}" class="geom-axis" marker-end="url(#${o})"/>
    <line x1="${i}" y1="${d}" x2="${u}" y2="${$}" class="geom-axis" marker-end="url(#${o})"/>
    <text x="${r-6}" y="${l-8}" class="geom-axis-label">x</text>
    <text x="${u+10}" y="${$+4}" class="geom-axis-label">y</text>
  `;return b+=ue(e),b}function O(e,o){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${o}"/>
  </marker>`}function V(e){const o=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${o}`,a=`geom-arrow-vector-${o}`,c=le(e);let n="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(n+=de(c)),e.axes&&(n+=ge(c,t)),(e.curves||[]).forEach(s=>{const r=s.points.map(([l,i])=>p(c,l,i).join(",")).join(" ");n+=`<polyline points="${r}" class="geom-curve${s.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(s=>{const r=s.points.map(l=>p(c,...M(e,l)).join(",")).join(" ");n+=`<polygon points="${r}" class="geom-polygon"/>`}),(e.circles||[]).forEach(s=>{const[r,l]=p(c,...M(e,s.center));n+=`<circle cx="${r}" cy="${l}" r="${s.radius*c.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(s=>{const[r,l]=p(c,...M(e,s.center)),i=s.radius*c.unit,d=s.startDeg*Math.PI/180,u=s.endDeg*Math.PI/180,$=r+i*Math.cos(d),b=l-i*Math.sin(d),f=r+i*Math.cos(u),m=l-i*Math.sin(u),h=Math.abs(s.endDeg-s.startDeg)>180?1:0;if(n+=`<path d="M ${r} ${l} L ${$} ${b} A ${i} ${i} 0 ${h} 1 ${f} ${m} Z" class="geom-angle-arc"/>`,s.label){const v=(s.startDeg+s.endDeg)/2*(Math.PI/180),k=r+(i+12)*Math.cos(v),w=l-(i+12)*Math.sin(v);n+=`<text x="${k}" y="${w}" class="geom-label">${s.label}</text>`}}),(e.segments||[]).forEach(s=>{const[r,l]=p(c,...M(e,s.from)),[i,d]=p(c,...M(e,s.to));n+=`<line x1="${r}" y1="${l}" x2="${i}" y2="${d}" class="geom-segment${s.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(s=>{const[r,l]=p(c,...M(e,s.from)),[i,d]=p(c,...M(e,s.to));if(n+=`<line x1="${r}" y1="${l}" x2="${i}" y2="${d}" class="geom-vector" marker-end="url(#${a})"/>`,s.label){const u=(r+i)/2+8,$=(l+d)/2-8;n+=`<text x="${u}" y="${$}" class="geom-label geom-label--vector">${s.label}</text>`}}),(e.points||[]).forEach(s=>{const[r,l]=p(c,s.x,s.y);n+=`<circle cx="${r}" cy="${l}" r="4.5" class="geom-point"/>`,s.label&&(n+=`<text x="${r+9}" y="${l-9}" class="geom-label">${s.label}</text>`),(s.showCoords||e.showCoords)&&(n+=`<text x="${r+9}" y="${l-9+15}" class="geom-label geom-coord-label">(${s.x} ; ${s.y})</text>`)}),(e.texts||[]).forEach(s=>{const[r,l]=p(c,s.x,s.y);n+=`<text x="${r}" y="${l}" class="geom-label">${s.label}</text>`}),(e.angles||[]).forEach(s=>{const[r,l]=p(c,...M(e,s.vertex));n+=`<circle cx="${r}" cy="${l}" r="2.5" class="geom-point"/>`,s.label&&(n+=`<text x="${r+10}" y="${l+4}" class="geom-label">${s.label}</text>`)}),`
    <svg viewBox="0 0 ${c.width} ${c.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${O(t,"geom-arrow-head geom-arrow-head--axis")}
        ${O(a,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${n}
    </svg>
  `}function me(e){const s=e.branches||[],r=s.length||1,l=320/r;let i="";return s.forEach((d,u)=>{const $=32+l*(u+.5),b=u<r/2;i+=`<line x1="48" y1="192" x2="264" y2="${$}" class="geom-tree-edge"/>`,i+=`<text x="${312/2}" y="${(192+$)/2-13}" class="geom-tree-proba">${d.proba||""}</text>`,i+=`<text x="254" y="${b?$-19:$+29}" class="geom-tree-label" text-anchor="end">${d.label}</text>`;const f=d.branches||[],m=f.length||1,h=54;f.forEach((v,k)=>{const w=$+(k-(m-1)/2)*h;i+=`<line x1="264" y1="${$}" x2="528" y2="${w}" class="geom-tree-edge"/>`,i+=`<text x="${792/2}" y="${($+w)/2-13}" class="geom-tree-proba">${v.proba||""}</text>`,i+=`<text x="544" y="${w+6}" class="geom-tree-label">${v.label}</text>`})}),i+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',s.forEach((d,u)=>{const $=32+l*(u+.5);i+=`<circle cx="264" cy="${$}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${i}</svg>`}function $e(e){const[s,r]=e.sets||["A","B"];let l=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${s}</text>
    <text x="336" y="147" class="geom-label">${r}</text>
  `;return e.overlapLabel&&(l+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${l}</svg>`}function xe(e){const n=e.labels||[],g=Math.max(n.length,1);let s="";return n.forEach((r,l)=>{const i=42+l*(160/Math.max(g-1,1));s+=`<circle cx="208" cy="224" r="${i}" class="geom-nested-circle"/>`,s+=`<text x="208" y="${224-i+24}" class="geom-label" text-anchor="middle">${r}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${s}</svg>`}function pe(e){const{min:a,max:c}=e,n=32,g=416,s=(g-n)/(c-a||1),r=d=>n+(d-a)*s,l=72;let i=`<line x1="${n}" y1="${l}" x2="${g}" y2="${l}" class="geom-axis"/>`;if(e.highlight){const{from:d,to:u}=e.highlight;i+=`<line x1="${r(d)}" y1="${l}" x2="${r(u)}" y2="${l}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(d=>{const u=r(d.value);i+=`<circle cx="${u}" cy="${l}" r="8" class="${d.filled===!1?"geom-point--open":"geom-point"}"/>`,i+=`<text x="${u}" y="${l+30}" class="geom-label" text-anchor="middle">${d.label??d.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${i}</svg>`}function ve(e){const a=e.bars||[],c=e.maxValue||Math.max(...a.map(i=>i.value),1),n=240,g=32,s=384/Math.max(a.length,1),r=s*.6;let l=`<line x1="32" y1="${n}" x2="416" y2="${n}" class="geom-axis"/>`;return a.forEach((i,d)=>{const u=(n-g)*i.value/c,$=32+d*s+(s-r)/2;l+=`<rect x="${$}" y="${n-u}" width="${r}" height="${u}" class="geom-bar"/>`,l+=`<text x="${$+r/2}" y="${n+26}" class="geom-label" text-anchor="middle">${i.label}</text>`,l+=`<text x="${$+r/2}" y="${n-u-10}" class="geom-label" text-anchor="middle">${i.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${l}</svg>`}function he(e){const g=e.slices||[],s=g.reduce((i,d)=>i+d.value,0)||1;let r=-90,l="";return g.forEach((i,d)=>{const u=i.value/s*360,$=r*Math.PI/180,b=(r+u)*Math.PI/180,f=176+112*Math.cos($),m=160+112*Math.sin($),h=176+112*Math.cos(b),v=160+112*Math.sin(b),k=u>180?1:0;l+=`<path d="M 176 160 L ${f} ${m} A 112 112 0 ${k} 1 ${h} ${v} Z" class="geom-pie-slice geom-pie-slice--${d%5}"/>`;const w=(r+u/2)*Math.PI/180;l+=`<text x="${176+144*Math.cos(w)}" y="${160+144*Math.sin(w)+6}" class="geom-label" text-anchor="middle">${i.label}</text>`,r+=u}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${l}</svg>`}function ye(e){const{min:a,q1:c,median:n,q3:g,max:s}=e,r=32,i=(416-r)/(s-a||1),d=f=>r+(f-a)*i,u=74,$=48;let b=`
    <line x1="${d(a)}" y1="${u}" x2="${d(c)}" y2="${u}" class="geom-segment"/>
    <line x1="${d(g)}" y1="${u}" x2="${d(s)}" y2="${u}" class="geom-segment"/>
    <line x1="${d(a)}" y1="${u-$/4}" x2="${d(a)}" y2="${u+$/4}" class="geom-segment"/>
    <line x1="${d(s)}" y1="${u-$/4}" x2="${d(s)}" y2="${u+$/4}" class="geom-segment"/>
    <rect x="${d(c)}" y="${u-$/2}" width="${Math.max(d(g)-d(c),1)}" height="${$}" class="geom-boxplot-box"/>
    <line x1="${d(n)}" y1="${u-$/2}" x2="${d(n)}" y2="${u+$/2}" class="geom-boxplot-median"/>
  `;return[a,c,n,g,s].forEach(f=>{b+=`<text x="${d(f)}" y="${u+$/2+29}" class="geom-label" text-anchor="middle">${f}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${b}</svg>`}const be={cube:`
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
  `},fe={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function we(e){const o=be[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||fe[e.shape]||"Solide"}">${o}</svg>`}const ke={geom:V,tree:me,venn:$e,"nested-sets":xe,numberline:pe,bars:ve,pie:he,boxplot:ye,solid:we};function Me(e){return(ke[e.kind]||V)(e)}K().then(()=>ee());se(document.getElementById("settings-btn"));const z=document.getElementById("cours-list-view"),y=document.getElementById("cours-reader-view"),P=document.getElementById("cours-grid"),qe=2;let F=!1;C.me().then(({user:e})=>{F=!!e.is_guest}).catch(()=>{});const H=new Set;let B=[],D={};const R=new Map;function Ce(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Ee(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",o=>{o.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(o=>{o.addEventListener("click",()=>{e.hidden=!0})})}function Se(){Ee(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function Z(e){const o=D[e.id]||{},t=Object.values(o),a=t.filter(s=>s.status==="done").length,c=e.n_notions||0,n=c?Math.round(a/c*100):0,g=t.some(s=>s.status==="in_progress");return{doneCount:a,total:c,pct:n,anyInProgress:g}}function j(){P.innerHTML="",B.forEach(e=>{const o=Z(e),t=document.createElement("article");t.className="chapter-card card card--interactive",t.dataset.id=e.id,t.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ce()}</div>
      </div>
      <h3>${_(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
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
    `,t.querySelector(".cours-open-btn").addEventListener("click",()=>U(e.id)),P.appendChild(t)})}function Le(e){return e==="seconde"?"cours":`cours_${e}`}async function Q(e){if(R.has(e))return R.get(e);const o=e.replace("Chapitre_",""),t=Le(S()),a=await fetch(`data/${t}/chapitre_${o}.json`);if(!a.ok)throw new Error("Contenu introuvable pour "+e);const c=await a.json();return R.set(e,c),c}function He(){z.hidden=!1,y.hidden=!0,y.innerHTML=""}function Re(){z.hidden=!0,y.hidden=!1}async function U(e){if(F&&!H.has(e)&&H.size>=qe){Se();return}H.add(e),y.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,Re();const o=await Q(e);J(e,o)}function Ae(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}function J(e,o){const t=D[e]||{},a=B.find(n=>n.id===e),c=a?Z(a):null;y.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${x("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${_(o.title,o.notions.map(n=>n.title))||e.replace(/_/g," ")}</h1>
      ${c?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${c.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${c.doneCount}/${c.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${o.notions.map(n=>{var s,r;const g=((s=t[n.id])==null?void 0:s.status)||"todo";return`
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <h3>${n.title}</h3>
            ${Ae(g)}
          </div>
          <div class="cours-notion-meta">
            <span>${(n.exemples||[]).length} exemple${(n.exemples||[]).length>1?"s":""}</span>
            ${(r=t[n.id])!=null&&r.quizTotal?`<span>Quiz : ${t[n.id].quizScore}/${t[n.id].quizTotal}</span>`:""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${x("play")} ${g==="todo"?"Commencer":g==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,E(y),y.querySelector("#cours-back-to-grid").addEventListener("click",()=>{j(),He()}),y.querySelectorAll(".cours-read-btn").forEach(n=>{n.addEventListener("click",g=>{const s=g.target.closest(".cours-notion-card").dataset.notion,r=o.notions.find(l=>l.id===s);W(e,o,r)})})}const Y=["blue","purple","green","orange","pink"];function Ie(e){return`<div class="cours-steps">${(e||[]).map((o,t)=>`
    <div class="cours-step cours-step--${o.couleur||Y[t%Y.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${x(o.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(o.texte)}"></div>
    </div>
  `).join("")}</div>`}function Te(e){const o=(e.calcul||[]).map((t,a,c)=>`
    <div class="cours-calc-row">
      ${t.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${a<c.length-1?`<div class="cours-calc-arrow">${ne.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${x("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${o}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function Pe(e){e.querySelectorAll("[data-text]").forEach(o=>{A(o,decodeURIComponent(o.dataset.text)),o.removeAttribute("data-text")})}function _e(e,o){const t=e.notions.findIndex(n=>n.id===o.id),a=t>0?e.notions[t-1]:null,c=t<e.notions.length-1?e.notions[t+1]:null;return!a&&!c?"":`
    <div class="cours-notion-nav">
      ${a?`
      <button type="button" class="cours-notion-nav-btn" data-notion="${a.id}">
        ${x("arrowLeft")}
        <span><span class="cours-notion-nav-eyebrow">Notion précédente</span><span class="cours-notion-nav-title">${a.title}</span></span>
      </button>`:"<span></span>"}
      ${c?`
      <button type="button" class="cours-notion-nav-btn cours-notion-nav-btn--next" data-notion="${c.id}">
        <span><span class="cours-notion-nav-eyebrow">Notion suivante</span><span class="cours-notion-nav-title">${c.title}</span></span>
        ${x("arrowRight")}
      </button>`:""}
    </div>
  `}function W(e,o,t){var g,s,r,l,i,d,u,$,b,f;function a(m){C.saveCourseProgress(e,t.id,m,S()).catch(()=>{})}function c(m){var k;if(!m)return"";const v=((k=m.details)==null?void 0:k.length)?`
        <div class="cours-figure-details-title">${x("compass")} Sur ce graphique</div>
        <ul class="cours-figure-details-list">
          ${m.details.map(w=>`<li data-text="${encodeURIComponent(w)}"></li>`).join("")}
        </ul>
      `:m.alt?`<p class="cours-figure-caption-text" data-text="${encodeURIComponent(m.alt)}"></p>`:"";return`
      <div class="cours-figure-layout">
        <div class="cours-figure-col">
          <div class="cours-figure-wrap">${Me(m)}</div>
        </div>
        ${v?`<div class="cours-figure-text-col">${v}</div>`:""}
      </div>
    `}y.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${x("arrowLeft")} ${_(o.title,o.notions.map(m=>m.title))||e.replace(/_/g," ")}</button>
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

    ${c(t.figure)}

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${x("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}

    ${(g=t.exemplesConcrets)!=null&&g.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${x("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map(m=>`<li data-text="${encodeURIComponent(m)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(s=t.reglesImportantes)!=null&&s.length?`
    <div class="cours-section-label">${x("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map(m=>`<div class="card cours-regle-card" data-text="${encodeURIComponent(m)}"></div>`).join("")}
    </div>`:""}

    ${(l=(r=t.methode)==null?void 0:r.etapes)!=null&&l.length?`
    <div class="cours-section-label">${x("compass")} ${t.methode.titre||"Méthode"}</div>
    ${Ie(t.methode.etapes)}`:""}

    ${(i=t.exemples)!=null&&i.length?`
    <div class="cours-section-label">${x("penSquare")} Exemples</div>
    ${t.exemples.map(Te).join("")}`:""}

    ${(d=t.erreursFrequentes)!=null&&d.length?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${x("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map(m=>`<li data-text="${encodeURIComponent(m)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${x("lightbulb")} <span>Astuce</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(u=t.aRetenir)!=null&&u.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${x("star")} À retenir</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,5).map(m=>`<li data-text="${encodeURIComponent(m)}"></li>`).join("")}
      </ul>
    </div>`:""}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${($=t.quizExerciseIds)!=null&&$.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${x("check")} J'ai terminé cette leçon</button>
    </div>

    ${_e(o,t)}
  `,Pe(y),E(y),y.querySelector("#cours-back-to-chapter").addEventListener("click",()=>J(e,o)),y.querySelectorAll(".cours-notion-nav-btn").forEach(m=>{m.addEventListener("click",()=>{const h=o.notions.find(v=>v.id===m.dataset.notion);h&&W(e,o,h)})}),a({status:"in_progress"}),(b=t.quizExerciseIds)!=null&&b.length?n(y.querySelector("#cours-quiz-zone")):(f=y.querySelector("#cours-mark-done-btn"))==null||f.addEventListener("click",()=>{a({status:"done"}),y.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${x("check")} Leçon terminée !</span>`});async function n(m){m.innerHTML='<div class="skeleton" style="height:140px;"></div>';let h;try{h=await Promise.all(t.quizExerciseIds.map(q=>C.exercise(q,S()).then(L=>L.exercise)))}catch{m.innerHTML="",a({status:"done"});return}let v=0,k=0;function w(){if(v>=h.length){m.innerHTML=`<div class="card cours-quiz-done">${x("check")} Mini-quiz terminé : <strong>${k}/${h.length}</strong> bonnes réponses.</div>`,E(m.querySelector(".cours-quiz-done")),a({status:"done",quizScore:k,quizTotal:h.length});return}const q=h[v],L=Math.round(v/h.length*100);m.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${x("lightbulb")} Mini-quiz — question ${v+1}/${h.length}</span>
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
      `,E(m.querySelector(".cours-quiz-card")),A(m.querySelector("#cours-quiz-enonce"),q.enonce),m.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const X=m.querySelector("#cours-quiz-answer");X.hidden=!1,A(X,`Réponse : ${q.answer}${q.hint?`
Indice : ${q.hint}`:""}`),m.querySelector("#cours-quiz-reveal").hidden=!0,m.querySelector("#cours-quiz-verdict").hidden=!1}),m.querySelector("#cours-quiz-fail").addEventListener("click",()=>{v+=1,w()}),m.querySelector("#cours-quiz-success").addEventListener("click",()=>{k+=1,v+=1,w()})}w()}}async function ze(e,o){await U(e);const t=await Q(e),a=t.notions.find(c=>c.id===o);a&&W(e,t,a)}function Be(){P.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${x("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function De(){const e=S();let o=!0;try{const r=(await oe()).find(l=>l.classLevel===e);o=r?r.hasCourses!==!1:!0}catch{o=!0}if(!o){Be();return}const[t,a]=await Promise.all([C.chapters(e),C.getCourseProgress(e).catch(()=>({}))]);B=t.chapters_meta||[],D=a||{},j();const c=new URLSearchParams(window.location.search),n=c.get("chapter"),g=c.get("notion");n&&g?ze(n,g):n&&U(n)}De();te(e=>{["appearance","*"].includes(e.detail.category)&&(z.hidden||j())});
