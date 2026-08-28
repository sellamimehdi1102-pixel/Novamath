import{e as g}from"./i18n.p3FnEZbd.js";import{i as o}from"./theme.CdfXyWq_.js";function f(t){return t<60?`${t} s`:`${Math.round(t/60)} min`}function u(t){var s,n;const e=g();if(!e)return t.hidden=!0,!1;const a=(e.draftQuestions||[]).reduce((d,c)=>d+(c.duration_s||0),0),i=((s=e.seriesConfig)==null?void 0:s.chapterId)||"Entraînement mixte",p=((n=e.seriesConfig)==null?void 0:n.notion)||"—",r=e.total||10,l=e.progressPct??Math.round(e.seriesIndex/r*100);return t.hidden=!1,t.innerHTML=`
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
      <div>
        <h3 style="font-size:1rem; margin-bottom:10px; display:flex; align-items:center; gap:8px;">${o("bookOpen")} Série en cours</h3>
        <div style="display:flex; gap:18px; flex-wrap:wrap; font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">
          <span>Chapitre : <strong style="color:var(--text);">${i}</strong></span>
          <span>Notion : <strong style="color:var(--text);">${p}</strong></span>
          <span>Question <strong style="color:var(--text);">${e.seriesIndex+1} / ${r}</strong></span>
          <span>Temps écoulé : <strong style="color:var(--text);">${f(a)}</strong></span>
        </div>
        <div class="progress-track" style="max-width:260px;">
          <div class="progress-fill" style="width:${l}%"></div>
        </div>
      </div>
      <a href="exercice.html" class="btn btn-primary">${o("play")} Reprendre la série</a>
    </div>
  `,!0}export{u as r};
