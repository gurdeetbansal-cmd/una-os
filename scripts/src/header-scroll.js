/**
 * Header Sticky Scroll
 * When window.scrollY > 0, add .is-sticky to lock header to white bg + black text.
 * When scrollY === 0, remove .is-sticky so header returns to transparent + white text.
 */

(function() {
  'use strict';

  const header = document.querySelector('.site-header');

  if (!header) return;

  function handleScroll() {
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;

    if (scrollY > 0) {
      header.classList.add('is-sticky');
    } else {
      header.classList.remove('is-sticky');
    }
  }

  handleScroll();
  window.addEventListener('scroll', handleScroll, { passive: true });
})();
