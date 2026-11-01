/* Marquee navigation — manual prev/next for the brand logo strip.
   Controls the brand marquee on the homepage:
   - Steps smoothly forward/backward by one brand item on button click.
   - Seamlessly pauses the CSS infinite drift during user interaction.
   - Resumes continuous drifting from the exact same position after 2.2s idle.
   - Full keyboard accessibility and touch swipe support.
   - Respects prefers-reduced-motion. */
(function () {
  'use strict';

  function initMarqueeNav() {
    var carousels = document.querySelectorAll('.brand-marquee--autoslider');
    for (var i = 0; i < carousels.length; i++) {
      setupCarousel(carousels[i]);
    }
  }

  function setupCarousel(carousel) {
    var container = carousel.closest('[data-marquee-id]') || carousel.parentElement;
    var track = carousel.querySelector('.brand-marquee__track');
    var nextBtn = container.querySelector('[data-marquee-next]');
    var prevBtn = container.querySelector('[data-marquee-prev]');

    if (!track || !nextBtn || !prevBtn) return;

    // Animation configuration
    var ANIM_DURATION_SEC = 30; // Matches CSS: brand-marquee-scroll 30s linear infinite
    var prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var groupWidth = 0;
    var stepDistance = 0;
    var activeTx = 0;
    var isManual = false;
    var resumeTimer = null;
    var wrapTimer = null;
    var isHoveredOrFocused = false;

    function measure() {
      var firstGroup = track.querySelector('.brand-marquee__group');
      if (firstGroup) {
        groupWidth = firstGroup.getBoundingClientRect().width;
      }
      if (!groupWidth || groupWidth <= 0) {
        groupWidth = (track.scrollWidth || 0) / 2;
      }

      var item = track.querySelector('.brand-marquee__item');
      if (item) {
        var style = window.getComputedStyle(item);
        var ml = parseFloat(style.marginLeft) || 0;
        var mr = parseFloat(style.marginRight) || 0;
        stepDistance = item.getBoundingClientRect().width + ml + mr;
      }
      if (!stepDistance || stepDistance <= 0) {
        stepDistance = 200; // Sensible default fallback
      }
    }

    measure();
    window.addEventListener('resize', measure, { passive: true });
    window.addEventListener('load', measure, { passive: true });

    // Extract current translateX in pixels from computed transform matrix
    function getCurrentTx() {
      var style = window.getComputedStyle(track);
      var transform = style.transform || style.webkitTransform;
      if (!transform || transform === 'none') return 0;
      try {
        if (window.DOMMatrix) {
          return new DOMMatrix(transform).m41 || 0;
        }
      } catch (e) {}
      var match = transform.match(/matrix.*\((.+)\)/);
      if (match) {
        var parts = match[1].split(',').map(function (s) {
          return parseFloat(s.trim());
        });
        if (parts.length === 6) return parts[4]; // 2D tx
        if (parts.length === 16) return parts[12]; // 3D tx
      }
      return 0;
    }

    // Switch from CSS continuous animation to manual inline transform
    function enterManualMode() {
      if (!isManual) {
        var currentTx = getCurrentTx();
        if (groupWidth > 0) {
          currentTx = ((currentTx % groupWidth) + groupWidth) % groupWidth;
        }
        track.style.animation = 'none';
        track.style.transition = 'none';
        track.style.transform = 'translateX(' + currentTx + 'px)';
        // Force reflow
        void track.offsetHeight;
        activeTx = currentTx;
        isManual = true;
      }
    }

    // Step forward or backward by one card
    // direction > 0: Next (moves track rightward, revealing next brands)
    // direction < 0: Prev (moves track leftward, revealing previous brands)
    function step(direction) {
      if (groupWidth <= 0) measure();
      enterManualMode();

      if (resumeTimer) clearTimeout(resumeTimer);
      if (wrapTimer) clearTimeout(wrapTimer);

      var delta = direction * (stepDistance || 200);

      // Boundary check to prevent exposing blank space at track edges
      // In RTL, items are in [0, groupWidth].
      // If moving left (direction < 0) and activeTx < |delta|:
      if (direction < 0 && activeTx < Math.abs(delta)) {
        activeTx += groupWidth;
        track.style.transition = 'none';
        track.style.transform = 'translateX(' + activeTx + 'px)';
        void track.offsetHeight;
      }

      activeTx += delta;

      // Animate smoothly
      var duration = prefersReducedMotion ? '0.1s' : '0.4s';
      track.style.transition = 'transform ' + duration + ' cubic-bezier(0.16, 1, 0.3, 1)';
      track.style.transform = 'translateX(' + activeTx + 'px)';

      // After transition finishes, seamlessly normalize activeTx within [0, groupWidth)
      wrapTimer = setTimeout(function () {
        if (groupWidth > 0) {
          if (activeTx >= groupWidth || activeTx < 0) {
            activeTx = ((activeTx % groupWidth) + groupWidth) % groupWidth;
            track.style.transition = 'none';
            track.style.transform = 'translateX(' + activeTx + 'px)';
            void track.offsetHeight;
          }
        }
      }, 420);

      // Schedule auto-scroll resumption if user is not hovering/focusing
      scheduleResume();
    }

    function scheduleResume() {
      if (resumeTimer) clearTimeout(resumeTimer);
      if (prefersReducedMotion) return;

      resumeTimer = setTimeout(function () {
        if (!isHoveredOrFocused) {
          resumeAutoScroll();
        }
      }, 2200);
    }

    function resumeAutoScroll() {
      if (!isManual || prefersReducedMotion) return;
      if (groupWidth <= 0) measure();

      var normalizedTx = groupWidth > 0 ? ((activeTx % groupWidth) + groupWidth) % groupWidth : 0;
      var progress = groupWidth > 0 ? normalizedTx / groupWidth : 0;
      var delaySeconds = -(progress * ANIM_DURATION_SEC);

      track.style.transition = 'none';
      track.style.transform = '';
      track.style.animation = 'brand-marquee-scroll ' + ANIM_DURATION_SEC + 's linear infinite';
      track.style.animationDelay = delaySeconds + 's';
      isManual = false;
    }

    // Button event handlers
    nextBtn.addEventListener('click', function (e) {
      e.preventDefault();
      step(1); // Forward / Next
    });

    prevBtn.addEventListener('click', function (e) {
      e.preventDefault();
      step(-1); // Backward / Prev
    });

    // Hover & focus management
    function onInteractionStart() {
      isHoveredOrFocused = true;
      if (resumeTimer) clearTimeout(resumeTimer);
    }

    function onInteractionEnd() {
      isHoveredOrFocused = false;
      if (isManual) {
        scheduleResume();
      }
    }

    carousel.addEventListener('mouseenter', onInteractionStart, { passive: true });
    carousel.addEventListener('mouseleave', onInteractionEnd, { passive: true });
    carousel.addEventListener('focusin', onInteractionStart, { passive: true });
    carousel.addEventListener('focusout', onInteractionEnd, { passive: true });

    nextBtn.addEventListener('mouseenter', onInteractionStart, { passive: true });
    nextBtn.addEventListener('mouseleave', onInteractionEnd, { passive: true });
    prevBtn.addEventListener('mouseenter', onInteractionStart, { passive: true });
    prevBtn.addEventListener('mouseleave', onInteractionEnd, { passive: true });

    // Keyboard support on the buttons and carousel
    function handleKeyDown(e) {
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        step(1);
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        step(-1);
      }
    }
    carousel.addEventListener('keydown', handleKeyDown);

    // Touch swipe support for mobile
    var touchStartX = 0;
    var touchStartY = 0;
    carousel.addEventListener('touchstart', function (e) {
      if (e.touches && e.touches.length === 1) {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        onInteractionStart();
      }
    }, { passive: true });

    carousel.addEventListener('touchend', function (e) {
      if (e.changedTouches && e.changedTouches.length === 1) {
        var deltaX = e.changedTouches[0].clientX - touchStartX;
        var deltaY = e.changedTouches[0].clientY - touchStartY;
        // Check for primarily horizontal swipe
        if (Math.abs(deltaX) > 40 && Math.abs(deltaX) > Math.abs(deltaY)) {
          if (deltaX > 0) {
            step(1); // Swiped right -> advance
          } else {
            step(-1); // Swiped left -> reverse
          }
        }
      }
      onInteractionEnd();
    }, { passive: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMarqueeNav);
  } else {
    initMarqueeNav();
  }
})();
