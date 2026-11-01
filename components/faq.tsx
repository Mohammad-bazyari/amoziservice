"use client";

/**
 * Faq — بلوک «پرسش‌های متداول» دو ستونی (۲/۵ و ۳/۵) برای صفحات راست‌چین.
 *
 * • موبایل: یک ستون روی هم. دسکتاپ (lg): شبکه‌ی ۵ ستونی با ۲ ستون برای عنوان و
 *   ۳ ستون برای پرسش‌ها.
 * • آکاردئون داخلی همان کامپوننت Accordion است: شورون در سمت چپ و انیمیشن ارتفاع
 *   با grid-template-rows.
 * • همه‌ی متن‌ها فارسی‌اند و رنگ‌ها از توکن‌های تم می‌آیند.
 *
 * نمونه استفاده
 *
 *   <Faq
 *     title="پرسش‌های متداول"
 *     description="هر چیزی که پیش از ثبت درخواست لازم است بدانید."
 *     defaultOpen="fee"
 *     items={[
 *       {
 *         value: "fee",
 *         question: "هزینه عیب‌یابی چقدر است؟",
 *         answer: `هزینه عیب‌یابی ${formatToman(350000)} است و پیش از شروع کار اعلام می‌شود.`,
 *       },
 *       {
 *         value: "area",
 *         question: "در چه مناطقی خدمت می‌دهید؟",
 *         answer: "تهران و شهرهای اطراف؛ هنگام ثبت درخواست منطقه را انتخاب می‌کنید.",
 *       },
 *     ]}
 *   />
 */

import * as React from "react";
import { Accordion, AccordionItem, cn } from "./accordion";

export type FaqItem = {
  /** کلید یکتا برای کنترل باز/بسته بودن. */
  value?: string;
  question: string;
  answer: React.ReactNode;
};

export type FaqProps = {
  title?: string;
  description?: string;
  items: FaqItem[];
  /** مقدار پرسشی که در ابتدا باز باشد. */
  defaultOpen?: string;
  /** سطح تیتر پرسش‌ها؛ پیش‌فرض ۳. */
  headingLevel?: 2 | 3 | 4 | 5 | 6;
  className?: string;
};

export function Faq({
  title = "پرسش‌های متداول",
  description = "پاسخ پرتکرارترین پرسش‌ها درباره ثبت درخواست، هزینه و محدوده‌ی خدمات.",
  items,
  defaultOpen,
  headingLevel = 3,
  className,
}: FaqProps) {
  const headingId = React.useId();

  return (
    <section
      dir="rtl"
      aria-labelledby={headingId}
      className={cn("bg-background font-sans text-foreground", className)}
    >
      <div className="mx-auto max-w-6xl px-4 py-14 md:py-20">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-5 lg:gap-12">
          {/* ستون عنوان — ۲ از ۵ ستون در دسکتاپ */}
          <header className="lg:col-span-2">
            <div className="lg:sticky lg:top-24">
              <h2
                id={headingId}
                className="text-balance text-2xl font-extrabold leading-[1.7] md:text-3xl"
              >
                {title}
              </h2>
              {description ? (
                <p className="mt-4 text-base leading-8 text-muted-foreground">
                  {description}
                </p>
              ) : null}
            </div>
          </header>

          {/* ستون پرسش‌ها — ۳ از ۵ ستون در دسکتاپ */}
          <div className="lg:col-span-3">
            <Accordion
              type="single"
              defaultOpen={defaultOpen ? [defaultOpen] : []}
              aria-label={title}
            >
              {items.map((item, index) => (
                <AccordionItem
                  key={item.value ?? index}
                  value={item.value}
                  title={item.question}
                  headingLevel={headingLevel}
                >
                  {item.answer}
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Faq;
