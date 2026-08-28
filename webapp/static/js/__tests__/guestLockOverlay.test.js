// ── guestLockOverlay.js : composant unique de verrou invité (fusion du
// floutage du Dashboard + de la popup du Chatbot), voir MISSION "uniformiser
// les interfaces invité". Couvre le contrat commun aux deux consommateurs :
// mount => .guest-lock-target + popup, dismiss => popup fermée mais flou
// conservé (dashboard.js), unmount => déverrouillage complet.
import { describe, it, expect, beforeEach } from "vitest";
import { mountGuestLockOverlay, dismissGuestLockOverlay, unmountGuestLockOverlay } from "../guestLockOverlay.js";

beforeEach(() => {
  document.body.innerHTML = `<div id="target"></div>`;
});

describe("guestLockOverlay.js", () => {
  it("mount ajoute .guest-lock-target sur le conteneur et injecte la popup", () => {
    const container = document.getElementById("target");
    mountGuestLockOverlay(container, {
      id: "test-overlay",
      title: "Connexion requise",
      description: "Connecte-toi.",
      actionsHtml: `<button type="button" class="btn btn-primary js-open-login">Se connecter</button>`,
    });

    expect(container.classList.contains("guest-lock-target")).toBe(true);
    const overlay = document.getElementById("test-overlay");
    expect(overlay).not.toBeNull();
    expect(overlay.className).toBe("guest-lock-overlay");
    expect(overlay.querySelector("h3").textContent).toBe("Connexion requise");
    expect(overlay.querySelector(".js-open-login")).not.toBeNull();
  });

  it("mount est idempotent : un second appel avec le même id ne duplique pas la popup", () => {
    const container = document.getElementById("target");
    mountGuestLockOverlay(container, { id: "test-overlay", title: "A", description: "B", actionsHtml: "" });
    mountGuestLockOverlay(container, { id: "test-overlay", title: "A", description: "B", actionsHtml: "" });

    expect(document.querySelectorAll("#test-overlay").length).toBe(1);
  });

  it("dismiss retire la popup mais conserve le flou (comportement 'Continuer en mode invité' du Dashboard)", () => {
    const container = document.getElementById("target");
    mountGuestLockOverlay(container, { id: "test-overlay", title: "A", description: "B", actionsHtml: "" });

    dismissGuestLockOverlay("test-overlay");

    expect(document.getElementById("test-overlay")).toBeNull();
    expect(container.classList.contains("guest-lock-target")).toBe(true);
  });

  it("unmount retire la popup ET lève le flou (déverrouillage complet)", () => {
    const container = document.getElementById("target");
    mountGuestLockOverlay(container, { id: "test-overlay", title: "A", description: "B", actionsHtml: "" });

    unmountGuestLockOverlay(container, "test-overlay");

    expect(document.getElementById("test-overlay")).toBeNull();
    expect(container.classList.contains("guest-lock-target")).toBe(false);
  });

  it("rend la liste optionnelle uniquement quand elle est fournie", () => {
    const container = document.getElementById("target");
    const overlay = mountGuestLockOverlay(container, {
      id: "test-overlay",
      title: "A",
      description: "B",
      listItems: ["un ;", "deux."],
      actionsHtml: "",
    });

    const items = overlay.querySelectorAll(".guest-lock-card-list li");
    expect(items.length).toBe(2);
    expect(items[0].textContent).toBe("un ;");
  });
});
