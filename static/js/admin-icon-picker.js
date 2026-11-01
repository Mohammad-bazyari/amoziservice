/* Admin icon picker: clicking a tile stores the lucide name in the hidden
   `icon` field and previews every tile. Icons hydrate from the same bundled
   window.LUCIDE_ICONS map the public site uses. */
(function () {
  "use strict";

  function hydrateIcons(root) {
    var nodes = (root || document).querySelectorAll("svg[data-lucide]");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var markup = window.LUCIDE_ICONS && window.LUCIDE_ICONS[el.getAttribute("data-lucide")];
      if (markup && !el.firstChild) el.innerHTML = markup;
    }
  }

  function initPicker(picker) {
    var store = document.getElementById("id_icon_store");
    if (!store) return;
    var options = picker.querySelectorAll(".b-icon-opt input");
    options.forEach(function (radio) {
      radio.addEventListener("change", function () {
        if (radio.checked) store.value = radio.value;
      });
    });
    // Keep store in sync if the form re-renders with a server error.
    if (store.value && !picker.querySelector(".b-icon-opt input:checked")) {
      options.forEach(function (radio) {
        radio.checked = radio.value === store.value;
      });
    }
  }

  function initAll() {
    document.querySelectorAll("[data-icon-picker]").forEach(initPicker);
    hydrateIcons(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
  }
  // Re-hydrate after Django admin's dynamic formset rows appear.
  document.addEventListener("formset:added", function () { initAll(); });
})();
