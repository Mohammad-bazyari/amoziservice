/**
 * اعتبارسنجی فرم درخواست — همان رفتار snippet «Form» برای فرم سروری.
 *
 * • اعتبارسنجی هر میدان پس از blur و همه‌ی میدان‌ها هنگام ارسال.
 * • منبع قواعد، خود مرورگر است (validity) به‌علاوه‌ی data-pattern؛ پس قواعد
 *   سرور تکرار نمی‌شوند و از هم جدا نمی‌افتند. سرور همچنان مرجع نهایی است.
 * • خلاصه‌ی خطاها با پیوند به هر میدان؛ کلیک روی پیوند، میدان را فوکوس می‌کند.
 * • میدان‌هایی که سرور برایشان پیام داده، دست‌نخورده می‌مانند (بدون پیام تکراری).
 * • بدون وابستگی؛ اگر این فایل بارگذاری نشود، فرم مثل قبل با اعتبارسنجی سرور کار می‌کند.
 */
(function () {
  "use strict";

  var SUMMARY_ID = "wizard-error-summary";
  var CLIENT_MESSAGES = {
    valueMissing: "این بخش را کامل کنید.",
    patternMismatch: "مقدار واردشده معتبر نیست.",
    tooLong: "متن واردشده بیش از حد بلند است.",
    tooShort: "متن واردشده کوتاه است.",
    notSelected: "یکی از گزینه‌ها را انتخاب کنید.",
    fileType: "فرمت فایل انتخاب‌شده مجاز نیست.",
  };

  /** میدان‌هایی که اعتبارسنجی خودمان روی آن‌ها معنا دارد. */
  var SKIP_TYPES = { hidden: 1, file: 1, submit: 1, button: 1, reset: 1, image: 1 };

  /** خطاهای سمت کلاینت: فرم → (عنصر → پیام). */
  var clientErrors = new WeakMap();

  /* ---------------------------------------------------------------- */
  /* کمکی‌ها                                                           */
  /* ---------------------------------------------------------------- */

  function isRequiredGroup(container) {
    return Boolean(container && container.dataset.required);
  }

  /** یکاهای اعتبارسنجی فرم، به ترتیب ظاهر شدن در صفحه. */
  function unitsOf(form) {
    var units = [];
    var radios = Object.create(null);
    Array.prototype.forEach.call(form.querySelectorAll("input, textarea, select"), function (el) {
      if (SKIP_TYPES[el.type] || el.disabled) return;
      if (el.type === "radio") {
        if (!el.name) return;
        if (!radios[el.name]) {
          radios[el.name] = { el: el, elements: [], group: true };
          units.push(radios[el.name]);
        }
        radios[el.name].elements.push(el);
        return;
      }
      units.push({ el: el, elements: [el], group: false });
    });
    return units;
  }

  function groupContainer(unit) {
    return unit.group ? unit.el.closest("[data-required]") : null;
  }

  /** پیام خطای سرور برای این میدان (قالب آن را با همین شناسه رندر می‌کند). */
  function serverMessageNode(unit) {
    if (!unit.el.id) return null;
    var node = document.getElementById(unit.el.id + "-error");
    if (node && !node.hasAttribute("data-client-error")) return node;
    return null;
  }

  function clientMessageNode(unit) {
    if (!unit.el.id) return null;
    var node = document.getElementById(unit.el.id + "-error");
    if (node && node.hasAttribute("data-client-error")) return node;
    return null;
  }

  /** پیام این میدان طبق قواعد مرورگر + data-pattern؛ "" یعنی سالم. */
  function messageFor(unit) {
    if (unit.group) {
      var container = groupContainer(unit);
      if (!isRequiredGroup(container)) return "";
      var checked = unit.elements.some(function (radio) {
        return radio.checked;
      });
      if (checked) return "";
      return (container.dataset.errorRequired || CLIENT_MESSAGES.notSelected);
    }

    var el = unit.el;
    var validity = el.validity;
    if (validity) {
      if (validity.valueMissing) return el.dataset.errorRequired || CLIENT_MESSAGES.valueMissing;
      if (validity.patternMismatch || validity.typeMismatch || validity.badInput) {
        return el.dataset.errorPattern || CLIENT_MESSAGES.patternMismatch;
      }
      if (validity.tooLong) return el.dataset.errorLong || CLIENT_MESSAGES.tooLong;
      if (validity.tooShort) return el.dataset.errorShort || CLIENT_MESSAGES.tooShort;
      if (validity.valid) {
        return customPatternMessage(el);
      }
    }
    return customPatternMessage(el);
  }

  /**
   * قاعده‌ی اختیاری data-pattern (مثلاً الگوی شماره موبایل).
   * نرمال‌سازی شماره — مرآت apps/requests/phone.py (منبع واحد سرور):
   * «+98» و «0098» و صفرِ گروه‌نگه‌داشته + ارقام فارسی/عربی همگی به
   * «09xxxxxxxxx» می‌رسند تا اعتبارسنجی مرورگر مثل سرور نرمال باشد.
   */
  function normalizeMobileClient(raw) {
    var text = String(raw || "");
    var digits = "";
    for (var i = 0; i < text.length; i += 1) {
      var code = text.charCodeAt(i);
      if (code >= 1632 && code <= 1641) digits += String(code - 1632);        // ارقام عربی
      else if (code >= 1776 && code <= 1785) digits += String(code - 1776);   // ارقام فارسی
      else if (code >= 48 && code <= 57) digits += String.fromCharCode(code); // ارقام لاتین
    }
    var hadPlus = /^\s*\+/.test(text);
    if (digits.indexOf("0098") === 0) digits = digits.slice(4);
    else if (digits.indexOf("98") === 0 && (hadPlus || digits.length === 12)) digits = digits.slice(2);
    if (digits.length === 10 && digits.indexOf("9") === 0) digits = "0" + digits;
    return digits;
  }

  function isPhoneField(el) {
    return Boolean(el && el.hasAttribute("data-phone"));
  }

  function customPatternMessage(el) {
    var pattern = el.dataset.pattern;
    if (!pattern) return "";
    var value = (el.value || "").trim();
    if (!value) return "";
    if (isPhoneField(el)) value = normalizeMobileClient(value);
    var matches;
    try {
      matches = new RegExp("^(?:" + pattern + ")$").test(value);
    } catch (error) {
      return "";
    }
    if (matches) return "";
    return el.dataset.errorPattern || CLIENT_MESSAGES.patternMismatch;
  }

  /** برچسب فارسی میدان برای خلاصه‌ی خطاها. */
  function labelFor(unit) {
    var container = groupContainer(unit);
    if (container && container.dataset.errorLabel) return container.dataset.errorLabel;
    if (unit.el.dataset && unit.el.dataset.errorLabel) return unit.el.dataset.errorLabel;
    if (unit.el.id) {
      var label = document.querySelector('label[for="' + unit.el.id + '"]');
      if (label && label.textContent.trim()) return label.textContent.trim();
    }
    return unit.el.name || unit.el.id || "میدان";
  }

  function describe(unit, messageId) {
    var target = unit.group ? groupContainer(unit) || unit.el : unit.el;
    if (!target) return;
    var current = target.dataset.describedbyKeep;
    if (current === undefined) {
      current = target.getAttribute("aria-describedby") || "";
      target.dataset.describedbyKeep = current;
    }
    var ids = current.split(/\s+/).filter(Boolean);
    if (ids.indexOf(messageId) === -1) ids.push(messageId);
    target.setAttribute("aria-describedby", ids.join(" "));
  }

  function undescribe(unit, messageId) {
    var target = unit.group ? groupContainer(unit) || unit.el : unit.el;
    if (!target) return;
    var current = target.dataset.describedbyKeep || "";
    var ids = current.split(/\s+/).filter(Boolean);
    if (ids.length) target.setAttribute("aria-describedby", ids.join(" "));
    else target.removeAttribute("aria-describedby");
  }

  function markInvalid(unit) {
    if (unit.group) {
      var container = groupContainer(unit);
      if (container) container.setAttribute("aria-invalid", "true");
      return;
    }
    unit.el.setAttribute("aria-invalid", "true");
  }

  function markValid(unit) {
    if (unit.group) {
      var container = groupContainer(unit);
      if (container) container.removeAttribute("aria-invalid");
      return;
    }
    unit.el.removeAttribute("aria-invalid");
  }

  function messageClasses() {
    return [
      "mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700",
      "dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
    ].join(" ");
  }

  /** پیام کلاینت را نشان می‌دهد یا برمی‌دارد (پیام سرور دست‌نخورده می‌ماند). */
  function applyMessage(unit, message) {
    var anchor = unit.group ? groupContainer(unit) || unit.el : unit.el;
    if (!anchor) return;
    var id = unit.el.id ? unit.el.id + "-error" : "";
    var existing = clientMessageNode(unit);

    if (!message) {
      if (existing) {
        existing.remove();
        if (id) undescribe(unit, id);
      }
      markValid(unit);
      return;
    }

    markInvalid(unit);
    if (!id) return;
    if (!existing) {
      existing = document.createElement("p");
      existing.id = id;
      existing.setAttribute("data-client-error", "");
      existing.className = messageClasses();
      existing.setAttribute("role", "alert");
      var host = anchor.closest("[data-field]") || anchor.parentElement || anchor;
      if (host === anchor) anchor.insertAdjacentElement("afterend", existing);
      else host.appendChild(existing);
    }
    existing.textContent = message;
    describe(unit, id);
  }

  /* ---------------------------------------------------------------- */
  /* خلاصه‌ی خطاها                                                     */
  /* ---------------------------------------------------------------- */

  function summaryList() {
    var summary = document.getElementById(SUMMARY_ID);
    if (!summary) return null;
    return summary.querySelector("[data-error-list]") || summary.querySelector("ul");
  }

  function renderSummary(form) {
    var list = summaryList();
    var errors = clientErrors.get(form);
    var items = [];
    if (errors) {
      unitsOf(form).forEach(function (unit) {
        var message = errors.get(unit.el);
        if (message) items.push({ unit: unit, message: message });
      });
    }

    if (list) {
      Array.prototype.forEach.call(
        list.querySelectorAll("li[data-client-error]"),
        function (li) {
          li.remove();
        },
      );
    }

    if (!items.length) return;
    if (!list) {
      list = document.createElement("ul");
      list.setAttribute("data-error-list", "");
      list.className = "mt-2 flex flex-col gap-1.5 ps-6";
      var summary = ensureSummary();
      summary.appendChild(list);
    }
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.setAttribute("data-client-error", "");
      li.className = "list-disc marker:text-red-400";
      var link = document.createElement("a");
      link.href = "#" + item.unit.el.id;
      link.className =
        "font-bold text-red-700 underline underline-offset-4 decoration-red-300 hover:decoration-red-500 dark:text-red-300";
      var label = document.createElement("span");
      label.className = "font-bold";
      label.textContent = labelFor(item.unit) + ": ";
      var text = document.createElement("span");
      text.className = "font-normal";
      text.textContent = item.message;
      link.appendChild(label);
      link.appendChild(text);
      li.appendChild(link);
      list.appendChild(li);
    });
  }

  /** خلاصه را می‌سازد اگر سرور خطایی نداشته و هنوز ساخته نشده باشد. */
  function ensureSummary() {
    var summary = document.getElementById(SUMMARY_ID);
    if (summary) return summary;
    var heading = document.createElement("p");
    heading.id = SUMMARY_ID + "-title";
    heading.className =
      "flex flex-wrap items-center gap-x-2 gap-y-1 font-bold text-red-700 dark:text-red-300";
    heading.textContent = "لطفاً این موارد را اصلاح کنید";
    summary = document.createElement("div");
    summary.id = SUMMARY_ID;
    summary.setAttribute("role", "alert");
    summary.setAttribute("aria-labelledby", heading.id);
    summary.className =
      "rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200";
    summary.appendChild(heading);
    return summary;
  }

  /** خلاصه را داخل فرم (بالای آن) جا می‌دهد. */
  function mountSummary(form) {
    var summary = document.getElementById(SUMMARY_ID);
    var csrf = form.querySelector('input[name="csrfmiddlewaretoken"]');
    var anchor = csrf ? csrf.closest("div") : null;
    var parent = (anchor && anchor.parentElement) || form;
    if (!summary) {
      summary = ensureSummary();
      if (anchor) anchor.insertAdjacentElement("afterend", summary);
      else parent.insertBefore(summary, parent.firstChild);
    }
    if (!summary.querySelector("[data-error-list]") && !summary.querySelector("ul")) {
      var list = document.createElement("ul");
      list.setAttribute("data-error-list", "");
      list.className = "mt-2 flex flex-col gap-1.5 ps-6";
      summary.appendChild(list);
    }
    return summary;
  }

  /* ---------------------------------------------------------------- */
  /* فوکوس و وضعیت                                                     */
  /* ---------------------------------------------------------------- */

  function focusUnit(unit) {
    var target = unit.group ? unit.elements[0] : unit.el;
    if (target && typeof target.focus === "function") target.focus();
  }

  /**
   * فوکوس روی میدان خطادار: اگر هدف خودش کنترل باشد همان، وگرنه اولین
   * کنترل داخلش (مثلاً گروه رادیویی) فوکوس می‌گیرد.
   */
  function focusTarget(target) {
    if (!target) return;
    if (target.matches && target.matches("input, select, textarea")) {
      target.focus();
      return;
    }
    var control = target.querySelector("input:not([type=hidden]), select, textarea");
    if (control) {
      control.focus();
      return;
    }
    if (typeof target.focus === "function") target.focus();
  }

  /**
   * پیوندهای خلاصه‌ی خطاها (چه سروری، چه کلاینتی) کاربر را به همان میدان
   * می‌برند و فوکوس را روی کنترل می‌گذارند.
   */
  function bindSummaryLinks() {
    document.addEventListener("click", function (event) {
      var link = event.target && event.target.closest && event.target.closest("#" + SUMMARY_ID + " a[href^='#']");
      if (!link) return;
      var id = decodeURIComponent((link.getAttribute("href") || "").slice(1));
      var target = id && document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      focusTarget(target);
    });
  }

  function remember(form, unit, message) {
    var errors = clientErrors.get(form);
    if (!errors) {
      errors = new Map();
      clientErrors.set(form, errors);
    }
    if (message) errors.set(unit.el, message);
    else errors.delete(unit.el);
  }

  /** یک میدان را بررسی می‌کند و وضعیت را می‌نویسد. */
  function checkUnit(form, unit) {
    var message = messageFor(unit);
    var hasServerMessage = Boolean(serverMessageNode(unit));
    // اگر سرور پیام داده، پیام دومی اضافه نمی‌کنیم؛ همان خطا معتبر است.
    var shown = hasServerMessage ? "" : message;
    applyMessage(unit, shown);
    remember(form, unit, hasServerMessage ? "" : message);
    return message;
  }

  /* ---------------------------------------------------------------- */
  /* اعلان‌ها (Toast)                                                  */
  /* ---------------------------------------------------------------- */

  /**
   * اعلان خطاها هنگام تلاش برای ارسال: عنوان «ارسال نشد» و توضیح خود مشکل
   * (تا سه مورد؛ مابقی با شمارش فارسی). هر ۵ ثانیه بیش از یک بار اعلام نمی‌شود
   * تا دوباره‌گویی (مثلاً مسیر دوم Alpine) اعلان اضاف نسازد.
   */
  function toastSubmitError(form) {
    if (!window.WizardToast) return;
    var now = Date.now();
    var last = Number(form.dataset.errorToastAt || 0);
    if (now - last < 5000) return;
    form.dataset.errorToastAt = String(now);

    var errors = clientErrors.get(form);
    var parts = [];
    if (errors) {
      unitsOf(form).forEach(function (unit) {
        var message = errors.get(unit.el);
        if (message) parts.push(labelFor(unit) + " " + message);
      });
    }
    if (!parts.length) return;
    var description = parts.slice(0, 3).join("؛ ");
    if (parts.length > 3) description += "؛ و " + faNum(parts.length - 3) + " مورد دیگر";
    window.WizardToast.error("ارسال نشد؛ این موارد را پیش از مرحله‌ی بعد اصلاح کنید", {
      description: description,
    });
  }

  /** ارقام فارسی برای شمارش در اعلان‌ها. */
  function faNum(value) {
    return String(value).replace(/[0-9]/g, function (digit) {
      return "۰۱۲۳۴۵۶۷۸۹"[Number(digit)];
    });
  }

  /**
   * اگر سرور خطا داده و صفحه با خلاصه لود شده، همان را اعلام می‌کنیم تا کاربر
   * (و صفحه‌خوان) توجه کند؛ متن پیام اول + شمارش مابقی.
   */
  function announceServerErrors() {
    if (!window.WizardToast) return;
    var summary = document.getElementById(SUMMARY_ID);
    if (!summary) return;
    var items = summary.querySelectorAll("li");
    if (!items.length) return;
    var first = items[0].textContent.trim();
    var description = first;
    if (items.length > 1) {
      description = first + "؛ و " + faNum(items.length - 1) + " مورد دیگر در خلاصه‌ی زیر فرم";
    }
    window.WizardToast.error("درخواست قبلی ثبت نشد", {
      description: description,
    });
  }

  /** همه‌ی میدان‌ها را بررسی می‌کند؛ در صورت خطا false برمی‌گرداند. */
  function validate(form) {
    mountSummary(form);
    var firstInvalid = null;
    var hasClientErrors = false;

    unitsOf(form).forEach(function (unit) {
      var message = checkUnit(form, unit);
      if (message && !firstInvalid) firstInvalid = unit;
      if (message && !serverMessageNode(unit)) hasClientErrors = true;
    });

    renderSummary(form);

    var summary = document.getElementById(SUMMARY_ID);
    if (summary && !hasClientErrors) {
      // خطاهای سرور باقی می‌مانند؛ فقط وقتی چیزی برای گفتن نیست جمع می‌شود.
      var hasAny = summary.querySelector("li");
      if (!hasAny) {
        summary.remove();
        var list = clientErrors.get(form);
        if (list) list.clear();
      }
    }

    if (firstInvalid) {
      focusUnit(firstInvalid);
      toastSubmitError(form);
      return false;
    }
    return true;
  }

  /* ---------------------------------------------------------------- */
  /* اتصال رویدادها                                                    */
  /* ---------------------------------------------------------------- */

  function unitFor(form, el) {
    var units = unitsOf(form);
    for (var i = 0; i < units.length; i += 1) {
      if (units[i].elements.indexOf(el) !== -1) return units[i];
    }
    return null;
  }

  function scheduleRefresh(form) {
    if (form.dataset.summaryTimer) return;
    form.dataset.summaryTimer = "1";
    window.setTimeout(function () {
      delete form.dataset.summaryTimer;
      mountSummary(form);
      renderSummary(form);
      // همهٔ خطاها رفع شد؟ خلاصه (حتی تهی) دیگر معنی ندارد؛ جمعش می‌کنیم.
      var summary = document.getElementById(SUMMARY_ID);
      if (summary && !summary.querySelector("li")) summary.remove();
    }, 0);
  }

  function init(form) {
    if (!form || form.dataset.wizardReady === "1") return;
    form.dataset.wizardReady = "1";
    announceServerErrors();

    form.addEventListener(
      "focusout",
      function (event) {
        var el = event.target;
        if (!el || !el.matches || !el.matches("input, textarea, select")) return;
        if (SKIP_TYPES[el.type] || el.disabled) return;
        // شماره موبایل: پس از خروج میدان، ورودی با شکل نرمال بازنویسی
        // می‌شود (+98/۹۸ فارسی… همه‌ی شکل‌ها → ۰.maxLength≈۹ لاتین).
        if (isPhoneField(el)) {
          var normalized = normalizeMobileClient(el.value);
          if (normalized && normalized !== el.value && /^09\d{9}$/.test(normalized)) {
            el.value = normalized;
          }
        }
        var unit = unitFor(form, el);
        if (!unit) return;
        checkUnit(form, unit);
        mountSummary(form);
        renderSummary(form);
      },
      true,
    );

    ["input", "change"].forEach(function (type) {
      form.addEventListener(
        type,
        function (event) {
          var el = event.target;
          if (!el || !el.matches || !el.matches("input, textarea, select")) return;
          if (SKIP_TYPES[el.type] || el.disabled) return;
          var unit = unitFor(form, el);
          if (!unit) return;
          // فقط میدانی که قبلاً خطا داشته دوباره بررسی می‌شود (مثل قلاب Form).
          var errors = clientErrors.get(form);
          var tracked = errors && errors.has(unit.el);
          var hasServerMessage = Boolean(serverMessageNode(unit));
          if (!tracked && !hasServerMessage) return;
          if (checkUnit(form, unit)) return;
          scheduleRefresh(form);
        },
        true,
      );
    });

    form.addEventListener("submit", function (event) {
      // مستقل از Alpine جلوی ارسال نامعتبر را می‌گیریم (Alpine هم همان را می‌کند؛
      // هرچه زودتر خود كلاینت بلاک کند، ارسال بره‌ای برای سرور رخ نمی‌دهد). سرور همچنان مرجع نهایی است.
      if (!validate(form)) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }, false);
  }

  function initAll(root) {
    var scope = root && root.querySelectorAll ? root : document;
    Array.prototype.forEach.call(scope.querySelectorAll("form[data-wizard-form]"), init);
  }

  window.WizardForm = {
    validate: validate,
    validateField: function (form, el) {
      var unit = unitFor(form, el);
      if (!unit) return "";
      var message = checkUnit(form, unit);
      mountSummary(form);
      renderSummary(form);
      return message;
    },
    init: initAll,
  };

  bindSummaryLinks();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initAll(document);
    });
  } else {
    initAll(document);
  }
})();
