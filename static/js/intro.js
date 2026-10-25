/* Intro page motion helpers. Without JS the hero story still plays once and everything is visible. */
(function () {
  "use strict";
  if (!("IntersectionObserver" in window)) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const hero = document.querySelector(".hero");

  // The promo loop: skipped on data saver (soldiers on mobile data). It only downloads once we call play(),
  // plays while on screen and pauses off screen. If the browser refuses to play it, the SVG story stays.
  const video = hero && hero.querySelector(".hero-video");
  const saveData = navigator.connection && navigator.connection.saveData;
  if (video && !saveData && (video.canPlayType("video/webm") || video.canPlayType("video/mp4"))) {
    hero.classList.add("has-video");
    new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) { video.pause(); return; }
      video.play().catch((err) => {
        console.warn("Hero video could not play, showing the animation instead:", err.name);
        hero.classList.remove("has-video");
      });
    }, { threshold: 0.25 }).observe(video);
  }

  // Replay the hero story each time it comes back into view after being fully scrolled away.
  if (hero) {
    let leftView = false;
    new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) { leftView = true; return; }
        if (!leftView) return;
        leftView = false;
        hero.classList.remove("play");
        void hero.offsetWidth; // force a style flush so the animations restart from 0
        hero.classList.add("play");
      });
    }).observe(hero);
  }

  // Scroll reveals: CSS does this natively where supported (intro.css). This is the fallback.
  if (CSS.supports("(animation-timeline: view()) and (animation-range: entry)")) return;
  document.body.classList.add("js-reveal");
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
  document.querySelectorAll("[data-reveal]").forEach((el) => io.observe(el));
})();
