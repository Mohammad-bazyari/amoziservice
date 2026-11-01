"use client";

/**
 * Accordion — آکاردئون دسترس‌پذیر برای رابط‌های راست‌چین.
 *
 * ویژگی‌ها
 * • ارتفاع فقط با `grid-template-rows: 0fr → 1fr` باز و بسته می‌شود؛ هیچ
 *   اندازه‌گیری جاوااسکریپتی (scrollHeight/offsetHeight) انجام نمی‌شود، پس اگر
 *   ارتفاع محتوا حین انیمیشن تغییر کند هم درست کار می‌کند.
 * • تریگر یک button واقعی با aria-expanded و aria-controls است.
 * • شورون در سمت چپ می‌نشیند (در RTL انتهای خط) و در حالت باز ۱۸۰ درجه می‌چرخد.
 * • ناوبری کامل با صفحه‌کلید: Enter/Space (بومی دکمه) و ArrowUp/ArrowDown/Home/End.
 * • همه‌ی رنگ‌ها از توکن‌های تم می‌آیند (bg-background، border-border، text-muted-foreground و…).
 * • حرکت ۲۰۰ میلی‌ثانیه است و زیر prefers-reduced-motion خاموش می‌شود.
 * • محتوای بسته با inert از دسترس صفحه‌کلید و صفحه‌خوان خارج می‌شود.
 *
 * نمونه استفاده
 *
 *   <Accordion type="single" defaultOpen={["fee"]} aria-label="پرسش‌های متداول">
 *     <AccordionItem value="fee" title="هزینه عیب‌یابی چقدر است؟">
 *       هزینه عیب‌یابی {formatToman(350000)} است و پیش از شروع کار اعلام می‌شود.
 *     </AccordionItem>
 *     <AccordionItem value="time" title="چقدر طول می‌کشد؟">
 *       معمولاً همان روز کاری.
 *     </AccordionItem>
 *   </Accordion>
 *
 * جهت صفحه را روی <html dir="rtl" lang="fa"> بگذارید و فونت پروژه («Vazirmatn» یا
 * «IRANSans») را روی توکن --font-sans تعریف کنید تا font-sans همان فونت شود.
 */

import * as React from "react";
import { ChevronLeft } from "lucide-react";

/* ------------------------------------------------------------------ */
/* ابزارهای فارسی                                                      */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;

/** جداکننده‌ی هزارگان فارسی (U+066C) — نه کاما. */
export const THOUSANDS_SEPARATOR = "٬";

/** ارقام لاتین را به ارقام فارسی (۰–۹) تبدیل می‌کند. */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

/**
 * مبلغ را با ارقام فارسی، جداکننده‌ی «٬» و واحد «تومان» برمی‌گرداند.
 *   formatToman(350000)          // ۳۵۰٬۰۰۰ تومان
 *   formatToman(350000, { unit: false }) // ۳۵۰٬۰۰۰
 */
export function formatToman(
  amount: number,
  options: { unit?: boolean } = {},
): string {
  const { unit = true } = options;
  const grouped = new Intl.NumberFormat("en-US")
    .format(Math.abs(Math.round(amount)))
    .replace(/,/g, THOUSANDS_SEPARATOR);
  const formatted = `${amount < 0 ? "−" : ""}${toPersianDigits(grouped)}`;
  return unit ? `${formatted} تومان` : formatted;
}

/** ادغام کلاس‌های شرطی بدون وابستگی اضافه. */
export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ */
/* زمینه‌ی آکاردئون                                                    */
/* ------------------------------------------------------------------ */

type AccordionContextValue = {
  openValues: string[];
  toggle: (value: string) => void;
};

const AccordionContext = React.createContext<AccordionContextValue | null>(null);

function useAccordionContext(componentName: string): AccordionContextValue {
  const context = React.useContext(AccordionContext);
  if (!context) {
    throw new Error(`${componentName} باید داخل <Accordion> رندر شود.`);
  }
  return context;
}

/* ------------------------------------------------------------------ */
/* ریشه                                                               */
/* ------------------------------------------------------------------ */

export type AccordionProps = {
  children: React.ReactNode;
  /** single: فقط یک پنل باز می‌ماند. multiple: چند پنل هم‌زمان. */
  type?: "single" | "multiple";
  /** مقدار آیتم‌هایی که در شروع باز باشند (state غیرکنترل‌شده). */
  defaultOpen?: string[];
  /** state کنترل‌شده. */
  value?: string[];
  onValueChange?: (value: string[]) => void;
  className?: string;
  "aria-label"?: string;
};

