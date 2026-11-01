/* FAQ accordion — height animation via grid-template-rows, no measuring.
   The markup ships as <button aria-expanded aria-controls> + a panel whose
   grid-template-rows is driven by [data-state]; this script only flips that
   state, so the animation stays in CSS and reduced-motion keeps working. */
(function () {
  'use strict';

  var NAV_KEYS = ['ArrowDown', 'ArrowUp', 'Home', 'End'];

  function panelFor(trigger) {
    var id = trigger.getAttribute('aria-controls');
    return id ? document.getElementById(id) : null;
  }

  function setOpen(trigger, open) {
    trigger.setAttribute('aria-expanded', open ? 'true' : 'false');

    var item = trigger.closest('.faq-accordion__item');
    if (item) item.setAttribute('data-state', open ? 'open' : 'closed');

    var panel = panelFor(trigger);
    if (!panel) return;
    panel.setAttribute('data-state', open ? 'open' : 'closed');
    // A collapsed panel must stay out of the tab order and the a11y tree.
    if (open) panel.removeAttribute('inert');
    else panel.setAttribute('inert', '');
  }

  function initAccordion(root) {
    var triggers = Array.prototype.slice.call(
      root.querySelectorAll('[data-accordion-trigger]')
    );
    if (!triggers.length) return;

    var single = root.getAttribute('data-accordion') === 'single';

    triggers.forEach(function (trigger) {
      setOpen(trigger, trigger.getAttribute('aria-expanded') === 'true');

      trigger.addEventListener('click', function () {
        var willOpen = trigger.getAttribute('aria-expanded') !== 'true';
        if (willOpen && single) {
          triggers.forEach(function (other) {
            if (other !== trigger) setOpen(other, false);
          });
        }
        setOpen(trigger, willOpen);
      });
    });

    // Roving focus between headers (WAI-ARIA accordion pattern). Vertical
    // layout, so the arrow keys are not mirrored for RTL.
    root.addEventListener('keydown', function (event) {
      if (NAV_KEYS.indexOf(event.key) === -1) return;

      var current = triggers.indexOf(document.activeElement);
      if (current === -1) return;

      var next = current;
      if (event.key === 'ArrowDown') next = (current + 1) % triggers.length;
      else if (event.key === 'ArrowUp')
        next = (current - 1 + triggers.length) % triggers.length;
      else if (event.key === 'Home') next = 0;
      else next = triggers.length - 1;

      event.preventDefault();
      triggers[next].focus();
    });
  }

  function init() {
    var roots = document.querySelectorAll('[data-accordion]');
    Array.prototype.forEach.call(roots, initAccordion);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
