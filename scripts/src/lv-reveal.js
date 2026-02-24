/**
 * LV Reveal – adds .in-view to .lv-reveal when element enters viewport (fade-in-up).
 */
(function() {
  'use strict';
  var els = document.querySelectorAll('.lv-reveal');
  if (!els.length) return;
  var io = typeof IntersectionObserver !== 'undefined'
    ? new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('in-view');
          }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0 })
    : null;
  if (io) {
    els.forEach(function(el) { io.observe(el); });
  } else {
    els.forEach(function(el) { el.classList.add('in-view'); });
  }
})();
