// Conversation (ticket #12) : amélioration progressive, la page marche sans ce fichier.
// Dans un fichier et non en attributs hx-on : compatible avec la future CSP stricte
// (docs/security.md).
(() => {
  const thread = document.getElementById("thread");
  const composer = document.querySelector("[data-composer]");
  if (!thread || !composer) return;

  const atBottom = () =>
    window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 80;
  const toBottom = () => window.scrollTo(0, document.documentElement.scrollHeight);

  toBottom(); // le dernier message est en bas, comme dans une messagerie de téléphone

  // Onglet en arrière-plan : pas de rafraîchissement, on économise les données.
  document.body.addEventListener("htmx:beforeRequest", (event) => {
    if (event.target.id === "poll" && document.hidden) event.preventDefault();
  });

  let follow = true;
  document.body.addEventListener("htmx:beforeSwap", () => {
    follow = atBottom();
  });
  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target.id === "composer-error") return;
    if (follow) toBottom();
  });

  // Message envoyé : on vide le champ (une erreur arrive avec l'en-tête HX-Retarget).
  composer.addEventListener("htmx:afterRequest", (event) => {
    const { xhr, successful } = event.detail;
    if (!successful || xhr.getResponseHeader("HX-Retarget")) return;
    composer.reset();
    const error = document.getElementById("composer-error");
    if (error) error.textContent = "";
    toBottom();
  });
})();
