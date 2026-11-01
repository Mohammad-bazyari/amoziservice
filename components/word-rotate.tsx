"use client";

/**
 * WordRotate — مؤلفه متحرک چرخش ۸ کلمه (React + Tailwind CSS) برای متون راست‌چین.
 *
 * ویژگی‌های کلیدی
 * • پایداری ابعاد با `inline-grid`: کانتینر شامل یک نسخه نامرئی از طولانی‌ترین
 *   کلمه (`col-start-1 row-start-1 invisible select-none`) است؛ بنابراین پهنای
 *   جمله هرگز نمی‌پرد و هیچ جابجایی چیدمان تجمعی (CLS = 0) رخ نمی‌دهد.
 * • بازنشانی انیمیشن با `key` تازه: با تغییر ایندکس کلمه، المان دوباره Mount شده
 *   و انیمیشن کوتاه ورود (ورود نرم از پایین به بالا با محو شدن) اجرا می‌شود.
 * • ۸ کلمه هدف پروژه:
 *   ۱. پکیج ۲. رادیاتور ۳. کولر گازی ۴. تصفیه آب ۵. لباسشویی ۶. ظرفشویی ۷. یخچال ۸. فریزر
 * • رنگ زرد ثانویه پروژه: `text-cta-400` / `text-cta-500` (برگرفته از توکن‌های تم سایت).
 * • دسترس‌پذیری (A11y): ویژگی `aria-live="polite"` کلمه جدید را به صفحه‌خوان‌ها
 *   اعلام می‌کند؛ نسخه نامرئی با `aria-hidden="true"` پنهان شده است.
 * • احترام به ترجیحات کاربر: انیمیشن‌ها در حالت `prefers-reduced-motion` متوقف می‌شوند.
 * • توقف هوشمند: در زمان هاور ماوس یا فوکوس صفحه‌کلید، چرخش برای خوانایی متوقف می‌شود.
 *
 * نمونه استفاده
 *
 *   import { WordRotate } from "@/components/word-rotate";
 *
 *   export function Hero() {
 *     return (
 *       <h1 className="text-3xl font-extrabold text-foreground md:text-5xl">
 *         تعمیر تخصصی{" "}
 *         <WordRotate
 *           words={["پکیج", "رادیاتور", "کولر گازی", "تصفیه آب", "لباسشویی", "ظرفشویی", "یخچال", "فریزر"]}
 *           className="text-cta-500 dark:text-cta-400"
 *         />{" "}
 *         در تهران
 *       </h1>
 *     );
 *   }
 */

import * as React from "react";

/* ------------------------------------------------------------------ */
/* ابزارهای فارسی و قالب‌بندی اعداد                                      */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;

/** جداکننده‌ی هزارگان فارسی (U+066C) */
export const THOUSANDS_SEPARATOR = "٬";

/** تبدیل ارقام لاتین به فارسی (۰–۹) */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

/** قالب‌بندی مبالغ با جداکننده و واحد تومان */
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

/** ادغام کلاس‌های Tailwind بدون وابستگی اضافه */
export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ */
/* انواع داده مؤلفه WordRotate                                        */
/* ------------------------------------------------------------------ */

export interface WordRotateProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** آرایه‌ای از کلمات برای چرخش دوره‌ای (پیش‌فرض: ۸ کلمه درخواستی) */
  words?: string[];
  /** مدت زمان نمایش هر کلمه به میلی‌ثانیه (پیش‌فرض: ۲۴۰۰) */
  duration?: number;
  /** کلاس‌های اختصاصی برای کلمه فعال متحرک */
  wordClassName?: string;
  /** توقف چرخش با هاور یا فوکوس برای راحتی کاربر (پیش‌فرض: true) */
  pauseOnHover?: boolean;
}

/** ۸ کلمه اصلی خدمات */
const DEFAULT_WORDS = [
  "پکیج",
  "رادیاتور",
  "کولر گازی",
  "تصفیه آب",
  "لباسشویی",
  "ظرفشویی",
  "یخچال",
  "فریزر",
];

