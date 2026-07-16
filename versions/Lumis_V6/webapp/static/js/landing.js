import { bindThemeToggle } from "./theme.js";

bindThemeToggle(document.getElementById("theme-toggle"));

document.querySelectorAll(".faq-question").forEach((q) => {
  q.addEventListener("click", () => {
    q.closest(".faq-item").classList.toggle("open");
  });
});
