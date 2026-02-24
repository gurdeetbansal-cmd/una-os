/**
 * Molecular Logic: rotate the PDRN molecule as the user scrolls (GSAP ScrollTrigger).
 */
(function () {
  "use strict";

  var wrap = document.getElementById("molecule-3d-wrap");
  var molecule = document.getElementById("molecule-3d");
  if (!wrap || !molecule) return;

  if (typeof gsap === "undefined" || typeof ScrollTrigger === "undefined") {
    return;
  }
  gsap.registerPlugin(ScrollTrigger);

  gsap.set(molecule, { transformOrigin: "50% 50%" });

  gsap.to(molecule, {
    rotateY: 360,
    ease: "none",
    scrollTrigger: {
      trigger: wrap,
      start: "top 80%",
      end: "bottom 20%",
      scrub: 1.2,
    },
  });
})();
