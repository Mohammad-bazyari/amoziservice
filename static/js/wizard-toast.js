/**
 * اعلان‌های (Toast) فرم درخواست — نسخه‌ی vanilla از کامپوننت React «Toast».
 *
 * همان رفتار کامپوننت React (components/toast.tsx) برای فرم سروری:
 * • ناحیه‌ی aria-live="polite" در گوشه‌ی پایین و ابتدای خط (bottom-4 start-4).
 * • کارت با آیکن وضعیت، عنوان، توضیح، دکمه‌ی اقدام و دکمه‌ی بستن.
 * • ورود کوتاه از سمت راست (۲۰۰ms) و بسته‌شدن خودکار؛ تایمر روی هاور/فوکوس
 *   نگه می‌دارد تا کاربر وقت بخواند.
 * • Escape اعلان فوکوس‌دار را می‌بندد؛ دکمه‌ی بستن و اقدام با Tab در دسترس‌اند.
 * • رنگ‌ها فقط از توکن‌های فعلی تم (slate/brand/cta/red)؛ حرکت‌ها ۲۰۰ms و
 *   زیر prefers-reduced-motion بدون انیمیشن.
 *
 * استفاده (بدون وابستگی):
 *   WizardToast.success("عنوان", { description: "..." });
 *   WizardToast.error("ارسال نشد", { description: "…", action: {label, onClick} });
 *   WizardToast.show({ variant: "info", title: "..." });
 * بدون JS هم فرم سروری کار می‌کند؛ این فقط بهبود UX است (progressive enhancement).
 */
