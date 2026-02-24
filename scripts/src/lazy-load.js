(function() {
  'use strict';
  function applyLazy() {
    document.querySelectorAll('img:not(.hero img):not([loading])').forEach(function(img) {
      img.setAttribute('loading', 'lazy');
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyLazy);
  } else {
    applyLazy();
  }
})();
