"use client";

/**
 * Pagination — مؤلفه صفحه‌بندی راست‌چین و دسترس‌پذیر (React + Tailwind CSS).
 *
 * ویژگی‌های کلیدی
 * • دکمه «قبلی» با شورون راست (ChevronRight) و «بعدی» با شورون چپ (ChevronLeft) مطابق جهت‌گیری زبان‌های RTL.
 * • الگوریتم بیضی (Ellipsis): همیشه صفحه اول (۱) و صفحه آخر نمایش داده می‌شوند به همراه صفحات مجاور صفحه جاری.
 * • صفحه جاری دارای `aria-current="page"`، پس‌زمینه رنگ شاخص `bg-primary text-primary-foreground` و کادر مشخص.
 * • سایر صفحات با کادر خنثی `border-border` و افکت هاور نرم.
 * • اعداد کاملاً با ارقام فارسی (۰–۹) نمایش داده می‌شوند.
 * • پشتیبانی کامل از صفحه‌کلید (کلیدهای Enter، Space، ArrowLeft برای رفتن به صفحه بعد در RTL و ArrowRight برای صفحه قبل).
 * • رعایت کامل توکن‌های تم پروژه (bg-background، text-foreground، bg-primary، border-border، text-muted-foreground).
 *
 * نمونه استفاده سریع
 *
 *   import { Pagination } from "@/components/pagination";
 *
 *   export function ArticlesList() {
 *     const [currentPage, setCurrentPage] = React.useState(1);
 *     const totalPages = 10;
 *
 *     return (
 *       <div className="space-y-6">
 *         <div className="grid gap-4">...محتوای مقالات...</div>
 *         <Pagination
 *           currentPage={currentPage}
 *           totalPages={totalPages}
 *           onPageChange={(page) => setCurrentPage(page)}
 *         />
 *       </div>
 *     );
 *   }
 */

import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

/* ------------------------------------------------------------------ */
/* ابزارهای فارسی و قالب‌بندی                                         */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;

/** جداکننده‌ی هزارگان فارسی (U+066C) */
export const THOUSANDS_SEPARATOR = "٬";

/** تبدیل ارقام انگلیسی به فارسی (۰–۹) */
export function toPersianDigits(value: string | number): string {
  return String(value).replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)] || digit);
}

/** قالب‌بندی مبالغ با ارقام فارسی، جداکننده و واحد تومان */
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

/** ترکیب کلاس‌های شرطی Tailwind بدون نیاز به کتابخانه اضافی */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ */
/* الگوریتم محاسبه دامنه‌ی صفحات با بیضی (Ellipsis Algorithm)          */
/* ------------------------------------------------------------------ */

export const ELLIPSIS = "...";

/**
 * الگوریتم تولید دامنه‌ی صفحات:
 * همیشه صفحه ۱ و صفحه آخر باقی می‌مانند، به اضافه همسایه‌های چپ و راست صفحه جاری.
 */
export function getPaginationRange(
  currentPage: number,
  totalPages: number,
  siblingCount: number = 1,
): Array<number | typeof ELLIPSIS> {
  // اگر تعداد کل صفحات کم باشد، بیضی لازم نیست
  const totalPageNumbers = siblingCount * 2 + 5; // 1 + last + current + 2*siblings + 2*ellipsis

  if (totalPages <= totalPageNumbers) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const leftSiblingIndex = Math.max(currentPage - siblingCount, 1);
  const rightSiblingIndex = Math.min(currentPage + siblingCount, totalPages);

  const shouldShowLeftEllipsis = leftSiblingIndex > 2;
  const shouldShowRightEllipsis = rightSiblingIndex < totalPages - 1;

  // حالت ۱: فقط بیضی در سمت راست
  if (!shouldShowLeftEllipsis && shouldShowRightEllipsis) {
    const leftItemCount = 3 + 2 * siblingCount;
    const leftRange = Array.from({ length: leftItemCount }, (_, i) => i + 1);
    return [...leftRange, ELLIPSIS, totalPages];
  }

  // حالت ۲: فقط بیضی در سمت چپ
  if (shouldShowLeftEllipsis && !shouldShowRightEllipsis) {
    const rightItemCount = 3 + 2 * siblingCount;
    const rightRange = Array.from(
      { length: rightItemCount },
      (_, i) => totalPages - rightItemCount + i + 1,
    );
    return [1, ELLIPSIS, ...rightRange];
  }

  // حالت ۳: بیضی در هر دو سمت (چپ و راست)
  if (shouldShowLeftEllipsis && shouldShowRightEllipsis) {
    const middleRange = Array.from(
      { length: rightSiblingIndex - leftSiblingIndex + 1 },
      (_, i) => leftSiblingIndex + i,
    );
    return [1, ELLIPSIS, ...middleRange, ELLIPSIS, totalPages];
  }

  return Array.from({ length: totalPages }, (_, i) => i + 1);
}

