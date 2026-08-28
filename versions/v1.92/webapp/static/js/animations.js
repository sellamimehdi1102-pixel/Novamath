// ── Micro-interactions : confettis de réussite, secousse d'erreur, transitions
// Respecte le toggle Animations (Paramètres → Apparence) : tokens.css neutralise
// déjà les transitions/animations CSS via [data-animations="off"], mais ces
// trois fonctions pilotent aussi du JS pur (confettis ajoutés/retirés du DOM,
// écoute de transitionend) qui doit être court-circuité explicitement ici.
import { getAccentColor, getAccentColorSecondary } from "./theme.js";

function animationsEnabled() {
  return document.documentElement.getAttribute("data-animations") !== "off";
}

export function fireConfetti(rootEl = document.body) {
  if (!animationsEnabled()) return;
  const colors = [getAccentColor(), getAccentColorSecondary(), "#22c55e", "#f59e0b"];
  const container = document.createElement("div");
  container.style.cssText =
    "position:fixed;inset:0;pointer-events:none;z-index:9999;overflow:hidden;";
  rootEl.appendChild(container);

  const count = 60;
  for (let i = 0; i < count; i++) {
    const piece = document.createElement("span");
    const size = 6 + Math.random() * 6;
    const left = Math.random() * 100;
    const duration = 1600 + Math.random() * 900;
    const delay = Math.random() * 150;
    const rotate = Math.random() * 720 - 360;
    piece.style.cssText = `
      position:absolute; top:-10px; left:${left}%;
      width:${size}px; height:${size * 0.4}px;
      background:${colors[i % colors.length]};
      border-radius:2px;
      opacity:0.95;
      transform:rotate(${Math.random() * 360}deg);
      animation:lumis-confetti-fall ${duration}ms ${delay}ms cubic-bezier(0.4,0,0.2,1) forwards;
      --rotate-end:${rotate}deg;
    `;
    container.appendChild(piece);
  }

  ensureConfettiKeyframes();
  setTimeout(() => container.remove(), 2800);
}

function ensureConfettiKeyframes() {
  if (document.getElementById("lumis-confetti-style")) return;
  const style = document.createElement("style");
  style.id = "lumis-confetti-style";
  style.textContent = `
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
  `;
  document.head.appendChild(style);
}

export function shakeElement(el) {
  if (!animationsEnabled()) return;
  ensureConfettiKeyframes();
  el.style.animation = "none";
  // Force reflow pour pouvoir relancer l'animation
  void el.offsetWidth;
  el.style.animation = "lumis-shake 420ms";
}

export function fadeInTransition(el) {
  if (!animationsEnabled()) return;
  ensureConfettiKeyframes();
  el.classList.remove("lumis-fade-enter");
  void el.offsetWidth;
  el.classList.add("lumis-fade-enter");
}

// Compteur animé (stat-cards du Dashboard, statistiques du Profil...).
// Saute directement à la valeur finale si les animations sont désactivées.
export function animateCount(el, { to, from = 0, duration = 900, formatter = (n) => Math.round(n).toString() } = {}) {
  if (!animationsEnabled()) {
    el.textContent = formatter(to);
    return;
  }
  const start = performance.now();
  function tick(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = formatter(from + (to - from) * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
