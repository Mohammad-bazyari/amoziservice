/**
 * Osta Service - Expanding Circular Theme Transition (Light / Dark)
 * 
 * - Full light/dark mode persistence via localStorage ('theme').
 * - Respects OS prefers-color-scheme on initial visit when no preference is saved.
 * - Expanding Circular Reveal from button click coordinates via View Transitions API.
 * - Guaranteed expanding circular wipe in BOTH switching directions (Light -> Dark and Dark -> Light).
 * - Full-screen circular overlay fallback for browsers lacking View Transitions.
 * - Concurrency lock: prevents rapid repeated clicks from interrupting transition.
 * - Coordinated rotating morph animation for Sun and Moon icons.
 * - Strictly respects prefers-reduced-motion (instant switch, zero motion).
 * - Cross-tab synchronization via storage event.
 * - Dynamic OS preference change listener.
 * - Accessible ARIA attributes synchronization.
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'theme';
  var isBusy = false;

  function getSystemPreference() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function applyThemeDirect(theme) {
    var meta = document.querySelector('meta[name="color-scheme"]');
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (meta) meta.setAttribute('content', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
      if (meta) meta.setAttribute('content', 'light');
    }

    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {}

    updateToggleButtons(theme);

    // Notify listeners
    try {
      window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: theme } }));
    } catch (e) {}
  }

  function updateToggleButtons(theme) {
    var isDark = theme === 'dark';
    var nextLabel = isDark ? 'فعال کردن حالت روشن' : 'فعال کردن حالت تاریک';
    var nextTitle = isDark ? 'حالت روشن' : 'حالت تاریک';

    var buttons = document.querySelectorAll('.theme-toggle');
    for (var i = 0; i < buttons.length; i++) {
      var btn = buttons[i];
      btn.setAttribute('aria-label', nextLabel);
      btn.setAttribute('title', nextTitle);
      btn.setAttribute('aria-pressed', String(isDark));
    }
  }

  /**
   * Expanding circular reveal fallback for browsers without native View Transitions API.
   * Creates an expanding circular overlay from the toggle origin to seamlessly wipe to the destination theme.
   */
  function runCircularOverlayFallback(theme, originX, originY, endRadius) {
    var isDark = theme === 'dark';
    var overlay = document.createElement('div');
    overlay.className = 'theme-circle-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    overlay.style.backgroundColor = isDark ? '#020617' : '#f8fafc';
    overlay.style.clipPath = 'circle(0px at ' + originX + 'px ' + originY + 'px)';
    document.body.appendChild(overlay);

    var duration = 600;
    if (typeof overlay.animate === 'function') {
      var anim = overlay.animate(
        [
          { clipPath: 'circle(0px at ' + originX + 'px ' + originY + 'px)' },
          { clipPath: 'circle(' + endRadius + 'px at ' + originX + 'px ' + originY + 'px)' }
        ],
        {
          duration: duration,
          easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
          fill: 'forwards'
        }
      );

      // Switch underlying DOM theme once the expanding circle covers the central area
      var themeApplied = false;
      var timer = window.setTimeout(function () {
        applyThemeDirect(theme);
        themeApplied = true;
      }, Math.round(duration * 0.45));

      var finishCleanup = function () {
        if (!themeApplied) applyThemeDirect(theme);
        window.clearTimeout(timer);
        // Quick subtle fade to reveal newly updated DOM cleanly
        var fade = overlay.animate(
          [{ opacity: 1 }, { opacity: 0 }],
          { duration: 150, easing: 'ease-out' }
        );
        fade.finished.finally(function () {
          if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
          isBusy = false;
        });
      };

      if (anim && anim.finished && typeof anim.finished.finally === 'function') {
        anim.finished.finally(finishCleanup);
      } else {
        window.setTimeout(finishCleanup, duration + 50);
      }
    } else {
      // Very legacy browser without Element.animate
      applyThemeDirect(theme);
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      isBusy = false;
    }
  }

  function setTheme(theme, event) {
    var current = getCurrentTheme();
    if (theme === current) return;
    if (isBusy) return; // Prevent rapid repeated clicks from interrupting transition

    var prefersReducedMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Accessibility: user requested reduced motion
    if (prefersReducedMotion) {
      applyThemeDirect(theme);
      return;
    }

    isBusy = true;

    // Determine circular expansion center (click coordinates or button center)
    var originX = window.innerWidth / 2;
    var originY = 0;

    var ev = event || window.event;
    var btn = (ev && ev.target && ev.target.closest && ev.target.closest('.theme-toggle')) ||
              (ev && ev.currentTarget) ||
              document.querySelector('.theme-toggle');

    if (btn) {
      var rect = btn.getBoundingClientRect();
      if (ev && typeof ev.clientX === 'number' && (ev.clientX > 0 || ev.clientY > 0)) {
        originX = ev.clientX;
        originY = ev.clientY;
      } else {
        originX = rect.left + rect.width / 2;
        originY = rect.top + rect.height / 2;
      }
    } else if (ev && typeof ev.clientX === 'number' && (ev.clientX > 0 || ev.clientY > 0)) {
      originX = ev.clientX;
      originY = ev.clientY;
    }

    // Calculate maximum radius to fully cover all 4 viewport corners from origin
    var maxDistX = Math.max(originX, window.innerWidth - originX);
    var maxDistY = Math.max(originY, window.innerHeight - originY);
    var endRadius = Math.ceil(Math.hypot(maxDistX, maxDistY)) + 2;

    var supportsViewTransitions = typeof document.startViewTransition === 'function';

    if (!supportsViewTransitions) {
      runCircularOverlayFallback(theme, originX, originY, endRadius);
      return;
    }

    document.documentElement.classList.add('theme-view-transition');

    var transition;
    try {
      transition = document.startViewTransition(function () {
        applyThemeDirect(theme);
      });
    } catch (err) {
      document.documentElement.classList.remove('theme-view-transition');
      runCircularOverlayFallback(theme, originX, originY, endRadius);
      return;
    }

    transition.ready.then(function () {
      var anim;
      try {
        anim = document.documentElement.animate(
          {
            clipPath: [
              'circle(0px at ' + originX + 'px ' + originY + 'px)',
              'circle(' + endRadius + 'px at ' + originX + 'px ' + originY + 'px)'
            ]
          },
          {
            duration: 650,
            easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
            pseudoElement: '::view-transition-new(root)'
          }
        );
      } catch (animErr) {
        // Fallback gracefully if pseudoElement in animate() isn't supported in this browser version
      }

      var cleanup = function () {
        document.documentElement.classList.remove('theme-view-transition');
        isBusy = false;
      };

      if (transition.finished && typeof transition.finished.finally === 'function') {
        transition.finished.finally(cleanup);
      } else if (anim && anim.finished && typeof anim.finished.finally === 'function') {
        anim.finished.finally(cleanup);
      } else {
        window.setTimeout(cleanup, 700);
      }
    }).catch(function () {
      document.documentElement.classList.remove('theme-view-transition');
      isBusy = false;
    });
  }

  function toggleTheme(event) {
    var next = getCurrentTheme() === 'dark' ? 'light' : 'dark';
    setTheme(next, event);
  }

  // Sync state on load
  function initTheme() {
    var current = getCurrentTheme();
    updateToggleButtons(current);

    // Watch OS system preference changes (only adapts if user hasn't explicitly set localStorage)
    if (window.matchMedia) {
      var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      var handleOSChange = function (e) {
        if (!getSavedTheme()) {
          var osTheme = e.matches ? 'dark' : 'light';
          applyThemeDirect(osTheme);
        }
      };
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleOSChange);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleOSChange);
      }
    }

    // Cross-tab synchronization
    window.addEventListener('storage', function (e) {
      if (e.key === STORAGE_KEY) {
        var newTheme = e.newValue || getSystemPreference();
        if (newTheme !== getCurrentTheme()) {
          applyThemeDirect(newTheme);
        }
      }
    });
  }

  // Expose API
  window.toggleTheme = toggleTheme;
  window.setTheme = setTheme;
  window.getCurrentTheme = getCurrentTheme;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
})();
