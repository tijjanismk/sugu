// Bannière « Installer l'application » (ticket #14). Dans un fichier et non en ligne : CSP.
// Android et Chrome : on garde l'événement beforeinstallprompt et on ouvre la vraie demande
// d'installation au clic. iPhone et Safari n'ont pas d'événement : on montre la marche à suivre.
(() => {
  "use strict";

  const banner = document.querySelector("[data-install-banner]");
  if (!banner) return;
  const LATER_KEY = "sugu-installer-plus-tard";
  const LATER_DAYS = 30;

  const installed =
    window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (installed) return;
  try {
    const until = Number(localStorage.getItem(LATER_KEY));
    if (until && Date.now() < until) return;
  } catch (error) {
    // Stockage indisponible (navigation privée) : la bannière reste possible.
  }

  const accept = banner.querySelector("[data-install-accept]");
  const later = banner.querySelector("[data-install-later]");
  const show = () => banner.classList.remove("hidden");
  const hide = () => banner.classList.add("hidden");
  let installPrompt = null;

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault(); // pas la mini-barre du navigateur : notre bannière à la place
    installPrompt = event;
    show();
  });
  window.addEventListener("appinstalled", hide);

  accept.addEventListener("click", async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
    hide();
  });

  later.addEventListener("click", () => {
    hide();
    try {
      localStorage.setItem(LATER_KEY, String(Date.now() + LATER_DAYS * 24 * 60 * 60 * 1000));
    } catch (error) {
      // Rien à mémoriser : elle reviendra à la prochaine visite.
    }
  });

  const agent = navigator.userAgent;
  const ios = /iphone|ipad|ipod/i.test(agent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const safari = /safari/i.test(agent) && !/crios|fxios|edgios|opios/i.test(agent);
  if (ios && safari) {
    banner.querySelector("[data-install-text]").classList.add("hidden");
    banner.querySelector("[data-install-ios]").classList.remove("hidden");
    accept.classList.add("hidden");
    show();
  }
})();
