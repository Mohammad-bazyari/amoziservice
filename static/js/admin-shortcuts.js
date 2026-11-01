/* Admin keyboard shortcuts:
     Ctrl+S / ⌘S          → ذخیره
     Ctrl+E / ⌘E          → ذخیره و ادامهٔ ویرایش (only if that button exists)
     Ctrl+Shift+S / ⌘⇧S   → ذخیره و ایجاد یکی دیگر (only if that button exists)
   Only active on change/add forms (a submit-row with _save exists).
   The browser's own Ctrl+S (save page) is suppressed only here. */
(function () {
  "use strict";

  function clickButton(form, name) {
    var btn = form.querySelector('input[type="submit"][name="' + name + '"]');
    if (!btn) return false;
    btn.click();
    return true;
  }

  function init() {
    // Only on change/add pages: the toolbar with _save exists.
    var saveBtn = document.querySelector('.submit-row input[type="submit"][name="_save"]');
    if (!saveBtn) return;
    var form = saveBtn.closest("form");
    if (!form) return;

    document.addEventListener("keydown", function (ev) {
      var mod = ev.ctrlKey || ev.metaKey;
      if (!mod) return;

      var key = (ev.key || "").toLowerCase();

      if (key === "s" && !ev.shiftKey) {
        ev.preventDefault();
        clickButton(form, "_save");
      } else if (key === "s" && ev.shiftKey) {
        // save and add another, only when the button is present
        var another = form.querySelector('input[type="submit"][name="_addanother"]');
        if (another) {
          ev.preventDefault();
          another.click();
        }
      } else if (key === "e" && !ev.shiftKey) {
        var cont = form.querySelector('input[type="submit"][name="_continue"]');
        if (cont) {
          ev.preventDefault();
          cont.click();
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
