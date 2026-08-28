import{a as P}from"./api.D9MhFfTx.js";import"./scroll-reveal.C-UvXuVT.js";/* empty css             *//* empty css              */import{r as H}from"./chapterTitleByNotions.B33dvngo.js";import"./sidebar.CPsBZKLi.js";import"./command-palette.BPLLTaPv.js";import{i as J,b as V,s as K,g as U,c as X,m as Y,a as Z,d as Q,e as W,f as D,h as ee,j as te}from"./i18n.B3NAIOE2.js";import{b as se}from"./settingsPopup.CFfwvaaF.js";import{r as ne}from"./resume.D-9B4_bU.js";import{g as h,i as f}from"./theme.DpqEKRmI.js";const T=J();T.then(()=>V());se(document.getElementById("settings-btn"));ne(document.getElementById("resume-card"));const q={1:"Facile",2:"Moyen",3:"Confirmé",4:"Difficile",5:"Expert"},j={1:"badge--success",2:"badge--success",3:"badge--warning",4:"badge--danger",5:"badge--danger"},m=new Set,g=document.getElementById("chapters-grid"),N=document.getElementById("selection-bar"),re=document.getElementById("selection-count"),F=document.getElementById("chapters-empty-filter");let C=[],w="all";const ae=2;let R=!1;P.me().then(({user:e})=>{R=!!e.is_guest}).catch(()=>{});function oe(){if(document.getElementById("guest-chapters-modal-overlay"))return;const e=document.createElement("div");e.className="modal-overlay",e.id="guest-chapters-modal-overlay",e.hidden=!0,e.innerHTML=`
    <div class="modal-card card">
      <h3>Débloquez tous les chapitres</h3>
      <p>Créez gratuitement votre compte NovaMath afin d'accéder à tous les chapitres, sauvegarder votre progression et retrouver vos statistiques sur tous vos appareils.</p>
      <div class="verdict-row" style="flex-direction:column; gap:10px;">
        <button type="button" class="btn btn-primary js-open-signup">Créer un compte</button>
        <button type="button" class="btn btn-secondary js-open-login">Se connecter</button>
        <button type="button" class="btn btn-ghost" id="btn-guest-chapters-dismiss">Continuer en mode invité</button>
      </div>
    </div>
  `,document.body.appendChild(e),e.addEventListener("click",t=>{t.target===e&&(e.hidden=!0)}),e.querySelector("#btn-guest-chapters-dismiss").addEventListener("click",()=>{e.hidden=!0}),e.querySelectorAll(".js-open-signup, .js-open-login").forEach(t=>{t.addEventListener("click",()=>{e.hidden=!0})})}function ie(){oe(),document.getElementById("guest-chapters-modal-overlay").hidden=!1}function ce(e){if(!e)return"jamais";const t=Math.floor((Date.now()-e)/864e5);return t<=0?"aujourd'hui":t===1?"hier":`il y a ${t} j`}function le(){return f("checklist")}function de(e,t,r){return r===0?{text:"À faire",cls:"badge--neutral"}:e>=70&&t>=70?{text:"Maîtrisé",cls:"badge--success"}:e>=30||t>=50?{text:"En progrès",cls:"badge--warning"}:{text:"À renforcer",cls:"badge--danger"}}function ue(e,t){return t==="seconde"?e:`${t}:${e}`}function pe(){const e=h(),r=(D().favorites||[]).filter(a=>{const i=a.indexOf(":");return i===-1?e==="seconde":a.slice(0,i)===e}).map(a=>{const i=a.indexOf(":");return i===-1?a:a.slice(i+1)});return new Set(r)}function me(e){const t=h(),r=D().favorites||[],a=ue(e,t),i=r.includes(a),o=i?r.filter(d=>d!==a):[...r,a];return te("favorites",null,o),!i}function ge(){return'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 2.5 3 6.6 7 .8-5.2 4.8 1.4 7-6.2-3.6-6.2 3.6 1.4-7L2 9.9l7-.8 3-6.6Z" stroke-linejoin="round"/></svg>'}const ve={ongoing:"Aucune série en cours.",mastered:"Aucun chapitre maîtrisé pour l'instant.",unmastered:"Bravo, tous les chapitres travaillés sont maîtrisés !",saved:"Aucun chapitre enregistré pour l'instant — clique sur l'étoile d'une carte pour l'ajouter."};function fe(e,t,r){const{favorites:a,inProgress:i}=r;switch(t){case"ongoing":return e.filter(o=>{var d;return i&&((d=i.seriesConfig)==null?void 0:d.chapterId)===o.id});case"mastered":return e.filter(o=>r.masteryOf(o)==="mastered");case"unmastered":return e.filter(o=>r.masteryOf(o)!=="mastered");case"saved":return e.filter(o=>a.has(o.id));default:return e}}document.getElementById("chapter-filter-bar").addEventListener("click",e=>{const t=e.target.closest(".chapter-filter-pill");t&&(w=t.dataset.filter,document.querySelectorAll(".chapter-filter-pill").forEach(r=>{r.classList.toggle("active",r===t),r.setAttribute("aria-selected",String(r===t))}),I(C))});function I(e){C=e;const t=K(U(),h()),r=X(t.history),a=Y(t.history),i=Z(t.history),o=Q(t.history),d=W(),k=pe(),O=n=>{var _;const y=r[n.id]||new Set,$=n.n_exercises?Math.round(y.size/n.n_exercises*100):0,E=Math.round((((_=a[n.id])==null?void 0:_.rate)||0)*100);return{coveredIds:y,progressPct:$,accuracyPct:E}},b=fe(e,w,{favorites:k,inProgress:d,masteryOf:n=>ee(n.id,t.history)});F.hidden=b.length!==0,g.hidden=b.length===0,b.length||(F.textContent=ve[w]||"Aucun chapitre à afficher."),g.innerHTML="",b.forEach(n=>{const{coveredIds:y,progressPct:$,accuracyPct:E}=O(n),z=Math.max(0,n.n_exercises-y.size)*3,L=k.has(n.id),l=document.createElement("article");l.className="chapter-card card card--interactive",l.dataset.id=n.id;const G=n.notions_detail.map(s=>{const c=`${n.id}|${s.notion}`,u=(i[c]||new Set).size,x=s.n_exercises?Math.round(u/s.n_exercises*100):0,p=o[c]||{count:0,rate:0,last:null},B=Math.round(p.rate*100),M=de(x,B,p.count),v=d==null?void 0:d.seriesConfig,S=!!v&&v.chapterId===n.id&&(v.notions?v.notions.includes(s.notion):v.notion===s.notion);return`
        <div class="notion-row${S?" notion-row--resumable":" notion-row--selectable"}" data-chapter="${n.id}" data-notion="${s.notion.replace(/"/g,"&quot;")}" data-ids="${s.exercise_ids.join(",")}" data-resumable="${S}">
          <div class="notion-row-top">
            <span class="notion-row-label">${S?"":'<span class="notion-checkbox" aria-hidden="true"></span>'}<span>${s.notion}</span></span>
            <span class="badge ${j[s.difficulty_dominant]}">${q[s.difficulty_dominant]}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${x}%"></div></div>
          <div class="notion-meta">
            <span>${p.count}/${s.n_exercises} exercices faits · Accuracy ${B}% · Temps moyen ${he(t.history,n.id,s.notion)}</span>
            <span>Dernier entraînement : ${ce(p.last)}</span>
          </div>
          <div class="notion-meta">
            <span>Difficultés : ${(s.difficulties_available||[]).join(", ")}${s.n_natural_variants?` · ${s.n_natural_variants} variantes`:""}</span>
          </div>
          <div class="notion-meta" style="margin-top:6px;">
            <span class="badge ${M.cls}">${M.text}</span>
            ${S?`<button class="btn btn-ghost btn-sm notion-action-btn" type="button">${f("play")} Reprendre</button>`:""}
          </div>
        </div>`}).join("");l.innerHTML=`
      <div class="chapter-card-top">
        <div class="chapter-icon">${le()}</div>
        <div class="chapter-card-top-right">
          <button type="button" class="chapter-favorite-btn${L?" is-favorite":""}" aria-label="${L?"Retirer des favoris":"Ajouter aux favoris"}" aria-pressed="${L}">${ge()}</button>
          <div class="chapter-select-dot"></div>
        </div>
      </div>
      <h3>${H(n.title,n.notions_cours)||n.id.replace(/_/g," ")}</h3>
      <div class="chapter-id">${n.id.replace("_"," ")}</div>
      <div class="chapter-progress">
        <div class="chapter-progress-label"><span>Progression</span><span>${$}%</span></div>
        <div class="progress-track"><div class="progress-fill" style="width:${$}%"></div></div>
      </div>
      <div class="chapter-meta-row">
        <span>${f("clock")} ~${z} min restantes</span>
        <span>${f("penSquare")} ${n.n_exercises} exercices</span>
        <span>${f("layers")} ${n.n_notions} notions</span>
      </div>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <span class="badge ${j[n.difficulty_dominant]}">${q[n.difficulty_dominant]} dominant</span>
        <span class="badge badge--neutral">Réussite ${E}%</span>
      </div>
      <button class="chapter-expand-btn" type="button">
        Voir les notions
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </button>
      <div class="notions-panel">
        ${G}
        <button class="btn btn-primary btn-sm notions-start-btn" type="button" disabled>Commencer la série</button>
      </div>
    `,l.addEventListener("click",s=>{s.target.closest(".chapter-expand-btn")||s.target.closest(".notion-row")||s.target.closest(".chapter-favorite-btn")||ye(n.id,l)}),l.querySelector(".chapter-favorite-btn").addEventListener("click",s=>{s.stopPropagation();const c=me(n.id),u=s.currentTarget;u.classList.toggle("is-favorite",c),u.setAttribute("aria-pressed",String(c)),u.setAttribute("aria-label",c?"Retirer des favoris":"Ajouter aux favoris"),w==="saved"&&!c&&I(C)}),l.querySelector(".chapter-expand-btn").addEventListener("click",s=>{s.stopPropagation();const c=l.classList.contains("expanded");g.querySelectorAll(".chapter-card.expanded").forEach(u=>u.classList.remove("expanded")),c||l.classList.add("expanded")});const A=l.querySelector(".notions-start-btn");l.querySelectorAll(".notion-row").forEach(s=>{s.addEventListener("click",c=>{if(c.stopPropagation(),s.dataset.resumable==="true"){window.location.href="exercice.html";return}s.classList.toggle("selected"),A.disabled=l.querySelectorAll(".notion-row.selected").length===0})}),A.addEventListener("click",s=>{s.stopPropagation();const c=[...l.querySelectorAll(".notion-row.selected")];if(!c.length)return;const u=c.map(p=>p.dataset.notion),x=[...new Set(c.flatMap(p=>p.dataset.ids.split(",").map(Number)))];be(n.id,u,x)}),g.appendChild(l)})}function he(e,t,r){const a=e.filter(o=>o.chapter===t&&o.notion===r&&o.duration_s);if(!a.length)return"—";const i=a.reduce((o,d)=>o+d.duration_s,0)/a.length;return`${Math.round(i)} s`}function be(e,t,r){localStorage.setItem("lumis:pending_series",JSON.stringify({mode:"notion",chapterId:e,notion:t.join(" + "),notions:t,exerciseIds:r})),window.location.href="exercice.html"}function ye(e,t){if(m.has(e))m.delete(e),t.classList.remove("selected");else{if(R&&m.size>=ae){ie();return}m.add(e),t.classList.add("selected")}$e()}function $e(){const e=m.size;re.textContent=e===0?"Tous les chapitres (aucune sélection)":`${e} chapitre${e>1?"s":""} sélectionné${e>1?"s":""}`,N.classList.add("visible")}document.getElementById("btn-start-evaluation").addEventListener("click",e=>{e.preventDefault(),localStorage.setItem("lumis:selected_chapters",JSON.stringify({classLevel:h(),chapters:[...m]})),window.location.href="evaluation.html"});function xe(){let e;try{e=JSON.parse(localStorage.getItem("lumis:open_chapter"))}catch{e=null}if(!e)return;localStorage.removeItem("lumis:open_chapter");const t=g.querySelector(`.chapter-card[data-id="${e.chapterId}"]`);t&&(g.querySelectorAll(".chapter-card.expanded").forEach(r=>r.classList.remove("expanded")),t.classList.add("expanded"),t.scrollIntoView({behavior:"smooth",block:"center"}))}Promise.all([T,P.chapters(h())]).then(([,e])=>{I(e.chapters_meta||[]),N.classList.add("visible"),xe()});
