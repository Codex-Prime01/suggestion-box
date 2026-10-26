/* Owner pages: offer to put the inbox on the home screen (uses the owner manifest). "Not now" is remembered on this device. */
(function () {
  "use strict";
  const card = document.getElementById("install-card");
  if (!card) return;
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let dismissed = false;
  try {
    dismissed = localStorage.getItem("sb-install-dismissed") === "1";
  } catch (e) {
    console.warn("Can't read local storage, the install tip may show again:", e.name);
  }
  if (standalone || dismissed) return;

  const btn = document.getElementById("install-btn");
  document.getElementById("install-dismiss").addEventListener("click", () => {
    card.hidden = true;
    try {
      localStorage.setItem("sb-install-dismissed", "1");
    } catch (e) {
      console.warn("Can't save to local storage, the install tip may show again:", e.name);
    }
  });

  // iPhone/iPad have no install button: show the Share -> Add to Home Screen steps instead
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (isIOS) {
    card.querySelector("[data-ios]").hidden = false;
    card.hidden = false;
    return;
  }

  // Chrome/Edge/Samsung: the browser tells us when installing is possible
  let installEvent = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installEvent = e;
    card.querySelector("[data-other]").hidden = false;
    btn.hidden = false;
    card.hidden = false;
  });
  btn.addEventListener("click", async () => {
    if (!installEvent) return;
    installEvent.prompt();
    const { outcome } = await installEvent.userChoice;
    installEvent = null;
    if (outcome === "accepted") card.hidden = true;
  });
  window.addEventListener("appinstalled", () => { card.hidden = true; });
})();
