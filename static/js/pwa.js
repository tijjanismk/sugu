// Installation de Sugu comme application (ticket #14) : enregistre le service worker, dont
// l'adresse est donnée par la page (data-sw). Sans prise en charge : rien ne change.
(() => {
  const script = document.currentScript;
  if (!("serviceWorker" in navigator) || !script) return;
  const url = script.dataset.sw;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(url).catch(() => {});
  });
})();