/* ------------------------------------------------------------------ */
/* انواع و مؤلفه Pagination                                           */
/* ------------------------------------------------------------------ */

export interface PaginationProps {
  /** صفحه فعال جاری (شروع از ۱) */
  currentPage: number;
  /** تعداد کل صفحات */
  totalPages: number;
  /** تعداد صفحات مجاور صفحه جاری (پیش‌فرض: ۱) */
  siblingCount?: number;
  /** رویداد کلیک و تغییر صفحه */
  onPageChange: (page: number) => void;
  /** برچسب متنی دکمه قبلی (پیش‌فرض: «قبلی») */
  previousLabel?: string;
  /** برچسب متنی دکمه بعدی (پیش‌فرض: «بعدی») */
  nextLabel?: string;
  /** کلاس‌های سی‌اس‌اس والد */
  className?: string;
  /** برچسب دسترس‌پذیری ناحیه ناوبری */
  ariaLabel?: string;
  /** نمایش خلاصه‌ی تعداد آیتم‌ها و صفحات در کنار صفحه‌بندی */
  showSummary?: boolean;
  /** کل تعداد آیتم‌ها (برای نمایش خلاصه اختیاری) */
  totalItems?: number;
  /** تعداد آیتم در هر صفحه (برای محاسبه بازه نمایشی) */
  pageSize?: number;
}

