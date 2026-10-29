// ── Gratuité pédagogique côté interface : aucune redirection ni offre quand
// le serveur pose la classe `pedagogy-free` sur <html>. ─────────────────────
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("handleQuotaExceeded", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.innerHTML = "";
  });
  afterEach(() => {
    document.documentElement.classList.remove("pedagogy-free");
    vi.useRealTimers();
  });

  it("gratuité active : message d'information, aucune mention d'offre, aucune redirection", async () => {
    vi.useFakeTimers();
    document.documentElement.classList.add("pedagogy-free");
    const { handleQuotaExceeded } = await import("../api.js");
    handleQuotaExceeded({ quota: "chat_messages", required_plan: "premium" });
    const toast = document.getElementById("novamath-quota-toast");
    expect(toast.textContent).toContain("demain");
    expect(toast.textContent).not.toMatch(/Premium|Ultra|Passe à/);
    vi.advanceTimersByTime(6000);
    expect(toast.hidden).toBe(true);
  });

  it("gratuité inactive : ancien message de mise à niveau conservé (réversibilité)", async () => {
    vi.useFakeTimers();
    const { handleQuotaExceeded } = await import("../api.js");
    handleQuotaExceeded({ quota: "chat_messages", required_plan: "premium" });
    expect(document.getElementById("novamath-quota-toast").textContent).toContain("Passe à Premium");
  });
});
