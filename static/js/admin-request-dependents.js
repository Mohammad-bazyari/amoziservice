/* Admin request form: brand & problem depend on the chosen service.
   Django's FK dropdowns are emptied server-side (formfield_for_foreignkey);
   this script fills them client-side with the selected service's own rows
   and re-fills whenever the service changes — mirroring the public wizard's
   service-ownership logic so wrong service/brand pairs cannot be saved. */
(function () {
  "use strict";

  var DATA = window.ADMIN_REQUEST_DEPENDENTS || null;

  function option(value, label, selected) {
    var o = document.createElement("option");
    o.value = value == null ? "" : value;
    o.textContent = label;
    if (selected) o.selected = true;
    return o;
  }

  function fillSelect(select, rows, keepValue) {
    if (!select) return;
    var current = keepValue ? select.value : "";
    select.innerHTML = "";
    select.appendChild(option("", "---------", !current));
    rows.forEach(function (row) {
      select.appendChild(option(row.id, row.label, String(row.id) === current));
    });
  }

  function rowsFor(kind, serviceId) {
    if (!DATA) return [];
    return (DATA[kind] || []).filter(function (r) {
      return String(r.service) === String(serviceId);
    });
  }

  function update(serviceId, keepValues) {
    if (!DATA) return;
    var brand = document.querySelector('select[name="brand"]');
    var problem = document.querySelector('select[name="problem"]');
    fillSelect(brand, rowsFor("brands", serviceId), keepValues);
    fillSelect(problem, rowsFor("problems", serviceId), keepValues);
  }

  function init() {
    var service = document.querySelector('select[name="service"]');
    if (!service) return;
    if (!DATA) {
      // Payload injected right before this script by the admin template.
      var payload = document.getElementById("admin-request-dependents");
      if (payload) {
        try { DATA = JSON.parse(payload.textContent); } catch (e) { DATA = null; }
      }
      if (!DATA) return;
    }
    service.addEventListener("change", function () {
      update(service.value, false);
    });
    // Initial fill honors the server-selected service (edit case).
    update(service.value, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
