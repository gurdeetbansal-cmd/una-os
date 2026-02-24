/**
 * Scroll Reveal – Ultra-Slow Cinematic (3000vh)
 * scrub: 4 for heavy momentum/lag.
 * Massive dead zones (~25% each) so each product stays static for long scroll.
 * Phase 1 (0–28%): Reset – plateau 0–23%, out 23–28%
 * Phase 2 (33–65%): Signal – intro 33–38%, plateau 38–60%, out 60–65%
 * Phase 3 (70–100%): Seal – intro 70–75%, plateau 75–95%, out 95–100%
 */

(function() {
  'use strict';
  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
  }
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

  const section = document.getElementById('scroll-reveal-sequence');
  if (!section) return;

  /* Verification: log scroll height */
  const scrollHeight = section ? section.offsetHeight : 0;
  console.log('[Scroll Reveal] Section height:', scrollHeight, 'px (expected ~3000vh)');

  const items = Array.from(section.querySelectorAll('.scroll-reveal-sequence__item'));
  if (items.length < 3) return;

  const reset = items[0];
  const signal = items[1];
  const seal = items[2];

  const resetInfoLeft = reset.querySelector('.info-left');
  const resetInfoRight = reset.querySelector('.info-right');
  const signalInfoLeft = signal.querySelector('.info-left');
  const signalInfoRight = signal.querySelector('.info-right');
  const sealInfoLeft = seal.querySelector('.info-left');
  const sealInfoRight = seal.querySelector('.info-right');

  const ease = 'power2.out';

  /* Initial: Reset visible; Signal & Seal hidden */
  gsap.set([reset, signal, seal], { force3D: true });
  gsap.set(reset, { opacity: 1, scale: 1 });
  gsap.set([resetInfoLeft, resetInfoRight], { opacity: 1 });
  gsap.set(signal, { opacity: 0, scale: 1 });
  gsap.set(seal, { opacity: 0, scale: 1 });
  gsap.set([signalInfoLeft, signalInfoRight, sealInfoLeft, sealInfoRight], { opacity: 0 });

  const tl = gsap.timeline({
    ease: ease,
    scrollTrigger: {
      trigger: section,
      start: 'top top',
      end: 'bottom bottom',
      scrub: 4,
      anticipatePin: 0
    }
  });

  /* Phase 1 (0–28%): Reset – plateau 0–23%, fade out 23–28% */
  tl.to([reset, resetInfoLeft, resetInfoRight], { opacity: 0, duration: 0.05, ease: ease }, 0.23);
  tl.to(reset, { scale: 1.15, duration: 0.05, ease: ease }, 0.23);

  /* Phase 2 (33–65%): Signal – intro 33–38%, plateau 38–60%, out 60–65% */
  tl.to(signal, { opacity: 1, scale: 1, duration: 0.05, ease: ease }, 0.33);
  tl.to([signalInfoLeft, signalInfoRight], { opacity: 1, duration: 0.05, ease: ease }, 0.33);
  tl.to([signal, signalInfoLeft, signalInfoRight], { opacity: 0, duration: 0.05, ease: ease }, 0.6);
  tl.to(signal, { scale: 1.15, duration: 0.05, ease: ease }, 0.6);

  /* Phase 3 (70–100%): Seal – intro 70–75%, plateau 75–95%, out 95–100% */
  tl.to(seal, { opacity: 1, scale: 1, duration: 0.05, ease: ease }, 0.7);
  tl.to([sealInfoLeft, sealInfoRight], { opacity: 1, duration: 0.05, ease: ease }, 0.7);
  tl.to([seal, sealInfoLeft, sealInfoRight], { opacity: 0, duration: 0.05, ease: ease }, 0.95);
  tl.to(seal, { scale: 1.15, duration: 0.05, ease: ease }, 0.95);
})();
