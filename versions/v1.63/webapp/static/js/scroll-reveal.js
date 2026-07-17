/* Apparition progressive au scroll — observe .reveal/.reveal-stagger
   (définies dans css/animations.css) et ajoute .is-visible au premier
   passage dans le viewport. Respecte data-animations="off" et
   prefers-reduced-motion : rend tout visible immédiatement sans animer. */

export function initScrollReveal(root = document) {
  const els = root.querySelectorAll(".reveal, .reveal-stagger");
  if (!els.length) return;

  const reduced =
    document.documentElement.getAttribute("data-animations") === "off" ||
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduced || typeof IntersectionObserver === "undefined") {
    els.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
  );

  els.forEach((el) => io.observe(el));
}
