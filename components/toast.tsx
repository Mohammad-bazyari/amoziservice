"use client";

/**
 * Toast — اعلان‌های راست‌چین (React + Tailwind CSS).
 *
 * قطعه‌ها
 * • ToastProvider + useToast — وضعیت اعلان‌ها با useState؛ هر اعلان یک ویوالنت
 *   دارد: success (موفق) / error (خطا) / warning (هشدار) / info (اطلاع).
 * • ناحیه‌ی اعلان‌ها aria-live="polite" است و در bottom-4 start-4 می‌نشیند
 *   (در RTL یعنی پایین‌چپِ هر دو طرف منطقی؛ همیشه گوشه‌ی «پایین + ابتدای خط»).
 * • Toast — کارت اعلان: آیکن وضعیت، عنوان، توضیح، دکمه‌ی اقدام و دکمه‌ی بستن.
 *   ورود کوتاه از سمت راست (۲۰۰ms) و زیر prefers-reduced-motion بدون حرکت.
 * • صفحه‌کلید: دکمه‌های اقدام و بستن با Tab در دسترس‌اند و Escape هر اعلانِ
 *   فوکوس‌دار (یا داخلش فوکوس‌گذاری‌شده) را می‌بندد.
 * • توقف تایمر روی هاور/فوکوس: کاربر بتواند وقت داشته باشد بخواند.
 *
 * توکن‌های لازم تم (رنگ اختراع نشده است)
 *   background · foreground · muted-foreground · border · ring ·
 *   primary · primary-foreground · destructive
 *
 * قواعد فارسی و RTL
 * • dir="rtl" روی ناحیه‌ی اعلان‌ها؛ جای‌گذاری فقط با ویژگی‌های منطقی
 *   (start/end — هیچ left/right در کلاس‌ها نیست).
 * • متن فارسی؛ هیچ letter-spacing روی متن فارسی اعمال نمی‌شود.
 * • شمارش‌ها با ارقام فارسی (toPersianDigits از ./accordion).
 * • فونت از توکن پروژه (--font-sans = Vazirmatn یا IRANSans).
 *
 * نمونه استفاده
 *
 *   function RequestWizard() {
 *     return (
 *       <ToastProvider aria-label="اعلان‌های فرم درخواست">
 *         <RequestForm />
 *       </ToastProvider>
 *     );
 *   }
 *
 *   function RequestForm() {
 *     const toast = useToast();
 *
 *     function handleSubmit(values) {
 *       if (values.phone && !/^09\d{9}$/.test(values.phone)) {
 *         toast.error("ارسال نشد", {
 *           description: "شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷).",
 *           action: { label: "اصلاح شماره", onClick: () => phoneRef.current?.focus() },
 *         });
 *         return;
 *       }
 *       toast.success("درخواست شما ثبت شد", {
 *         description: "تا دقايقی دیگر برای هماهنگی تماس می‌گیریم.",
 *       });
 *     }
 *     return <Form onSubmit={handleSubmit}>{/* … *}</Form>;
 *   }
 */

import * as React from "react";
import {
  CircleAlert,
  Info,
  CircleCheck,
  TriangleAlert,
  X,
} from "lucide-react";
import { cn, toPersianDigits } from "./accordion";

/* ------------------------------------------------------------------ */
/* انواع                                                               */
/* ------------------------------------------------------------------ */

/** نوع اعلان — آیکن و رنگ وضعیت را تعیین می‌کند. */
export type ToastVariant = "success" | "error" | "warning" | "info";

/** دکمه‌ی اقدام داخل کارت اعلان. */
export type ToastAction = {
  label: string;
  onClick: () => void;
};

export type ToastOptions = {
  /** عنوان فارسی — اصلی‌ترین متن اعلان. */
  title: string;
  /** توضیح کوتاه مکمل (مثلاً خود پیام خطای میدان). */
  description?: string;
  /** دکمه‌ی داخل اعلان (مثلاً «اصلاح شماره»). */
  action?: ToastAction;
  /**
   * مدت نمایش بر حسب میلی‌ثانیه؛ ۰ یعنی خودکار بسته نشود (بستن دستی).
   * پیش‌فرض: ۵۰۰۰ برای عادی و ۶۰۰۰ برای خطا.
   */
  duration?: number;
};

