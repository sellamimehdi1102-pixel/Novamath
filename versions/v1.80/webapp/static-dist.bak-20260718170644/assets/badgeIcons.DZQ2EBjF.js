import{a as g}from"./api.BAG-rd0x.js";import{i as p,I as f}from"./theme.CdfXyWq_.js";import{a as h}from"./mathrender.C9lrWfgK.js";let o=null;const s=new Map;async function b(){if(o)return o;try{o=(await g.chapters()).chapters_meta||[]}catch{o=[]}return o}async function M(){const t=await b(),a={};return t.forEach(e=>{a[e.id]=e.title}),a}function x(t){if(!t)return"—";const[a,e,r]=t.split("-");return`${r}/${e}/${a}`}function w(t){return t?t<60?`${t} s`:`${Math.round(t/60)} min`:"0 min"}function $(t,a){if(!t)return"Mixte";const e=t.replace("Chapitre_",""),r=a[t];return r?`Chapitre ${e} · ${r}`:t}function L(t,a,{withRestart:e=!1}={}){const r=t.total-t.score,d=new Date(t.endedAt||Date.now()).toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"}),n=document.createElement("tr");return n.innerHTML=`
    <td>${x(t.date)}</td>
    <td>${d}</td>
    <td>${$(t.chapterId,a)}</td>
    <td>${t.notion||"—"}</td>
    <td>${t.score}/${t.total}</td>
    <td>${t.accuracy}%</td>
    <td>${w(t.durationTotal_s||0)}</td>
    <td>${t.score}</td>
    <td>${r}</td>
    <td>${t.levelAtTime||"—"}</td>
    <td style="white-space:nowrap;">
      <button class="btn btn-ghost btn-sm btn-review">${p("eye")} Revoir</button>
      ${e?`<button class="btn btn-ghost btn-sm btn-restart-series">${p("rotate")} Recommencer</button>`:""}
    </td>
  `,n.querySelector(".btn-review").addEventListener("click",()=>_(n,t)),e&&n.querySelector(".btn-restart-series").addEventListener("click",()=>C(t)),n}async function _(t,a){const e=t.nextElementSibling;if(e&&e.classList.contains("series-review-row")){e.remove();return}const r=document.createElement("tr");r.className="series-review-row";const c=document.createElement("td");c.colSpan=11,c.textContent="Chargement du détail...",r.appendChild(c),t.after(r);const d=await Promise.all(a.questions.map(async n=>{if(!s.has(n.exercise_id))try{const i=await g.exercise(n.exercise_id);s.set(n.exercise_id,i.exercise)}catch{s.set(n.exercise_id,null)}return{q:n,ex:s.get(n.exercise_id)}}));c.innerHTML="",d.forEach(({q:n,ex:i})=>{const l=document.createElement("div");l.className="series-review-item";const u=document.createElement("span");i?h(u,i.enonce):u.textContent="(exercice indisponible)";const m=document.createElement("span");m.className=`badge ${n.correct?"badge--success":"badge--danger"}`,m.textContent=n.correct?"Réussi":"Échoué",l.append(u,m),c.appendChild(l)})}function C(t){const a=[...new Set(t.questions.map(e=>e.exercise_id))];localStorage.setItem("lumis:pending_series",JSON.stringify({mode:t.mode,chapterId:t.chapterId,notion:t.notion,exerciseIds:a})),window.location.href="exercice.html"}const v={ex_10:"target",ex_50:"target",ex_100:"target",streak_7:"flame",streak_30:"star",chapter_mastered:"trophy",exam_pass:"graduationCap"};function N(t){return f[v[t]]||f.medal}export{N as a,L as b,M as c,b as g};