(function () {
  "use strict";

  var MAX_VISIBLE = 4;
  var EXIT_MS = 200;
  var FALLBACK_DURATION = { error: 6000, success: 5000, warning: 5000, info: 5000 };

  /* آیکن‌های لازم — از باندل lucide-icons.js؛ اگر نبود مسیر خودمان. */
  var FALLBACK_ICONS = {
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "circle-alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "triangle-alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  };

  var VARIANT_META = {
    success: { icon: "circle-check", role: "status", statusLabel: "موفق", iconClass: "text-brand-600 dark:text-brand-400" },
    error: { icon: "circle-alert", role: "alert", statusLabel: "خطا", iconClass: "text-red-600 dark:text-red-400" },
    warning: { icon: "triangle-alert", role: "status", statusLabel: "هشدار", iconClass: "text-cta-600 dark:text-cta-400" },
    info: { icon: "info", role: "status", statusLabel: "اطلاع", iconClass: "text-slate-500 dark:text-slate-400" },
  };

  /* ------------------------------------------------------------ */
  /* ارقام فارسی                                                    */
  /* ------------------------------------------------------------ */

  var PERSIAN = "۰۱۲۳۴۵۶۷۸۹";
  function faDigits(value) {
    return String(value).replace(/[0-9]/g, function (d) { return PERSIAN[Number(d)]; });
  }

  /* ------------------------------------------------------------ */
  /* ناحیه‌ی اعلان‌ها                                                */
  /* ------------------------------------------------------------ */

  var viewport = null;
  var idCounter = 0;
  var schedules = new Map(); // id → {timer, remaining, startedAt}

  function ensureViewport() {
    if (viewport) return viewport;
    viewport = document.createElement("div");
    viewport.dir = "rtl";
    viewport.setAttribute("aria-live", "polite");
    viewport.setAttribute("aria-atomic", "false");
    viewport.setAttribute("aria-label", "اعلان‌ها");
    viewport.className =
      "pointer-events-none fixed bottom-4 start-4 z-50 flex flex-col gap-2 " +
      "w-[min(20rem,calc(100vw-2rem))]";
    document.body.appendChild(viewport);
    return viewport;
  }

  function createIcon(name) {
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("data-lucide", name);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("class", "h-5 w-5 shrink-0");
    var markup = (window.LUCIDE_ICONS && window.LUCIDE_ICONS[name]) || FALLBACK_ICONS[name];
    if (markup) svg.innerHTML = markup;
    return svg;
  }

  /* ------------------------------------------------------------ */
  /* تایمر (توقف روی هاور/فوکوس)                                    */
  /* ------------------------------------------------------------ */

  function prefersReducedMotion() {
    return typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function clearSchedule(id) {
    var schedule = schedules.get(id);
    if (!schedule) return;
    if (schedule.timer !== undefined) window.clearTimeout(schedule.timer);
    schedules.delete(id);
  }

  /** شروع خروج: کلاس closing و سپس حذف از DOM. */
  function startClosing(id, toastNode) {
    clearSchedule(id);
    if (toastNode.parentNode) {
      var done = function () {
        if (toastNode.parentNode) toastNode.parentNode.removeChild(toastNode);
      };
      if (prefersReducedMotion()) done();
      else {
        toastNode.classList.add("opacity-0", "translate-x-4");
        window.setTimeout(done, EXIT_MS);
      }
    }
  }

  function pauseSchedule(id, toastNode) {
    var schedule = schedules.get(id);
    if (schedule) {
      if (schedule.timer !== undefined) window.clearTimeout(schedule.timer);
      schedule.timer = undefined;
      schedule.remaining = Math.max(0, schedule.remaining - (Date.now() - schedule.startedAt));
    }
  }

  function resumeSchedule(id) {
    var schedule = schedules.get(id);
    if (!schedule || schedule.timer !== undefined || schedule.remaining <= 0) return;
    schedule.startedAt = Date.now();
    schedule.timer = window.setTimeout(function () {
      startClosing(id, schedule.node);
    }, schedule.remaining);
  }

  /* ------------------------------------------------------------ */
  /* کارت اعلان                                                     */
  /* ------------------------------------------------------------ */

  function keyboardHandlerFor(id, toastNode) {
    return function (event) {
      if (event.key === "Escape") {
        event.stopPropagation();
        startClosing(id, toastNode);
      }
    };
  }

  function renderToast(options, variant) {
    ensureViewport();
    idCounter += 1;
    var id = "wt-" + idCounter;
    var meta = VARIANT_META[variant] || VARIANT_META.info;

    var card = document.createElement("div");
    card.dir = "rtl";
    card.setAttribute("role", meta.role);
    card.setAttribute("aria-labelledby", id + "-title");
    if (options.description) card.setAttribute("aria-describedby", id + "-description");
    card.tabIndex = -1;
    card.className =
      "pointer-events-auto w-full rounded-xl border border-slate-200 bg-white " +
      "p-3.5 shadow-card text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 " +
      "transition-all duration-200 ease-out motion-reduce:transition-none";
    // ورود از سمت راست: ابتدا از جای نهایی، کمی در سمت راست و کم‌رنگ.
    card.classList.add("opacity-0", "translate-x-4");

    var row = document.createElement("div");
    row.className = "flex items-start gap-3";

    var iconWrap = document.createElement("span");
    iconWrap.className = "mt-0.5 shrink-0 " + meta.iconClass;
    iconWrap.setAttribute("aria-hidden", "true");
    iconWrap.textContent = "";
    iconWrap.appendChild(createIcon(meta.icon));

    var body = document.createElement("div");
    body.className = "min-w-0 flex-1";

    var title = document.createElement("p");
    title.id = id + "-title";
    title.className = "text-sm font-bold leading-6";
    var srStatus = document.createElement("span");
    srStatus.className = "sr-only";
    srStatus.textContent = meta.statusLabel + ": ";
    title.appendChild(srStatus);
    title.appendChild(document.createTextNode(options.title || ""));

    body.appendChild(title);
    if (options.description) {
      var description = document.createElement("p");
      description.id = id + "-description";
      description.className = "mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400";
      description.textContent = options.description;
      body.appendChild(description);
    }
    if (options.action && options.action.label) {
      var actBtn = document.createElement("button");
      actBtn.type = "button";
      actBtn.className =
        "mt-2 rounded-lg text-xs font-bold text-brand-700 underline underline-offset-4 " +
        "decoration-brand-300 hover:decoration-brand-500 dark:text-brand-300 dark:decoration-brand-700 " +
        "outline-none focus-visible:ring-2 focus-visible:ring-brand-500 " +
        "focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900";
      actBtn.textContent = options.action.label;
      actBtn.addEventListener("click", function (event) {
        event.stopPropagation();
        if (typeof options.action.onClick === "function") options.action.onClick();
        startClosing(id, card);
      });
      body.appendChild(actBtn);
    }

    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.setAttribute("aria-label", "بستن اعلان");
    closeBtn.className =
      "shrink-0 rounded-lg p-1 text-slate-400 transition-colors duration-150 motion-reduce:transition-none " +
      "hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200 " +
      "outline-none focus-visible:ring-2 focus-visible:ring-brand-500 " +
      "focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900";
    var closeIcon = createIcon("x");
    closeIcon.setAttribute("class", "h-4 w-4 shrink-0");
    closeBtn.appendChild(closeIcon);
    closeBtn.addEventListener("click", function (event) {
      event.stopPropagation();
      startClosing(id, card);
    });

    row.appendChild(iconWrap);
    row.appendChild(body);
    row.appendChild(closeBtn);
    card.appendChild(row);
    card.dataset.toastId = id;

    /* ورود انیمیشنی: یک فریم بعد از mount کلاس‌های انتقال برداشته می‌شود. */
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        card.classList.remove("opacity-0", "translate-x-4");
      });
    });

    /* توقف تایمر روی هاور/فوکوس — مطابق کامپوننت React. */
    card.addEventListener("keydown", keyboardHandlerFor(id, card));
    card.addEventListener("pointerenter", function () { pauseSchedule(id, card); });
    card.addEventListener("pointerleave", function () { resumeSchedule(id); });
    card.addEventListener("focusin", function () { pauseSchedule(id, card); });
    card.addEventListener("focusout", function () { resumeSchedule(id); });

    viewport.appendChild(card);

    /* بستنِ خودکار + محدودکردن تعداد هم‌زمان. */
    var duration = options.duration !== undefined
      ? options.duration
      : (FALLBACK_DURATION[variant] || 5000);
    while (viewport.children.length > MAX_VISIBLE) {
      var oldest = viewport.children[0];
      if (oldest && oldest.dataset.toastId) startClosing(oldest.dataset.toastId, oldest);
      else { oldest && oldest.remove && oldest.remove(); break; }
    }
    card.dataset.toastId = id;
    var schedule = { remaining: duration, startedAt: Date.now(), timer: undefined, node: card };
    schedules.set(id, schedule);
    if (duration > 0) {
      schedule.timer = window.setTimeout(function () {
        startClosing(id, card);
      }, duration);
    }

    return id;
  }

  /* ------------------------------------------------------------ */
  /* API                                                            */
  /* ------------------------------------------------------------ */

  function show(options, variant) {
    var actual = variant || (options && options.variant) || "info";
    if (!VARIANT_META[actual]) actual = "info";
    return renderToast(options || {}, actual);
  }

  window.WizardToast = {
    show: show,
    success: function (title, options) {
      return show(Object.assign({ title: title }, options || {}), "success");
    },
    error: function (title, options) {
      return show(Object.assign({ title: title }, options || {}), "error");
    },
    warning: function (title, options) {
      return show(Object.assign({ title: title }, options || {}), "warning");
    },
    info: function (title, options) {
      return show(Object.assign({ title: title }, options || {}), "info");
    },
    dismiss: function (id) {
      var node = viewport && viewport.querySelector('[data-toast-id="' + id + '"]');
      if (node) startClosing(id, node);
    },
    faDigits: faDigits,
    /** شماره سازگاری: بستن همه — فعلاً لازم نداریم؛ برای API کامل. */
    dismissAll: function () {
      if (!viewport) return;
      Array.prototype.forEach.call(viewport.children, function (node) {
        startClosing(node.dataset.toastId || "", node);
      });
    },
  };

  /* ناحیه از همان ابتدا آماده باشد تا اعلان‌های زودهنگام اعلام شوند. */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureViewport);
  } else {
    ensureViewport();
  }
})();
