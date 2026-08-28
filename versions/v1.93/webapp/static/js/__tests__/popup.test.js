// ── popup.js : composant popup générique (ouverture/fermeture/prompt/confirm) ─
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { openPopup, openPromptPopup, openConfirmPopup } from "../popup.js";

describe("popup.js — openPopup", () => {
  it("insère un overlay dans le document avec titre et corps", () => {
    const { el } = openPopup({ title: "Titre", bodyHtml: "<p>Contenu</p>" });
    expect(document.body.contains(el)).toBe(true);
    expect(el.querySelector(".popup-title").textContent).toBe("Titre");
    expect(el.querySelector(".popup-body").innerHTML).toBe("<p>Contenu</p>");
  });

  it("réutilise un élément existant si `id` correspond à un id déjà présent", () => {
    const existing = document.createElement("div");
    existing.id = "my-popup";
    document.body.appendChild(existing);
    const { el } = openPopup({ id: "my-popup", title: "X" });
    expect(el).toBe(existing);
    expect(document.querySelectorAll("#my-popup").length).toBe(1);
  });

  it("n'affiche pas de bouton de fermeture si showCloseButton=false et aucun titre", () => {
    const { el } = openPopup({ showCloseButton: false });
    expect(el.querySelector(".popup-close")).toBeNull();
  });

  it("appelle onOpen(card) après l'insertion", () => {
    const onOpen = vi.fn();
    openPopup({ title: "X", onOpen });
    expect(onOpen).toHaveBeenCalledOnce();
  });

  it("close() masque l'overlay après l'animation de fermeture (timeout de secours)", async () => {
    vi.useFakeTimers();
    const { close, el } = openPopup({ title: "X" });
    close();
    await vi.advanceTimersByTimeAsync(300);
    expect(el.hidden).toBe(true);
    vi.useRealTimers();
  });

  it("le clic sur le bouton de fermeture ferme le popup", async () => {
    vi.useFakeTimers();
    const { el } = openPopup({ title: "X", showCloseButton: true });
    el.querySelector(".popup-close").click();
    await vi.advanceTimersByTimeAsync(300);
    expect(el.hidden).toBe(true);
    vi.useRealTimers();
  });

  it("Échap ferme le popup si closeOnEscape !== false", async () => {
    vi.useFakeTimers();
    const { el } = openPopup({ title: "X" });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await vi.advanceTimersByTimeAsync(300);
    expect(el.hidden).toBe(true);
    vi.useRealTimers();
  });

  it("Échap ne ferme rien si closeOnEscape=false", async () => {
    vi.useFakeTimers();
    const { el } = openPopup({ title: "X", closeOnEscape: false });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await vi.advanceTimersByTimeAsync(300);
    expect(el.hidden).toBe(false);
    vi.useRealTimers();
  });

  it("le clic sur l'overlay lui-même ferme le popup si closeOnOverlayClick !== false", async () => {
    vi.useFakeTimers();
    const { el } = openPopup({ title: "X" });
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await vi.advanceTimersByTimeAsync(300);
    expect(el.hidden).toBe(true);
    vi.useRealTimers();
  });

  it("appelle onClose une seule fois même si close() est appelé plusieurs fois", async () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    const { close } = openPopup({ title: "X", onClose });
    close();
    close();
    await vi.advanceTimersByTimeAsync(300);
    expect(onClose).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });
});

describe("popup.js — openPromptPopup", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("résout la valeur saisie au clic sur confirmer", async () => {
    const promise = openPromptPopup({ title: "Renommer", defaultValue: "ancien" });
    const input = document.querySelector("#popup-prompt-input");
    input.value = "nouveau nom";
    document.querySelector('[data-action="confirm"]').click();
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toBe("nouveau nom");
  });

  it("résout null au clic sur annuler", async () => {
    const promise = openPromptPopup({ title: "Renommer" });
    document.querySelector('[data-action="cancel"]').click();
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toBeNull();
  });

  it("Entrée valide la saisie comme le bouton confirmer", async () => {
    const promise = openPromptPopup({});
    const input = document.querySelector("#popup-prompt-input");
    input.value = "via Entrée";
    input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toBe("via Entrée");
  });

  it("pré-remplit l'input avec defaultValue", () => {
    openPromptPopup({ defaultValue: "valeur initiale" });
    expect(document.querySelector("#popup-prompt-input").value).toBe("valeur initiale");
  });
});

describe("popup.js — openConfirmPopup", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("résout true au clic sur confirmer", async () => {
    const promise = openConfirmPopup({ message: "Es-tu sûr ?" });
    document.querySelector('[data-action="confirm"]').click();
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toBe(true);
  });

  it("résout false au clic sur annuler", async () => {
    const promise = openConfirmPopup({ message: "Es-tu sûr ?" });
    document.querySelector('[data-action="cancel"]').click();
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toBe(false);
  });

  it("affiche le message fourni", () => {
    openConfirmPopup({ message: "Supprimer définitivement ?" });
    expect(document.querySelector(".popup-confirm-message").textContent).toBe("Supprimer définitivement ?");
  });

  it("utilise le style danger sur le bouton confirmer si danger=true", () => {
    openConfirmPopup({ message: "x", danger: true });
    expect(document.querySelector('[data-action="confirm"]').classList.contains("btn-danger-outline")).toBe(true);
  });
});
