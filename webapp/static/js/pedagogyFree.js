// Gratuité pédagogique : le serveur pose la classe `pedagogy-free` sur <html>
// (server.py::_serve_protected, config.PEDAGOGY_FREE). Module volontairement
// isolé : aucune dépendance, pour rester utilisable partout.
export function isPedagogyFree() {
  return document.documentElement.classList.contains("pedagogy-free");
}