/** هر اعلان در حال نمایش (وضعیت داخلی). */
type ToastItem = {
  id: string;
  options: Required<Pick<ToastOptions, "title">> & ToastOptions;
  variant: ToastVariant;
  /** درست پس از mount روشن می‌شود تا انیمیشن ورود از راست اجرا شود. */
  entered: boolean;
  /** در حال خروج (قبل از حذف از DOM). */
  closing: boolean;
};

/** آنچه useToast برمی‌گرداند. */
export type ToastApi = {
  show: (options: ToastOptions, variant?: ToastVariant) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  success: (
    title: string,
    options?: Omit<ToastOptions, "variant" | "title">,
  ) => string;
  error: (
    title: string,
    options?: Omit<ToastOptions, "variant" | "title">,
  ) => string;
  warning: (
    title: string,
    options?: Omit<ToastOptions, "variant" | "title">,
  ) => string;
  info: (
    title: string,
    options?: Omit<ToastOptions, "variant" | "title">,
  ) => string;
};

/* ------------------------------------------------------------------ */
/* زمینه                                                               */
/* ------------------------------------------------------------------ */

const ToastContext = React.createContext<ToastApi | null>(null);

/** حتماً داخل <ToastProvider> استفاده شود؛ وگرنه خطای واضح می‌دهد. */
export function useToast(componentName = "useToast"): ToastApi {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error(`${componentName} باید داخل <ToastProvider> فراخوانی شود.`);
  }
  return context;
}

/* ------------------------------------------------------------------ */
/* ظاهر کارت                                                          */
/* ------------------------------------------------------------------ */

const VARIANT_META: Record<
  ToastVariant,
  { icon: React.ReactNode; label: string }
> = {
  success: { icon: <CircleCheck aria-hidden="true" />, label: "موفق" },
  error: { icon: <CircleAlert aria-hidden="true" />, label: "خطا" },
  warning: { icon: <TriangleAlert aria-hidden="true" />, label: "هشدار" },
  info: { icon: <Info aria-hidden="true" />, label: "اطلاع" },
};

/** رنگ آیکن/حاشیه فقط از توکن‌های تم: primary برای موفق، destructive برای خطا. */
const VARIANT_ICON_CLASS: Record<ToastVariant, string> = {
  success: "text-primary",
  error: "text-destructive",
  warning: "text-destructive",
  info: "text-muted-foreground",
};

/* ------------------------------------------------------------------ */
/* کارت اعلان                                                          */
/* ------------------------------------------------------------------ */

export type ToastProps = {
  item: ToastItem;
  onClose: (id: string) => void;
  onHoverChange: (id: string, hovering: boolean) => void;
};

