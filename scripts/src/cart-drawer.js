/**
 * Cart Drawer
 * Toggles .active class to slide drawer in/out using transform.
 * CSS: translateX(100%) = closed (off-screen right), translateX(0) = open.
 */

(function() {
  'use strict';

  const cartToggle = document.getElementById('cart-toggle');
  const cartDrawer = document.getElementById('cart-drawer');
  const cartOverlay = document.getElementById('cart-overlay');
  const cartClose = document.getElementById('cart-close');

  if (!cartToggle || !cartDrawer || !cartOverlay) return;

  function openCart() {
    cartDrawer.classList.add('active');
    cartOverlay.classList.add('active');
    cartDrawer.setAttribute('aria-hidden', 'false');
    cartOverlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeCart() {
    cartDrawer.classList.remove('active');
    cartOverlay.classList.remove('active');
    cartDrawer.setAttribute('aria-hidden', 'true');
    cartOverlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  function toggleCart(e) {
    e.preventDefault();
    if (cartDrawer.classList.contains('active')) {
      closeCart();
    } else {
      openCart();
    }
  }

  cartToggle.addEventListener('click', toggleCart);
  cartOverlay.addEventListener('click', closeCart);
  if (cartClose) cartClose.addEventListener('click', closeCart);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && cartDrawer.classList.contains('active')) {
      closeCart();
    }
  });
})();
