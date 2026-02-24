/**
 * Side-drawer menu
 */

(function() {
  'use strict';

  const menuBtn = document.querySelector('.menu-btn');
  const drawer = document.getElementById('drawer-menu');
  const overlay = document.getElementById('drawer-overlay');
  const closeBtn = document.getElementById('drawer-close');
  const countryLink = document.getElementById('drawer-country-link');

  if (!menuBtn || !drawer || !overlay) return;

  function setCountry(country) {
    if (countryLink) {
      countryLink.textContent = country;
    }
  }

  var localeToCountry = {
    'en-US': 'United States', 'en-GB': 'United Kingdom', 'en-AU': 'Australia',
    'en-CA': 'Canada', 'en-IN': 'India', 'fr-FR': 'France', 'fr-CA': 'Canada',
    'de-DE': 'Germany', 'de-AT': 'Austria', 'de-CH': 'Switzerland',
    'es-ES': 'Spain', 'es-MX': 'Mexico', 'it-IT': 'Italy', 'ja-JP': 'Japan',
    'zh-CN': 'China', 'zh-TW': 'Taiwan', 'ko-KR': 'South Korea',
    'pt-BR': 'Brazil', 'nl-NL': 'Netherlands'
  };

  function getCountryFromLocale() {
    var locale = (navigator.language || navigator.userLanguage || 'en-US');
    return localeToCountry[locale] || 'United States';
  }

  function detectLocation() {
    fetch('https://ipapi.co/json/')
      .then(function(res) { return res.json(); })
      .then(function(data) {
        if (data && data.country_name && !data.error) {
          setCountry(data.country_name);
        } else {
          setCountry(getCountryFromLocale());
        }
      })
      .catch(function() {
        setCountry(getCountryFromLocale());
      });
  }

  detectLocation();

  function openDrawer() {
    drawer.classList.add('is-open');
    overlay.classList.add('is-open');
    menuBtn.setAttribute('aria-expanded', 'true');
    menuBtn.setAttribute('aria-label', 'Close menu');
    drawer.setAttribute('aria-hidden', 'false');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    drawer.classList.remove('is-open');
    overlay.classList.remove('is-open');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.setAttribute('aria-label', 'Open menu');
    drawer.setAttribute('aria-hidden', 'true');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function toggleDrawer() {
    const isOpen = drawer.classList.contains('is-open');
    if (isOpen) {
      closeDrawer();
    } else {
      openDrawer();
    }
  }

  menuBtn.addEventListener('click', toggleDrawer);
  overlay.addEventListener('click', closeDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer.classList.contains('is-open')) {
      closeDrawer();
    }
  });
})();
