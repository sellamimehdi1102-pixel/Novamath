import{a as E}from"./api.D9MhFfTx.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as z}from"./chapterTitleByNotions.B33dvngo.js";/* empty css                 */import"./sidebar.CPsBZKLi.js";import"./command-palette.BPLLTaPv.js";import{i as ee,b as te,l as se}from"./i18n.B3NAIOE2.js";import{b as oe}from"./settingsPopup.CFfwvaaF.js";import{g as S,f as ne,i as x,I as ce}from"./theme.DpqEKRmI.js";import{a as I}from"./mathrender.C9lrWfgK.js";import{f as C}from"./animations.C6RSdq0t.js";const re=620,ie=460,ae=34,le=120,T=50,G=30,O=30,P=50;function de(e){const[o,t,a,c]=e.viewBox;let n=Math.min((re-T-G)/a,(ie-O-P)/c);return n=Math.max(ae,Math.min(le,n)),{xmin:o,ymin:t,w:a,h:c,unit:n,width:a*n+T+G,height:c*n+O+P}}function p(e,o,t){const a=T+(o-e.xmin)*e.unit,c=e.height-P-(t-e.ymin)*e.unit;return[a,c]}function M(e,o){if(typeof o=="string"){const t=(e.points||[]).find(a=>a.label===o);return t?[t.x,t.y]:[0,0]}return[o.x,o.y]}function ue(e){const{xmin:o,ymin:t,w:a,h:c}=e;let n="";for(let g=Math.ceil(o);g<=o+a;g++){const[s,i]=p(e,g,t),[l,r]=p(e,g,t+c);n+=`<line x1="${s}" y1="${i}" x2="${l}" y2="${r}" class="geom-grid-line"/>`}for(let g=Math.ceil(t);g<=t+c;g++){const[s,i]=p(e,o,g),[l,r]=p(e,o+a,g);n+=`<line x1="${s}" y1="${i}" x2="${l}" y2="${r}" class="geom-grid-line"/>`}return n}function ge(e){const{xmin:o,ymin:t,w:a,h:c}=e,n=a*.05,g=c*.05;let s="";for(let r=Math.ceil(o);r<=o+a;r++){if(r===0||r<o+n||r>o+a-n)continue;const[d,u]=p(e,r,0);s+=`<line x1="${d}" y1="${u-4}" x2="${d}" y2="${u+4}" class="geom-tick"/>`,s+=`<text x="${d}" y="${u+18}" class="geom-tick-label" text-anchor="middle">${r}</text>`}for(let r=Math.ceil(t);r<=t+c;r++){if(r===0||r<t+g||r>t+c-g)continue;const[d,u]=p(e,0,r);s+=`<line x1="${d-4}" y1="${u}" x2="${d+4}" y2="${u}" class="geom-tick"/>`,s+=`<text x="${d-9}" y="${u+4}" class="geom-tick-label" text-anchor="end">${r}</text>`}const[i,l]=p(e,0,0);return s+=`<text x="${i-9}" y="${l+16}" class="geom-tick-label geom-origin-label" text-anchor="end">O</text>`,s}function me(e,o){const{xmin:t,ymin:a,w:c,h:n}=e;if(t>0||t+c<0||a>0||a+n<0)return"";const[g,s]=p(e,t,0),[i,l]=p(e,t+c,0),[r,d]=p(e,0,a),[u,m]=p(e,0,a+n);let y=`
    <line x1="${g}" y1="${s}" x2="${i}" y2="${l}" class="geom-axis" marker-end="url(#${o})"/>
    <line x1="${r}" y1="${d}" x2="${u}" y2="${m}" class="geom-axis" marker-end="url(#${o})"/>
    <text x="${i-6}" y="${l-8}" class="geom-axis-label">x</text>
    <text x="${u+10}" y="${m+4}" class="geom-axis-label">y</text>
  `;return y+=ge(e),y}function Y(e,o){return`<marker id="${e}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 Z" class="${o}"/>
  </marker>`}function F(e){const o=Math.random().toString(36).slice(2,8),t=`geom-arrow-axis-${o}`,a=`geom-arrow-vector-${o}`,c=de(e);let n="";return(e.grid===!0||e.grid!==!1&&e.axes)&&(n+=ue(c)),e.axes&&(n+=me(c,t)),(e.curves||[]).forEach(s=>{const i=s.points.map(([l,r])=>p(c,l,r).join(",")).join(" ");n+=`<polyline points="${i}" class="geom-curve${s.dashed?" geom-curve--dashed":""}" fill="none"/>`}),(e.polygons||[]).forEach(s=>{const i=s.points.map(l=>p(c,...M(e,l)).join(",")).join(" ");n+=`<polygon points="${i}" class="geom-polygon"/>`}),(e.circles||[]).forEach(s=>{const[i,l]=p(c,...M(e,s.center));n+=`<circle cx="${i}" cy="${l}" r="${s.radius*c.unit}" class="geom-circle"/>`}),(e.arcs||[]).forEach(s=>{const[i,l]=p(c,...M(e,s.center)),r=s.radius*c.unit,d=s.startDeg*Math.PI/180,u=s.endDeg*Math.PI/180,m=i+r*Math.cos(d),y=l-r*Math.sin(d),b=i+r*Math.cos(u),k=l-r*Math.sin(u),$=Math.abs(s.endDeg-s.startDeg)>180?1:0;if(n+=`<path d="M ${i} ${l} L ${m} ${y} A ${r} ${r} 0 ${$} 1 ${b} ${k} Z" class="geom-angle-arc"/>`,s.label){const v=(s.startDeg+s.endDeg)/2*(Math.PI/180),f=i+(r+12)*Math.cos(v),w=l-(r+12)*Math.sin(v);n+=`<text x="${f}" y="${w}" class="geom-label">${s.label}</text>`}}),(e.segments||[]).forEach(s=>{const[i,l]=p(c,...M(e,s.from)),[r,d]=p(c,...M(e,s.to));n+=`<line x1="${i}" y1="${l}" x2="${r}" y2="${d}" class="geom-segment${s.dashed?" geom-segment--dashed":""}"/>`}),(e.vectors||[]).forEach(s=>{const[i,l]=p(c,...M(e,s.from)),[r,d]=p(c,...M(e,s.to));if(n+=`<line x1="${i}" y1="${l}" x2="${r}" y2="${d}" class="geom-vector" marker-end="url(#${a})"/>`,s.label){const u=(i+r)/2+8,m=(l+d)/2-8;n+=`<text x="${u}" y="${m}" class="geom-label geom-label--vector">${s.label}</text>`}}),(e.points||[]).forEach(s=>{const[i,l]=p(c,s.x,s.y);n+=`<circle cx="${i}" cy="${l}" r="4.5" class="geom-point"/>`,s.label&&(n+=`<text x="${i+9}" y="${l-9}" class="geom-label">${s.label}</text>`),(s.showCoords||e.showCoords)&&(n+=`<text x="${i+9}" y="${l-9+15}" class="geom-label geom-coord-label">(${s.x} ; ${s.y})</text>`)}),(e.texts||[]).forEach(s=>{const[i,l]=p(c,s.x,s.y);n+=`<text x="${i}" y="${l}" class="geom-label">${s.label}</text>`}),(e.angles||[]).forEach(s=>{const[i,l]=p(c,...M(e,s.vertex));n+=`<circle cx="${i}" cy="${l}" r="2.5" class="geom-point"/>`,s.label&&(n+=`<text x="${i+10}" y="${l+4}" class="geom-label">${s.label}</text>`)}),`
    <svg viewBox="0 0 ${c.width} ${c.height}" class="geom-figure geom-figure--geom" role="img" aria-label="${e.alt||"Figure géométrique"}">
      <defs>
        ${Y(t,"geom-arrow-head geom-arrow-head--axis")}
        ${Y(a,"geom-arrow-head geom-arrow-head--vector")}
      </defs>
      ${n}
    </svg>
  `}function $e(e){const s=e.branches||[],i=s.length||1,l=320/i;let r="";return s.forEach((d,u)=>{const m=32+l*(u+.5),y=u<i/2;r+=`<line x1="48" y1="192" x2="264" y2="${m}" class="geom-tree-edge"/>`,r+=`<text x="${312/2}" y="${(192+m)/2-13}" class="geom-tree-proba">${d.proba||""}</text>`,r+=`<text x="254" y="${y?m-19:m+29}" class="geom-tree-label" text-anchor="end">${d.label}</text>`;const b=d.branches||[],k=b.length||1,$=54;b.forEach((v,f)=>{const w=m+(f-(k-1)/2)*$;r+=`<line x1="264" y1="${m}" x2="528" y2="${w}" class="geom-tree-edge"/>`,r+=`<text x="${792/2}" y="${(m+w)/2-13}" class="geom-tree-proba">${v.proba||""}</text>`,r+=`<text x="544" y="${w+6}" class="geom-tree-label">${v.label}</text>`})}),r+='<circle cx="48" cy="192" r="6" class="geom-tree-node"/>',s.forEach((d,u)=>{const m=32+l*(u+.5);r+=`<circle cx="264" cy="${m}" r="6" class="geom-tree-node"/>`}),`<svg viewBox="0 0 672 384" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Arbre de probabilités"}">${r}</svg>`}function xe(e){const[s,i]=e.sets||["A","B"];let l=`
    <circle cx="173" cy="147" r="109" class="geom-venn-circle geom-venn-circle--a"/>
    <circle cx="269" cy="147" r="109" class="geom-venn-circle geom-venn-circle--b"/>
    <text x="106" y="147" class="geom-label">${s}</text>
    <text x="336" y="147" class="geom-label">${i}</text>
  `;return e.overlapLabel&&(l+=`<text x="${442/2}" y="153" class="geom-label geom-label--overlap" text-anchor="middle">${e.overlapLabel}</text>`),`<svg viewBox="0 0 416 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme de Venn"}">${l}</svg>`}function pe(e){const n=e.labels||[],g=Math.max(n.length,1);let s="";return n.forEach((i,l)=>{const r=42+l*(160/Math.max(g-1,1));s+=`<circle cx="208" cy="224" r="${r}" class="geom-nested-circle"/>`,s+=`<text x="208" y="${224-r+24}" class="geom-label" text-anchor="middle">${i}</text>`}),`<svg viewBox="0 0 416 416" class="geom-figure" role="img" aria-label="${e.alt||"Ensembles emboîtés"}">${s}</svg>`}function ve(e){const{min:a,max:c}=e,n=32,g=416,s=(g-n)/(c-a||1),i=d=>n+(d-a)*s,l=72;let r=`<line x1="${n}" y1="${l}" x2="${g}" y2="${l}" class="geom-axis"/>`;if(e.highlight){const{from:d,to:u}=e.highlight;r+=`<line x1="${i(d)}" y1="${l}" x2="${i(u)}" y2="${l}" class="geom-numberline-highlight"/>`}return(e.marks||[]).forEach(d=>{const u=i(d.value);r+=`<circle cx="${u}" cy="${l}" r="8" class="${d.filled===!1?"geom-point--open":"geom-point"}"/>`,r+=`<text x="${u}" y="${l+30}" class="geom-label" text-anchor="middle">${d.label??d.value}</text>`}),`<svg viewBox="0 0 448 144" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Droite graduée"}">${r}</svg>`}function he(e){const a=e.bars||[],c=e.maxValue||Math.max(...a.map(r=>r.value),1),n=240,g=32,s=384/Math.max(a.length,1),i=s*.6;let l=`<line x1="32" y1="${n}" x2="416" y2="${n}" class="geom-axis"/>`;return a.forEach((r,d)=>{const u=(n-g)*r.value/c,m=32+d*s+(s-i)/2;l+=`<rect x="${m}" y="${n-u}" width="${i}" height="${u}" class="geom-bar"/>`,l+=`<text x="${m+i/2}" y="${n+26}" class="geom-label" text-anchor="middle">${r.label}</text>`,l+=`<text x="${m+i/2}" y="${n-u-10}" class="geom-label" text-anchor="middle">${r.value}</text>`}),`<svg viewBox="0 0 448 288" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Diagramme en bâtons"}">${l}</svg>`}function ye(e){const g=e.slices||[],s=g.reduce((r,d)=>r+d.value,0)||1;let i=-90,l="";return g.forEach((r,d)=>{const u=r.value/s*360,m=i*Math.PI/180,y=(i+u)*Math.PI/180,b=176+112*Math.cos(m),k=160+112*Math.sin(m),$=176+112*Math.cos(y),v=160+112*Math.sin(y),f=u>180?1:0;l+=`<path d="M 176 160 L ${b} ${k} A 112 112 0 ${f} 1 ${$} ${v} Z" class="geom-pie-slice geom-pie-slice--${d%5}"/>`;const w=(i+u/2)*Math.PI/180;l+=`<text x="${176+144*Math.cos(w)}" y="${160+144*Math.sin(w)+6}" class="geom-label" text-anchor="middle">${r.label}</text>`,i+=u}),`<svg viewBox="0 0 384 352" class="geom-figure" role="img" aria-label="${e.alt||"Diagramme circulaire"}">${l}</svg>`}function be(e){const{min:a,q1:c,median:n,q3:g,max:s}=e,i=32,r=(416-i)/(s-a||1),d=b=>i+(b-a)*r,u=74,m=48;let y=`
    <line x1="${d(a)}" y1="${u}" x2="${d(c)}" y2="${u}" class="geom-segment"/>
    <line x1="${d(g)}" y1="${u}" x2="${d(s)}" y2="${u}" class="geom-segment"/>
    <line x1="${d(a)}" y1="${u-m/4}" x2="${d(a)}" y2="${u+m/4}" class="geom-segment"/>
    <line x1="${d(s)}" y1="${u-m/4}" x2="${d(s)}" y2="${u+m/4}" class="geom-segment"/>
    <rect x="${d(c)}" y="${u-m/2}" width="${Math.max(d(g)-d(c),1)}" height="${m}" class="geom-boxplot-box"/>
    <line x1="${d(n)}" y1="${u-m/2}" x2="${d(n)}" y2="${u+m/2}" class="geom-boxplot-median"/>
  `;return[a,c,n,g,s].forEach(b=>{y+=`<text x="${d(b)}" y="${u+m/2+29}" class="geom-label" text-anchor="middle">${b}</text>`}),`<svg viewBox="0 0 448 160" class="geom-figure geom-figure--wide" role="img" aria-label="${e.alt||"Boîte à moustaches"}">${y}</svg>`}const fe={cube:`
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
  `},we={cube:"Cube",pave:"Pavé droit",cylindre:"Cylindre",cone:"Cône",sphere:"Sphère",pyramide:"Pyramide",prisme:"Prisme"};function ke(e){const o=fe[e.shape]||"";return`<svg viewBox="0 0 320 320" class="geom-figure" role="img" aria-label="${e.alt||we[e.shape]||"Solide"}">${o}</svg>`}const Me={geom:F,tree:$e,venn:xe,"nested-sets":pe,numberline:ve,bars:he,pie:ye,boxplot:be,solid:ke};function qe(e){return(Me[e.kind]||F)(e)}ee().then(()=>te());oe(document.getElementById("settings-btn"));const B=document.getElementById("cours-list-view"),h=document.getElementById("cours-reader-view"),_=document.getElementById("cours-grid"),Ee=2;let Z=!1;E.me().then(({user:e})=>{Z=!!e.is_guest}).catch(()=>{});const A=new Set;let j=[],D={};const R=new Map;function Ce(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg>'}function Se(){if(document.getElementById("guest-cours-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-cours-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les cours</h3>
      <p>Créez gratuitement votre compte NovaMath pour accéder à tous les cours et sauvegarder votre progression de lecture.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-cours-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",o=>{o.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-cours-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(o=>{o.addEventListener("click",()=>{e.hidden=!0})})}function Le(){Se(),document.getElementById("guest-cours-modal-overlay").hidden=!1}function Q(e){const o=D[e.id]||{},t=Object.values(o),a=t.filter(s=>s.status==="done").length,c=e.n_notions||0,n=c?Math.round(a/c*100):0,g=t.some(s=>s.status==="in_progress");return{doneCount:a,total:c,pct:n,anyInProgress:g}}function U(){_.innerHTML="",j.forEach(e=>{const o=Q(e),t=document.createElement("article");t.className="chapter-card card card--interactive",t.dataset.id=e.id,t.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${Ce()}</div>
      </div>
      <h3>${z(e.title,e.notions_cours)||e.id.replace(/_/g," ")}</h3>
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
    `,t.querySelector(".cours-open-btn").addEventListener("click",()=>W(e.id)),_.appendChild(t)})}function He(e){return e==="seconde"?"cours":`cours_${e}`}async function J(e){if(R.has(e))return R.get(e);const o=e.replace("Chapitre_",""),t=He(S()),a=await fetch(`data/${t}/chapitre_${o}.json`);if(!a.ok)throw new Error("Contenu introuvable pour "+e);const c=await a.json();return R.set(e,c),c}function Ae(){B.hidden=!1,h.hidden=!0,h.innerHTML=""}function Re(){B.hidden=!0,h.hidden=!1}async function W(e){if(Z&&!A.has(e)&&A.size>=Ee){Le();return}A.add(e),h.innerHTML=`
    <div class="cours-skeleton-card" style="margin-bottom:24px;">
      <span class="skeleton" style="height:14px;width:120px;"></span>
      <span class="skeleton" style="height:26px;width:55%;"></span>
      <span class="skeleton" style="height:8px;width:100%;"></span>
    </div>
    <div class="cours-notions-list">
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
      <div class="cours-skeleton-card"><span class="skeleton" style="height:16px;width:70%;"></span><span class="skeleton" style="height:10px;width:90%;"></span><span class="skeleton" style="height:32px;width:110px;border-radius:999px;"></span></div>
    </div>
  `,Re();const o=await J(e);K(e,o)}function Ie(e){return e==="done"?'<span class="badge badge--success">Terminée</span>':e==="in_progress"?'<span class="badge badge--warning">En cours</span>':'<span class="badge badge--neutral">À lire</span>'}function K(e,o){const t=D[e]||{},a=j.find(n=>n.id===e),c=a?Q(a):null;h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-grid" type="button">${x("arrowLeft")} Tous les cours</button>
    </div>
    <div class="cours-chapter-hero">
      <div class="chapter-id">${e.replace("_"," ")}</div>
      <h1>${z(o.title,o.notions.map(n=>n.title))||e.replace(/_/g," ")}</h1>
      ${c?`
      <div class="cours-chapter-hero-progress">
        <div class="progress-track"><div class="progress-fill" style="width:${c.pct}%"></div></div>
        <span class="cours-chapter-hero-progress-label">${c.doneCount}/${c.total} notions terminées</span>
      </div>`:""}
    </div>
    <div class="cours-notions-list">
      ${o.notions.map(n=>{var s,i;const g=((s=t[n.id])==null?void 0:s.status)||"todo";return`
        <div class="card cours-notion-card" data-notion="${n.id}">
          <div class="cours-notion-top">
            <h3>${n.title}</h3>
            ${Ie(g)}
          </div>
          <div class="cours-notion-meta">
            <span>${(n.exemples||[]).length} exemple${(n.exemples||[]).length>1?"s":""}</span>
            ${(i=t[n.id])!=null&&i.quizTotal?`<span>Quiz : ${t[n.id].quizScore}/${t[n.id].quizTotal}</span>`:""}
          </div>
          <button class="btn btn-secondary btn-sm cours-read-btn" type="button">
            ${x("play")} ${g==="todo"?"Commencer":g==="done"?"Relire":"Continuer"}
          </button>
        </div>`}).join("")}
    </div>
  `,C(h),h.querySelector("#cours-back-to-grid").addEventListener("click",()=>{U(),Ae()}),h.querySelectorAll(".cours-read-btn").forEach(n=>{n.addEventListener("click",g=>{const s=g.target.closest(".cours-notion-card").dataset.notion,i=o.notions.find(l=>l.id===s);X(e,o,i)})})}const V=["blue","purple","green","orange","pink"];function Te(e){return`<div class="cours-steps">${(e||[]).map((o,t)=>`
    <div class="cours-step cours-step--${o.couleur||V[t%V.length]}">
      <div class="cours-step-num">
        <span class="cours-step-icon">${x(o.icone||"check")}</span>
        <span class="cours-step-index">${t+1}</span>
      </div>
      <div class="cours-step-text" data-text="${encodeURIComponent(o.texte)}"></div>
    </div>
  `).join("")}</div>`}function Pe(e){const o=(e.calcul||[]).map((t,a,c)=>`
    <div class="cours-calc-row">
      ${t.expr?`<div class="cours-calc-expr" data-text="${encodeURIComponent(`$${t.expr}$`)}"></div>`:""}
      <div class="cours-calc-texte" data-text="${encodeURIComponent(t.texte)}"></div>
    </div>
    ${a<c.length-1?`<div class="cours-calc-arrow">${ce.arrowRight}</div>`:""}
  `).join("");return`
    <div class="card cours-exemple-card">
      <div class="cours-exemple-title">${x("penSquare")} ${e.titre||"Exemple"}</div>
      <div class="cours-exemple-enonce" data-text="${encodeURIComponent(e.enonce)}"></div>
      ${e.explication?`<div class="cours-exemple-explication" data-text="${encodeURIComponent(e.explication)}"></div>`:""}
      <div class="cours-calc-block">${o}</div>
      <div class="cours-exemple-reponse" data-text="${encodeURIComponent("Réponse : "+e.reponse)}"></div>
      ${e.conclusion?`<div class="cours-exemple-conclusion" data-text="${encodeURIComponent(e.conclusion)}"></div>`:""}
    </div>
  `}function _e(e){e.querySelectorAll("[data-text]").forEach(o=>{I(o,decodeURIComponent(o.dataset.text)),o.removeAttribute("data-text")})}function ze(e,o){const t=e.notions.findIndex(n=>n.id===o.id),a=t>0?e.notions[t-1]:null,c=t<e.notions.length-1?e.notions[t+1]:null;return!a&&!c?"":`
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
  `}function X(e,o,t){var s,i,l,r,d,u,m,y,b,k;function a($){E.saveCourseProgress(e,t.id,$,S()).catch(()=>{})}const c=`
    ${t.explicationSimple?`
    <div class="cours-box cours-box--simple">
      <div class="cours-box-header">${x("lightbulb")} <span>Pour bien comprendre</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.explicationSimple)}"></div>
    </div>`:""}

    <div class="cours-box cours-box--definition">
      <div class="cours-box-header">${x("bookOpen")} <span>Définition</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.definition||"")}"></div>
    </div>

    ${t.intuition?`
    <div class="cours-box cours-box--intuition">
      <div class="cours-box-header">${x("target")} <span>À retenir</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.intuition)}"></div>
    </div>`:""}

    ${(s=t.exemplesConcrets)!=null&&s.length?`
    <div class="cours-box cours-box--concret">
      <div class="cours-box-header">${x("compass")} <span>Dans la vraie vie</span></div>
      <ul class="cours-concrets-list">
        ${t.exemplesConcrets.map($=>`<li data-text="${encodeURIComponent($)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${(i=t.reglesImportantes)!=null&&i.length?`
    <div class="cours-section-label">${x("scale")} Règles importantes</div>
    <div class="cours-regles-grid">
      ${t.reglesImportantes.map($=>`<div class="card cours-regle-card" data-text="${encodeURIComponent($)}"></div>`).join("")}
    </div>`:""}

    ${(r=(l=t.methode)==null?void 0:l.etapes)!=null&&r.length?`
    <div class="cours-section-label">${x("compass")} ${t.methode.titre||"Méthode"}</div>
    ${Te(t.methode.etapes)}`:""}

    ${(d=t.exemples)!=null&&d.length?`
    <div class="cours-section-label">${x("penSquare")} Exemples</div>
    ${t.exemples.map(Pe).join("")}`:""}

    ${(u=t.erreursFrequentes)!=null&&u.length?`
    <div class="cours-box cours-box--attention">
      <div class="cours-box-header">${x("x")} <span>Erreurs fréquentes</span></div>
      <ul class="cours-erreurs-list">
        ${t.erreursFrequentes.map($=>`<li data-text="${encodeURIComponent($)}"></li>`).join("")}
      </ul>
    </div>`:""}

    ${t.astuce?`
    <div class="cours-box cours-box--astuce">
      <div class="cours-box-header">${x("lightbulb")} <span>Astuce</span></div>
      <div class="cours-box-body" data-text="${encodeURIComponent(t.astuce)}"></div>
    </div>`:""}

    ${(m=t.aRetenir)!=null&&m.length?`
    <div class="card cours-aretenir-card">
      <div class="cours-aretenir-title">${x("star")} À retenir</div>
      <ul class="cours-aretenir-list">
        ${t.aRetenir.slice(0,5).map($=>`<li data-text="${encodeURIComponent($)}"></li>`).join("")}
      </ul>
    </div>`:""}
  `,n=t.figure?`
    <div class="cours-figure-wrap">
      ${qe(t.figure)}
      ${t.figure.alt?`<div class="cours-figure-caption">${t.figure.alt}</div>`:""}
    </div>
  `:"";h.innerHTML=`
    <div class="cours-back-row">
      <button class="btn btn-ghost btn-sm" id="cours-back-to-chapter" type="button">${x("arrowLeft")} ${z(o.title,o.notions.map($=>$.title))||e.replace(/_/g," ")}</button>
    </div>

    <h1 class="cours-notion-title">${t.title}</h1>
    <p class="cours-intro-text">${t.intro||""}</p>

    <div class="card cours-objectif-card">
      <div class="cours-objectif-icon">${x("target")}</div>
      <p>${t.objectif||""}</p>
    </div>

    ${t.figure?`
    <div class="cours-figure-layout">
      <div class="cours-figure-col">${n}</div>
      <div class="cours-figure-text-col">${c}</div>
    </div>
    `:c}

    <div id="cours-quiz-zone"></div>
    <div class="cours-nav-row" id="cours-done-row" ${(y=t.quizExerciseIds)!=null&&y.length?"hidden":""}>
      <span></span>
      <button class="btn btn-primary" id="cours-mark-done-btn" type="button">${x("check")} J'ai terminé cette leçon</button>
    </div>

    ${ze(o,t)}
  `,_e(h),C(h),h.querySelector("#cours-back-to-chapter").addEventListener("click",()=>K(e,o)),h.querySelectorAll(".cours-notion-nav-btn").forEach($=>{$.addEventListener("click",()=>{const v=o.notions.find(f=>f.id===$.dataset.notion);v&&X(e,o,v)})}),a({status:"in_progress"}),(b=t.quizExerciseIds)!=null&&b.length?g(h.querySelector("#cours-quiz-zone")):(k=h.querySelector("#cours-mark-done-btn"))==null||k.addEventListener("click",()=>{a({status:"done"}),h.querySelector("#cours-done-row").innerHTML=`<span class="cours-done-confirm">${x("check")} Leçon terminée !</span>`});async function g($){$.innerHTML='<div class="skeleton" style="height:140px;"></div>';let v;try{v=await Promise.all(t.quizExerciseIds.map(q=>E.exercise(q,S()).then(H=>H.exercise)))}catch{$.innerHTML="",a({status:"done"});return}let f=0,w=0;function L(){if(f>=v.length){$.innerHTML=`<div class="card cours-quiz-done">${x("check")} Mini-quiz terminé : <strong>${w}/${v.length}</strong> bonnes réponses.</div>`,C($.querySelector(".cours-quiz-done")),a({status:"done",quizScore:w,quizTotal:v.length});return}const q=v[f],H=Math.round(f/v.length*100);$.innerHTML=`
        <div class="card cours-quiz-card">
          <div class="cours-quiz-label">
            <span class="cours-quiz-label-text">${x("lightbulb")} Mini-quiz — question ${f+1}/${v.length}</span>
            <div class="progress-track cours-quiz-progress"><div class="progress-fill" style="width:${H}%"></div></div>
          </div>
          <div id="cours-quiz-enonce"></div>
          <button class="btn btn-ghost btn-sm" id="cours-quiz-reveal" type="button">Voir la réponse</button>
          <div id="cours-quiz-answer" hidden></div>
          <div class="cours-nav-row" id="cours-quiz-verdict" hidden>
            <button class="btn btn-verdict-no" id="cours-quiz-fail" type="button">À revoir</button>
            <button class="btn btn-verdict-yes" id="cours-quiz-success" type="button">${x("check")} J'ai réussi</button>
          </div>
        </div>
      `,C($.querySelector(".cours-quiz-card")),I($.querySelector("#cours-quiz-enonce"),q.enonce),$.querySelector("#cours-quiz-reveal").addEventListener("click",()=>{const N=$.querySelector("#cours-quiz-answer");N.hidden=!1,I(N,`Réponse : ${q.answer}${q.hint?`
Indice : ${q.hint}`:""}`),$.querySelector("#cours-quiz-reveal").hidden=!0,$.querySelector("#cours-quiz-verdict").hidden=!1}),$.querySelector("#cours-quiz-fail").addEventListener("click",()=>{f+=1,L()}),$.querySelector("#cours-quiz-success").addEventListener("click",()=>{w+=1,f+=1,L()})}L()}}async function Be(e,o){await W(e);const t=await J(e),a=t.notions.find(c=>c.id===o);a&&X(e,t,a)}function je(){_.innerHTML=`
    <section class="empty-state card" style="grid-column:1/-1;">
      <div class="empty-state-icon">${x("bookOpen")}</div>
      <h3>Pas encore de cours ici</h3>
      <p>Aucun cours n'est encore disponible pour cette classe.</p>
    </section>
  `}async function De(){const e=S();let o=!0;try{const i=(await ne()).find(l=>l.classLevel===e);o=i?i.hasCourses!==!1:!0}catch{o=!0}if(!o){je();return}const[t,a]=await Promise.all([E.chapters(e),E.getCourseProgress(e).catch(()=>({}))]);j=t.chapters_meta||[],D=a||{},U();const c=new URLSearchParams(window.location.search),n=c.get("chapter"),g=c.get("notion");n&&g?Be(n,g):n&&W(n)}De();se(e=>{["appearance","*"].includes(e.detail.category)&&(B.hidden||U())});