export function Accordion({
  children,
  type = "multiple",
  defaultOpen = [],
  value,
  onValueChange,
  className,
  ...rest
}: AccordionProps) {
  const [uncontrolledValue, setUncontrolledValue] =
    React.useState<string[]>(defaultOpen);
  const isControlled = value !== undefined;
  const openValues = isControlled ? value : uncontrolledValue;
  const rootRef = React.useRef<HTMLDivElement>(null);

  const commit = React.useCallback(
    (next: string[]) => {
      if (!isControlled) setUncontrolledValue(next);
      onValueChange?.(next);
    },
    [isControlled, onValueChange],
  );

  const toggle = React.useCallback(
    (itemValue: string) => {
      const isOpen = openValues.includes(itemValue);
      if (type === "single") {
        commit(isOpen ? [] : [itemValue]);
        return;
      }
      commit(
        isOpen
          ? openValues.filter((current) => current !== itemValue)
          : [...openValues, itemValue],
      );
    },
    [commit, openValues, type],
  );

  /**
   * ناوبری بین سرتیترها با کلیدهای عمودی — الگوی WAI-ARIA Accordion.
   * کلیدهای جهت‌دار افقی اینجا استفاده نمی‌شوند چون چیدمان عمودی است و
   * در RTL جهت‌شان معکوس می‌شد.
   */
  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const navigationKeys = ["ArrowDown", "ArrowUp", "Home", "End"];
    if (!navigationKeys.includes(event.key)) return;

    const triggers = Array.from(
      rootRef.current?.querySelectorAll<HTMLButtonElement>(
        "[data-accordion-trigger]",
      ) ?? [],
    );
    if (triggers.length === 0) return;

    const currentIndex = triggers.indexOf(
      document.activeElement as HTMLButtonElement,
    );
    if (currentIndex === -1) return;

    let nextIndex = currentIndex;
    if (event.key === "ArrowDown") nextIndex = (currentIndex + 1) % triggers.length;
    else if (event.key === "ArrowUp")
      nextIndex = (currentIndex - 1 + triggers.length) % triggers.length;
    else if (event.key === "Home") nextIndex = 0;
    else nextIndex = triggers.length - 1;

    event.preventDefault();
    triggers[nextIndex].focus();
  };

  return (
    <AccordionContext.Provider value={{ openValues, toggle }}>
      <div
        ref={rootRef}
        dir="rtl"
        onKeyDown={handleKeyDown}
        className={cn(
          "flex w-full flex-col gap-3 font-sans text-foreground",
          className,
        )}
        {...rest}
      >
        {children}
      </div>
    </AccordionContext.Provider>
  );
}

/* ------------------------------------------------------------------ */
/* آیتم                                                               */
/* ------------------------------------------------------------------ */

export type AccordionItemProps = {
  /** کلید یکتا؛ برای defaultOpen/value لازم است. */
  value?: string;
  title: React.ReactNode;
  children: React.ReactNode;
  /** سطح تیتر پرسش (پیش‌فرض ۳) تا ساختار سرفصل‌های صفحه درست بماند. */
  headingLevel?: 2 | 3 | 4 | 5 | 6;
  className?: string;
};

export function AccordionItem({
  value,
  title,
  children,
  headingLevel = 3,
  className,
}: AccordionItemProps) {
  const { openValues, toggle } = useAccordionContext("AccordionItem");
  const reactId = React.useId();
  const itemValue = value ?? reactId;
  const triggerId = `${reactId}-trigger`;
  const panelId = `${reactId}-panel`;
  const open = openValues.includes(itemValue);

  const panelRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    // پنل بسته نباید با Tab فوکوس بگیرد یا برای صفحه‌خوان خوانده شود.
    if (open) panel.removeAttribute("inert");
    else panel.setAttribute("inert", "");
  }, [open]);

  const Heading = `h${headingLevel}` as "h2" | "h3" | "h4" | "h5" | "h6";

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-background",
        "transition-colors duration-200 motion-reduce:transition-none",
        open && "border-primary/40",
        className,
      )}
    >
      <Heading className="m-0">
        <button
          type="button"
          id={triggerId}
          data-accordion-trigger
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => toggle(itemValue)}
          className={cn(
            "flex w-full items-center gap-3 bg-transparent px-4 py-4 text-start",
            "font-sans text-base font-semibold text-foreground",
            "transition-colors duration-200 motion-reduce:transition-none",
            "hover:bg-muted",
            "outline-none focus-visible:ring-2 focus-visible:ring-ring",
            "focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          <span className="flex-1 text-start">{title}</span>
          {/*
            شورون در سمت چپ است: در RTL انتهای خط (end) همان چپ است، پس
            آخرین فرزند فلکس قرار می‌گیرد و نیازی به left/right نیست.
            «next» در RTL به چپ اشاره می‌کند، پس از ChevronLeft استفاده شده
            و در حالت باز ۱۸۰ درجه می‌چرخد.
          */}
          <ChevronLeft
            aria-hidden="true"
            className={cn(
              "size-5 shrink-0 text-muted-foreground",
              "transition-transform duration-200 motion-reduce:transition-none",
              open && "rotate-180",
            )}
          />
        </button>
      </Heading>

      <div
        ref={panelRef}
        id={panelId}
        role="region"
        aria-labelledby={triggerId}
        className={cn(
          "grid ease-out",
          "transition-[grid-template-rows] duration-200 motion-reduce:transition-none",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="px-4 pb-4 text-sm leading-8 text-muted-foreground">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Accordion;