function ToastCard({ item, onClose, onHoverChange }: ToastProps) {
  const meta = VARIANT_META[item.variant];
  const id = item.id;
  const titleId = `toast-${id}-title`;
  const descriptionId = item.options.description
    ? `toast-${id}-description`
    : undefined;

  /** Escape → بستن؛ بقیه‌ی کلیدها به رفتار خود دکمه‌ها گذاشته می‌شود. */
  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose(id);
    }
  }

  return (
    <div
      dir="rtl"
      role={item.variant === "error" ? "alert" : "status"}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      onPointerEnter={() => onHoverChange(id, true)}
      onPointerLeave={() => onHoverChange(id, false)}
      onFocus={() => onHoverChange(id, true)}
      onBlur={() => onHoverChange(id, false)}
      className={cn(
        // کارت: رنگ و حاشیه از توکن‌ها؛ سایه‌ی ملایم
        "pointer-events-auto w-full rounded-xl border border-border",
        "bg-background p-3.5 font-sans text-foreground shadow-card",
        // ورود از سمت راست: ۲۰۰ms؛ زیر prefers-reduced-motion بدون حرکت
        "transition-all duration-200 ease-out motion-reduce:transition-none",
        item.closing || !item.entered
          ? "translate-x-4 opacity-0"
          : "translate-x-0 opacity-100",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className={cn(
            "mt-0.5 shrink-0 [&>svg]:size-5 [&>svg]:stroke-[2]",
            VARIANT_ICON_CLASS[item.variant],
          )}
        >
          {/* برچسب وضعیت برای صفحه‌خوان: «حالت: خطا» در sr-only درج می‌شود */}
          {meta.icon}
        </span>
        <div className="min-w-0 flex-1">
          <p id={titleId} className="text-sm font-bold leading-6">
            <span className="sr-only">{`${meta.label}: `}</span>
            {item.options.title}
          </p>
          {item.options.description ? (
            <p
              id={descriptionId}
              className="mt-1 text-xs leading-6 text-muted-foreground"
            >
              {item.options.description}
            </p>
          ) : null}
          {item.options.action ? (
            <button
              type="button"
              onClick={() => {
                item.options.action?.onClick();
                // اقدام با موفقیتِ کاربر تمام شده؛ اعلان دیگر لازم نیست.
                onClose(id);
              }}
              className={cn(
                "mt-2 rounded-lg text-xs font-bold underline",
                "underline-offset-4 decoration-border hover:decoration-foreground",
                "text-primary dark:decoration-primary/40 dark:hover:decoration-primary",
                "outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              {item.options.action.label}
            </button>
          ) : null}
        </div>
        <button
          type="button"
          aria-label="بستن اعلان"
          onClick={() => onClose(id)}
          className={cn(
            "shrink-0 rounded-lg p-1 text-muted-foreground",
            "transition-colors duration-150 motion-reduce:transition-none",
            "hover:bg-muted hover:text-foreground",
            "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          <X aria-hidden="true" className="size-4" />
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* ناحیه‌ی اعلان‌ها (Provider)                                          */
/* ------------------------------------------------------------------ */

const MAX_VISIBLE = 4;

export type ToastProviderProps = {
  children: React.ReactNode;
  className?: string;
  /** برچسب ناحیه برای صفحه‌خوان. */
  "aria-label"?: string;
};

export function ToastProvider({
  children,
  className,
  "aria-label": ariaLabel = "اعلان‌ها",
}: ToastProviderProps) {
  const [items, setItems] = React.useState<ToastItem[]>([]);
  const idRef = React.useRef(0);

  /** تایمر/زمان باقی‌مانده‌ی هر اعلان — برای توقف تایمر روی هاور/فوکوس. */
  const timersRef = React.useRef(new Map<string, number>());
  const remainingRef = React.useRef(new Map<string, number>());
  const startedRef = React.useRef(new Map<string, number>());

  const itemsRef = React.useRef(items);
  itemsRef.current = items;

  const reducedMotion = React.useCallback(
    () =>
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );

  const clearSchedule = React.useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      timersRef.current.delete(id);
    }
    remainingRef.current.delete(id);
    startedRef.current.delete(id);
  }, []);

  /** شروع خروج اعلان (کلاس closing) و سپس حذف کامل از DOM. */
  const startClosing = React.useCallback(
    (id: string) => {
      clearSchedule(id);
      const wait = reducedMotion() ? 0 : 200;
      setItems((previous) =>
        previous.map((item) =>
          item.id === id ? { ...item, closing: true } : item,
        ),
      );
      window.setTimeout(() => {
        setItems((previous) => previous.filter((item) => item.id !== id));
      }, wait);
    },
    [clearSchedule, reducedMotion],
  );

  /** توقف تایمر بستنِ خودکار — کاربر به شنیدن/خواندن مشغول است. */
  const pauseSchedule = React.useCallback((id: string) => {
    const started = startedRef.current.get(id);
    const remaining = remainingRef.current.get(id);
    const timer = timersRef.current.get(id);
    if (!timersRef.current.has(id)) return;
    if (timer !== undefined) window.clearTimeout(timer);
    timersRef.current.delete(id);
    if (started === undefined || remaining === undefined) return;
    remainingRef.current.set(id, Math.max(0, remaining - (Date.now() - started)));
  }, []);

  /** ادامه‌ی تایمر با زمان باقی‌مانده‌ی دقیق (بعد از پایان هاور/فوکوس). */
  const resumeSchedule = React.useCallback(
    (id: string) => {
      if (timersRef.current.has(id)) return;
      const remaining = remainingRef.current.get(id) ?? 0;
      if (remaining <= 0) return;
      startedRef.current.set(id, Date.now());
      timersRef.current.set(
        id,
        window.setTimeout(() => startClosing(id), remaining),
      );
    },
    [startClosing],
  );

  const handleHoverChange = React.useCallback(
    (id: string, hovering: boolean) => {
      if (hovering) pauseSchedule(id);
      else resumeSchedule(id);
    },
    [pauseSchedule, resumeSchedule],
  );

  const dismiss = React.useCallback((id: string) => {
    startClosing(id);
  }, [startClosing]);

  const dismissAll = React.useCallback(() => {
    for (const item of itemsRef.current) startClosing(item.id);
  }, [startClosing]);

  const show = React.useCallback(
    (options: ToastOptions, variant: ToastVariant = "info"): string => {
      idRef.current += 1;
      const id = String(idRef.current);
      const fallback = variant === "error" ? 6000 : 5000;
      const duration = options.duration ?? fallback;

      let item: ToastItem | undefined;
      setItems((previous) => {
        item = { id, options, variant, entered: false, closing: false };
        // بیش از MAX_VISIBLE هم‌زمان نمایش نمی‌دهیم؛ قدیمی‌ها بسته می‌شوند.
        const next = [...previous.filter((previous) => !previous.closing), item];
        if (next.length > MAX_VISIBLE) {
          const doomed = next.slice(0, next.length - MAX_VISIBLE);
          for (const lost of doomed) clearSchedule(lost.id);
          return next.slice(next.length - MAX_VISIBLE);
        }
        return next;
      });

      if (duration > 0) {
        remainingRef.current.set(id, duration);
        startedRef.current.set(id, Date.now());
        timersRef.current.set(
          id,
          window.setTimeout(() => startClosing(id), duration),
        );
      }

      return id;
    },
    [clearSchedule, startClosing],
  );

  const api = React.useMemo<ToastApi>(
    () => ({
      show,
      dismiss,
      dismissAll,
      success: (title, options) => show({ ...options, title }, "success"),
      error: (title, options) => show({ ...options, title }, "error"),
      warning: (title, options) => show({ ...options, title }, "warning"),
      info: (title, options) => show({ ...options, title }, "info"),
    }),
    [dismiss, dismissAll, show],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      {/* ناحیه‌ی اعلان‌ها: aria-live="polite" تا کاربرِ صفحه‌خوان بدون قطعِ کارش
          اعلان‌ها را بشنود. جای‌گذاری با ویژگی‌های منطقی (start در RTL = راست). */}
      <div
        dir="rtl"
        aria-live="polite"
        aria-atomic="false"
        aria-label={ariaLabel}
        className={cn(
          "pointer-events-none fixed bottom-4 start-4 z-50 flex",
          "w-[min(20rem,calc(100vw-2rem))] flex-col gap-2",
          className,
        )}
      >
        {items.map((item) => (
          <ToastEntry key={item.id} item={item} onClose={dismiss} onHoverChange={handleHoverChange} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** اعلان را یک فریم بعد از mount وارد می‌کند تا انیمیشن ورود اجرا شود. */
function ToastEntry(props: ToastProps) {
  const { item } = props;
  const [entered, setEntered] = React.useState(false);
  React.useEffect(() => {
    const frame = window.requestAnimationFrame(() => setEntered(true));
    return () => window.cancelAnimationFrame(frame);
  }, []);
  return <ToastCard {...props} item={{ ...item, entered }} />;
}

export default ToastProvider;