/* ------------------------------------------------------------------ */
/* مؤلفه اصلی WordRotate                                              */
/* ------------------------------------------------------------------ */

export function WordRotate({
  words = DEFAULT_WORDS,
  duration = 2400,
  className,
  wordClassName,
  pauseOnHover = true,
  ...props
}: WordRotateProps) {
  const [index, setIndex] = React.useState(0);
  const [isPaused, setIsPaused] = React.useState(false);

  // پیدا کردن طولانی‌ترین کلمه برای تثبیت پهنای کانتینر
  const longestWord = React.useMemo(() => {
    if (!words.length) return "";
    return words.reduce((longest, curr) => (curr.length > longest.length ? curr : longest), words[0]);
  }, [words]);

  // بررسی وضعیت prefers-reduced-motion
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const listener = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  // چرخش کلمات در صورت فعال بودن
  React.useEffect(() => {
    if (words.length <= 1 || isPaused || prefersReducedMotion) return;

    const intervalId = window.setInterval(() => {
      setIndex((prevIndex) => (prevIndex + 1) % words.length);
    }, Math.max(duration, 1000));

    return () => window.clearInterval(intervalId);
  }, [words.length, duration, isPaused, prefersReducedMotion]);

  const currentWord = words[index] || "";

  return (
    <>
      {/* تعریف استایل انیمیشن فشرده و استاندارد (۲۵۰ میلی‌ثانیه) */}
      <style>{`
        @keyframes wordRotateIn {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-word-rotate-in {
          animation: wordRotateIn 240ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-word-rotate-in {
            animation: none !important;
            transform: none !important;
            opacity: 1 !important;
          }
        }
      `}</style>

      <span
        dir="rtl"
        aria-live="polite"
        onMouseEnter={pauseOnHover ? () => setIsPaused(true) : undefined}
        onMouseLeave={pauseOnHover ? () => setIsPaused(false) : undefined}
        onFocus={pauseOnHover ? () => setIsPaused(true) : undefined}
        onBlur={pauseOnHover ? () => setIsPaused(false) : undefined}
        tabIndex={0}
        className={cn(
          "inline-grid grid-cols-1 grid-rows-1 align-baseline text-start outline-none transition-colors overflow-hidden",
          "rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          className,
        )}
        {...props}
      >
        {/* المان نامرئی جهت قفل کردن پهنا براساس طولانی‌ترین کلمه و جلوگیری از پرش جمله (CLS = 0) */}
        <span
          className="col-start-1 row-start-1 invisible pointer-events-none select-none"
          aria-hidden="true"
        >
          {longestWord}
        </span>

        {/* کلمه فعال با key جدید برای راه‌اندازی مجدد انیمیشن ورود */}
        <span
          key={index}
          className={cn(
            "col-start-1 row-start-1 inline-block",
            !prefersReducedMotion && "animate-word-rotate-in",
            wordClassName,
          )}
        >
          {currentWord}
        </span>
      </span>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* نمونه صفحه کامل هیرو (Hero Usage Example)                          */
/* ------------------------------------------------------------------ */

export function HeroHeadingExample() {
  const serviceItems = [
    "پکیج",
    "رادیاتور",
    "کولر گازی",
    "تصفیه آب",
    "لباسشویی",
    "ظرفشویی",
    "یخچال",
    "فریزر",
  ];

  return (
    <div dir="rtl" className="bg-background text-foreground p-8 text-center font-sans">
      <h1 className="text-3xl font-extrabold leading-[1.4] sm:text-4xl md:text-5xl">
        تعمیر تخصصی{" "}
        <WordRotate
          words={serviceItems}
          className="text-cta-500 dark:text-cta-400 font-black"
        />{" "}
        در تهران
      </h1>
      <p className="text-muted-foreground mt-4 text-base">
        ثبت آنلاین درخواست عیب‌یابی و تعمیر انواع دستگاه‌های سرمایشی، گرمایشی و خانگی
      </p>
    </div>
  );
}

export default WordRotate;
