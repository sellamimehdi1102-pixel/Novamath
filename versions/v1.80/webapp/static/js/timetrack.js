// ── Chronomètre d'activité réelle ───────────────────────────────────────────
// Mesure le temps effectivement passé sur une question : ignore l'onglet
// masqué et l'inactivité prolongée (aucune interaction depuis IDLE_LIMIT_MS).
const IDLE_LIMIT_MS = 60_000;
const TICK_MS = 1000;

export class ActivityTimer {
  constructor() {
    this.activeMs = 0;
    this.lastActivity = Date.now();
    this.tickHandle = null;
    this._onActivity = () => { this.lastActivity = Date.now(); };
    ["mousemove", "keydown", "click", "touchstart", "scroll"].forEach((evt) =>
      window.addEventListener(evt, this._onActivity, { passive: true })
    );
  }

  start() {
    this.activeMs = 0;
    this.lastActivity = Date.now();
    this._lastTick = Date.now();
    clearInterval(this.tickHandle);
    this.tickHandle = setInterval(() => {
      const now = Date.now();
      const elapsed = now - this._lastTick;
      this._lastTick = now;
      const idle = now - this.lastActivity > IDLE_LIMIT_MS;
      if (document.visibilityState === "visible" && !idle) {
        this.activeMs += elapsed;
      }
    }, TICK_MS);
  }

  /** Arrête le chrono et renvoie le nombre de secondes actives écoulées. */
  stop() {
    clearInterval(this.tickHandle);
    this.tickHandle = null;
    return Math.round(this.activeMs / 1000);
  }

  destroy() {
    clearInterval(this.tickHandle);
    ["mousemove", "keydown", "click", "touchstart", "scroll"].forEach((evt) =>
      window.removeEventListener(evt, this._onActivity)
    );
  }
}
