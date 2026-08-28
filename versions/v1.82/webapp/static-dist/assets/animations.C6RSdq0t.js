import{a as u,c as p}from"./theme.DpqEKRmI.js";function r(){return document.documentElement.getAttribute("data-animations")!=="off"}function y(t=document.body){if(!r())return;const a=[u(),p(),"#22c55e","#f59e0b"],e=document.createElement("div");e.style.cssText="position:fixed;inset:0;pointer-events:none;z-index:9999;overflow:hidden;",t.appendChild(e);const m=60;for(let n=0;n<m;n++){const o=document.createElement("span"),s=6+Math.random()*6,c=Math.random()*100,i=1600+Math.random()*900,d=Math.random()*150,l=Math.random()*720-360;o.style.cssText=`
      position:absolute; top:-10px; left:${c}%;
      width:${s}px; height:${s*.4}px;
      background:${a[n%a.length]};
      border-radius:2px;
      opacity:0.95;
      transform:rotate(${Math.random()*360}deg);
      animation:lumis-confetti-fall ${i}ms ${d}ms cubic-bezier(0.4,0,0.2,1) forwards;
      --rotate-end:${l}deg;
    `,e.appendChild(o)}f(),setTimeout(()=>e.remove(),2800)}function f(){if(document.getElementById("lumis-confetti-style"))return;const t=document.createElement("style");t.id="lumis-confetti-style",t.textContent=`
    @keyframes lumis-confetti-fall {
      to { top: 100vh; transform: rotate(var(--rotate-end)); opacity: 0.2; }
    }
    @keyframes lumis-shake {
      10%, 90% { transform: translateX(-2px); }
      20%, 80% { transform: translateX(4px); }
      30%, 50%, 70% { transform: translateX(-8px); }
      40%, 60% { transform: translateX(8px); }
    }
    .lumis-fade-enter { animation: lumis-fade-in 320ms cubic-bezier(0.16,1,0.3,1); }
    @keyframes lumis-fade-in {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `,document.head.appendChild(t)}function x(t){r()&&(f(),t.style.animation="none",t.offsetWidth,t.style.animation="lumis-shake 420ms")}function b(t){r()&&(f(),t.classList.remove("lumis-fade-enter"),t.offsetWidth,t.classList.add("lumis-fade-enter"))}function g(t,{to:a,from:e=0,duration:m=900,formatter:n=o=>Math.round(o).toString()}={}){if(!r()){t.textContent=n(a);return}const o=performance.now();function s(c){const i=Math.min(1,(c-o)/m),d=1-Math.pow(1-i,3);t.textContent=n(e+(a-e)*d),i<1&&requestAnimationFrame(s)}requestAnimationFrame(s)}export{g as a,y as b,b as f,x as s};
