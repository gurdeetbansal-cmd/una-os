/**
 * Molecule Zone – fade in data points on scroll
 */

(function() {
  'use strict';

  const section = document.getElementById('molecule-zone');
  if (!section) return;

  const dataPoints = section.querySelectorAll('.molecule-zone__data');
  if (!dataPoints.length) return;

  const observer = new IntersectionObserver(
    function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          dataPoints.forEach(function(el, i) {
            setTimeout(function() {
              el.classList.add('in-view');
            }, i * 150);
          });
        }
      });
    },
    { threshold: 0.2, rootMargin: '0px' }
  );

  observer.observe(section);
})();