export function Pagination({
  currentPage,
  totalPages,
  siblingCount = 1,
  onPageChange,
  previousLabel = "قبلی",
  nextLabel = "بعدی",
  className,
  ariaLabel = "صفحه‌بندی مطالب",
  showSummary = false,
  totalItems,
  pageSize = 6,
}: PaginationProps) {
  // اگر کلاً یک صفحه یا صفر صفحه باشد، رندر غیرضروری است
  if (totalPages <= 1) return null;

  const paginationRange = getPaginationRange(currentPage, totalPages, siblingCount);
  const isFirstPage = currentPage <= 1;
  const isLastPage = currentPage >= totalPages;

  // محاسبه بازه شماره آیتم‌ها برای خلاصه
  const startItem = totalItems ? (currentPage - 1) * pageSize + 1 : null;
  const endItem = totalItems ? Math.min(currentPage * pageSize, totalItems) : null;

  // ناوبری صفحه‌کلید با رعایت RTL:
  // در زبان فارسی ArrowLeft = رفتن به جلو/بعدی و ArrowRight = رفتن به عقب/قبلی
  const handleKeyDown = (e: React.KeyboardEvent, targetPage: number) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onPageChange(targetPage);
    } else if (e.key === "ArrowLeft" && !isLastPage) {
      e.preventDefault();
      onPageChange(currentPage + 1);
    } else if (e.key === "ArrowRight" && !isFirstPage) {
      e.preventDefault();
      onPageChange(currentPage - 1);
    }
  };

  return (
    <nav
      dir="rtl"
      aria-label={ariaLabel}
      className={cn(
        "flex flex-col sm:flex-row items-center justify-between gap-4 py-4 select-none",
        className,
      )}
    >
      {/* متن خلاصه اختیاری */}
      {showSummary && totalItems && startItem && endItem && (
        <p className="text-xs sm:text-sm text-muted-foreground order-2 sm:order-1">
          نمایش <span className="font-bold text-foreground num">{toPersianDigits(startItem)}</span> تا{" "}
          <span className="font-bold text-foreground num">{toPersianDigits(endItem)}</span> از{" "}
          <span className="font-bold text-foreground num">{toPersianDigits(totalItems)}</span> مورد
        </p>
      )}

      {/* لیست دکمه‌های صفحه‌بندی */}
      <ul
        className={cn(
          "flex items-center gap-1 sm:gap-1.5 order-1 sm:order-2",
          !showSummary && "mx-auto",
        )}
      >
        {/* دکمه صفحه قبلی: در RTL فلش رو به راست اشاره دارد */}
        <li>
          <button
            type="button"
            disabled={isFirstPage}
            onClick={() => !isFirstPage && onPageChange(currentPage - 1)}
            aria-label="رفتن به صفحه قبل"
            className={cn(
              "inline-flex h-9 sm:h-10 items-center gap-1 rounded-xl border border-border px-2.5 sm:px-3 text-xs sm:text-sm font-bold transition-all",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              isFirstPage
                ? "cursor-not-allowed opacity-40 text-muted-foreground bg-muted/20"
                : "cursor-pointer text-foreground bg-background hover:bg-muted/60 hover:border-primary/40 active:scale-95",
            )}
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
            <span className="hidden xs:inline">{previousLabel}</span>
          </button>
        </li>

        {/* لیست شماره صفحات و بیضی‌ها */}
        {paginationRange.map((pageNumber, idx) => {
          if (pageNumber === ELLIPSIS) {
            return (
              <li key={`ellipsis-${idx}`} className="flex h-9 w-8 sm:h-10 sm:w-9 items-center justify-center">
                <span className="flex items-center justify-center text-muted-foreground" aria-hidden="true">
                  <MoreHorizontal className="h-4 w-4" />
                </span>
                <span className="sr-only">صفحات بیشتر</span>
              </li>
            );
          }

          const pageNum = pageNumber as number;
          const isCurrent = pageNum === currentPage;

          return (
            <li key={`page-${pageNum}`}>
              <button
                type="button"
                onClick={() => onPageChange(pageNum)}
                onKeyDown={(e) => handleKeyDown(e, pageNum)}
                aria-current={isCurrent ? "page" : undefined}
                aria-label={`صفحه ${toPersianDigits(pageNum)}`}
                className={cn(
                  "inline-flex h-9 min-w-9 sm:h-10 sm:min-w-10 items-center justify-center rounded-xl px-2 text-xs sm:text-sm font-bold transition-all cursor-pointer",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  isCurrent
                    ? "bg-primary text-primary-foreground font-black shadow-sm"
                    : "border border-border bg-background text-foreground hover:bg-muted/60 hover:border-primary/40 hover:text-primary active:scale-95",
                )}
              >
                <span className="num">{toPersianDigits(pageNum)}</span>
              </button>
            </li>
          );
        })}

        {/* دکمه صفحه بعدی: در RTL فلش رو به چپ اشاره دارد */}
        <li>
          <button
            type="button"
            disabled={isLastPage}
            onClick={() => !isLastPage && onPageChange(currentPage + 1)}
            aria-label="رفتن به صفحه بعد"
            className={cn(
              "inline-flex h-9 sm:h-10 items-center gap-1 rounded-xl border border-border px-2.5 sm:px-3 text-xs sm:text-sm font-bold transition-all",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              isLastPage
                ? "cursor-not-allowed opacity-40 text-muted-foreground bg-muted/20"
                : "cursor-pointer text-foreground bg-background hover:bg-muted/60 hover:border-primary/40 active:scale-95",
            )}
          >
            <span className="hidden xs:inline">{nextLabel}</span>
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </button>
        </li>
      </ul>
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* نمونه استفاده کامل و تعاملی (Short Usage Example)                  */
/* ------------------------------------------------------------------ */

interface ArticleItem {
  id: number;
  title: string;
  category: string;
  summary: string;
  readTime: number;
}

const SAMPLE_ARTICLES: ArticleItem[] = [
  { id: 1, title: "ارورهای متداول پکیج بوتان و راهنمای رفع آن", category: "پکیج دیواری", summary: "بررسی کدهای خطای A01 تا A11 و اقدامات سریع هنگام افت فشار آب.", readTime: 5 },
  { id: 2, title: "چرا پکیج آب مصرفی را گرم نمی‌کند؟ ۸ علت رایج", category: "عیب‌یابی", summary: "مشکلات سنسور NTC، فلومتر، مبدل ثانویه و تنظیم نبودن شیر گاز.", readTime: 7 },
  { id: 3, title: "زمان مناسب تعویض فیلترهای تصفیه آب خانگی", category: "تصفیه آب", summary: "راهنمای تعویض فیلترهای مرحله ۱ تا ۶ و جلوگیری از افت فشار مخزن.", readTime: 4 },
  { id: 4, title: "علت صداهای غیرعادی و تق‌تق پکیج در زمستان", category: "پکیج دیواری", summary: "بررسی هواگیری نامناسب مدار، رسوب مبدل اصلی و خرابی پمپ سیرکولاتور.", readTime: 6 },
  { id: 5, title: "راهنمای کامل هواگیری رادیاتور و شوفاژ", category: "رادیاتور", summary: "مراحل گام به گام هواگیری بدون کثیف‌کاری و تنظیم فشار بار پکیج روی ۱.۵.", readTime: 3 },
  { id: 6, title: "کاهش مصرف گاز پکیج با چند ترفند ساده", category: "نگهداری", summary: "تنظیم صحیح ترموستات، عایق‌کاری لوله‌های آب گرم و شستشوی مدار گرمایش.", readTime: 5 },
  { id: 7, title: "تعمیر پکیج ایران رادیاتور در مناطق غرب تهران", category: "پکیج دیواری", summary: "خدمات اعزام سریع سرویس‌کار مجاز با قطعات یدکی شرکتی.", readTime: 4 },
  { id: 8, title: "سرویس دوره‌ای کولر گازی قبل از شروع فصل گرما", category: "کولر گازی", summary: "شستشوی کندانسور، بررسی فشار گاز مبرد و تست سلامت کمپرسور.", readTime: 6 },
  { id: 9, title: "نشتی آب از زیر پکیج؛ علت‌ها و خطرات احتمالی", category: "عیب‌یابی", summary: "خرابی شیر اطمینان ۳ بار، اورینگ‌های مبدل و اتصالات شلنگ.", readTime: 5 },
  { id: 10, title: "نحوه رسوب‌زدایی مبدل پکیج با پمپ اسیدشویی", category: "آموزش تخصصی", summary: "نکات ایمنی دیسکلر، زمان گردش اسید و پیشگیری از سوراخ شدن مبدل.", readTime: 8 },
  { id: 11, title: "تفاوت پکیج فن‌دار و بدون فن از نظر ایمنی", category: "راهنمای خرید", summary: "ضوابط دودکش‌های دوجداره، استانداردهای ساختمانی و نصب در بالکن.", readTime: 4 },
  { id: 12, title: "علت بوی گاز یا سوختگی در اطراف پکیج", category: "ایمنی فوری", summary: "اقدامات اورژانسی، بستن فلکه گاز، تهویه محیط و تماس سریع با تعمیرکار.", readTime: 3 },
];

export function PaginationUsageExample() {
  const [currentPage, setCurrentPage] = React.useState(1);
  const pageSize = 3;
  const totalItems = SAMPLE_ARTICLES.length;
  const totalPages = Math.ceil(totalItems / pageSize);

  // برش مقالات صفحه جاری
  const startIndex = (currentPage - 1) * pageSize;
  const currentArticles = SAMPLE_ARTICLES.slice(startIndex, startIndex + pageSize);

  return (
    <div dir="rtl" className="mx-auto w-full max-w-4xl rounded-2xl border border-border bg-background p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4 mb-6">
        <div>
          <h3 className="text-lg font-extrabold text-foreground">دانشنامه و مقالات تخصصی</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            نمایش مقالات بر اساس صفحه‌بندی راست‌چین و دسترس‌پذیر
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
          {toPersianDigits(totalItems)} مقاله منتشر شده
        </span>
      </div>

      {/* کارت‌های مقالات صفحه جاری */}
      <div className="grid gap-4 sm:grid-cols-3 mb-6">
        {currentArticles.map((article) => (
          <article
            key={article.id}
            className="flex flex-col justify-between rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/40 hover:shadow-xs"
          >
            <div>
              <span className="inline-block rounded-md bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground mb-2">
                {article.category}
              </span>
              <h4 className="text-sm font-bold text-foreground leading-6 line-clamp-2">
                {article.title}
              </h4>
              <p className="mt-2 text-xs text-muted-foreground leading-5 line-clamp-3">
                {article.summary}
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
              <span>زمان مطالعه: {toPersianDigits(article.readTime)} دقیقه</span>
              <span className="font-bold text-primary">ادامه مطلب ←</span>
            </div>
          </article>
        ))}
      </div>

      {/* کامپوننت صفحه‌بندی */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={totalItems}
        pageSize={pageSize}
        showSummary={true}
        onPageChange={(page) => setCurrentPage(page)}
      />
    </div>
  );
}
