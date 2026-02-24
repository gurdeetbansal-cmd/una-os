/**
 * Ultra-Luxury Smooth Scrolling
 * Lightweight momentum scrolling with strict boundaries
 * Prioritizes control and stability over momentum
 */

(function() {
  'use strict';

  // Configuration - 30% less momentum, shorter deceleration, strict control
  const DAMPING = 0.28;      // Higher = shorter deceleration, prevents overshoot
  const MOMENTUM_FACTOR = 0.7; // 30% reduction in momentum
  const MIN_VELOCITY = 0.25; // Stops sooner for stability

  let rafId = null;
  let lastScrollTop = 0;
  let lastTime = 0;
  let velocity = 0;
  let isAnimating = false;

  // Get scroll boundaries
  function getScrollBounds() {
    const maxScroll = Math.max(
      0,
      document.documentElement.scrollHeight - window.innerHeight
    );
    return { min: 0, max: maxScroll };
  }

  // Clamp value to strict boundaries
  function clampScroll(value) {
    const { min, max } = getScrollBounds();
    return Math.max(min, Math.min(max, value));
  }

  // Smooth deceleration loop with strict boundaries
  function smoothDecelerate() {
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const { min, max } = getScrollBounds();

    // Apply damping - stronger for shorter deceleration
    velocity *= (1 - DAMPING);

    // Apply 30% momentum reduction (more responsive, less "ice")
    const scaledVelocity = velocity * MOMENTUM_FACTOR;

    // Strict boundary check - stop at edges
    if (currentScrollTop <= min && velocity < 0) {
      velocity = 0;
      window.scrollTo(0, min);
      isAnimating = false;
      return;
    }
    if (currentScrollTop >= max && velocity > 0) {
      velocity = 0;
      window.scrollTo(0, max);
      isAnimating = false;
      return;
    }

    // Continue if velocity is significant
    if (Math.abs(scaledVelocity) > MIN_VELOCITY) {
      const nextScroll = clampScroll(currentScrollTop + scaledVelocity);
      window.scrollTo({
        top: nextScroll,
        behavior: 'auto'
      });

      // Zero velocity if we hit a boundary
      if (nextScroll === min || nextScroll === max) {
        velocity = 0;
        isAnimating = false;
        return;
      }

      rafId = requestAnimationFrame(smoothDecelerate);
      isAnimating = true;
    } else {
      // Snap to boundary if we're very close
      const clamped = clampScroll(currentScrollTop);
      if (clamped !== currentScrollTop) {
        window.scrollTo(0, clamped);
      }
      isAnimating = false;
      velocity = 0;
    }
  }

  // Track scroll velocity (only when user is scrolling, not during our animation)
  function trackScroll() {
    const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const currentTime = performance.now();

    // Don't overwrite velocity during our own animation - causes bounce/glitches
    if (!isAnimating && lastTime > 0) {
      const deltaTime = Math.max(1, currentTime - lastTime) / 16.67;
      const deltaScroll = currentScrollTop - lastScrollTop;

      velocity = deltaScroll / deltaTime;
    }

    lastScrollTop = currentScrollTop;
    lastTime = currentTime;

    // Start smooth deceleration when user stops scrolling
    if (!isAnimating && Math.abs(velocity) > MIN_VELOCITY) {
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
      rafId = requestAnimationFrame(smoothDecelerate);
    }
  }

  // Initialize
  function init() {
    if (!('requestAnimationFrame' in window)) return;

    lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    lastTime = performance.now();

    window.addEventListener('scroll', trackScroll, { passive: true });

    let wheelTimer;
    window.addEventListener('wheel', function() {
      clearTimeout(wheelTimer);
      wheelTimer = setTimeout(function() {
        if (Math.abs(velocity) > MIN_VELOCITY && !isAnimating) {
          if (rafId) {
            cancelAnimationFrame(rafId);
          }
          rafId = requestAnimationFrame(smoothDecelerate);
        }
      }, 100);
    }, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
