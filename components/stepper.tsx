"use client";

/**
 * Stepper — مؤلفه گام‌شمار راست‌چین و دسترس‌پذیر (React + Tailwind CSS).
 *
 * ویژگی‌های کلیدی
 * • گام‌های تکمیل‌شده: تیک تأیید (آیکون Check) و پس‌زمینه رنگ شاخص `bg-primary text-primary-foreground`.
 * • گام جاری: حلقه شاخص `ring-4 ring-primary/20 border-2 border-primary` و صفت دسترس‌پذیری `aria-current="step"`.
 * • گام‌های آینده: کادر خاکستری `border-2 border-border` با شماره گام به رنگ خنثی `text-muted-foreground`.
 * • خط اتصال (Connector line) پیوسته میان دایره‌ها: با رنگ‌آمیزی بر اساس وضعیت گام‌ها (شاخص/خنثی).
 * • اعداد تماماً با ارقام فارسی (۰–۹) نمایش داده می‌شوند.
 * • ناوبری کامل با صفحه‌کلید (Enter، Space، ArrowLeft برای گام بعد در RTL و ArrowRight برای گام قبل).
 * • رعایت کامل توکن‌های تم پروژه (bg-background، text-foreground، bg-primary، border-border، text-muted-foreground).
 *
 * نمونه استفاده سریع
 *
 *   import { Stepper, StepItem } from "@/components/stepper";
 *
 *   const steps: StepItem[] = [
 *     { id: "service", title: "انتخاب خدمت", description: "نوع دستگاه" },
 *     { id: "problem", title: "برند و مشکل", description: "شرح و تصاویر" },
 *     { id: "customer", title: "اطلاعات تماس", description: "نام و شماره همراه" },
 *     { id: "address", title: "آدرس و موقعیت", description: "محل مراجعه" },
 *     { id: "review", title: "بازبینی نهایی", description: "تأیید و ارسال" },
 *   ];
 *
 *   export function RequestWizard() {
 *     const [currentStep, setCurrentStep] = React.useState(1);
 *     return <Stepper steps={steps} currentStep={currentStep} onStepClick={setCurrentStep} />;
 *   }
 */

import * as React from "react";
import { Check, ChevronLeft, ChevronRight } from "lucide-react";

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

export type ClassValue = string | number | boolean | undefined | null | ClassValue[];

/** ترکیب کلاس‌های شرطی Tailwind */
export function cn(...inputs: ClassValue[]): string {
  const classes: string[] = [];
  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === "string") {
      classes.push(input);
    } else if (Array.isArray(input)) {
      const nested = cn(...input);
      if (nested) classes.push(nested);
    }
  }
  return classes.join(" ");
}

/* ------------------------------------------------------------------ */
/* مشخصات و انواع مؤلفه Stepper                                       */
/* ------------------------------------------------------------------ */

export interface StepItem {
  /** شناسه منحصر‌به‌فرد گام */
  id: string;
  /** عنوان اصلی گام */
  title: string;
  /** توضیح یا زیرعنوان کوتاه اختیاری */
  description?: string;
  /** نشان اختیاری بودن گام */
  optional?: boolean;
}

export interface StepperProps {
  /** لیست مراحل */
  steps: StepItem[];
  /** شماره گام فعال جاری (شروع از ۱ تا تعداد کل مراحل) */
  currentStep: number;
  /** رویداد کلیک روی گام برای تغییر گام */
  onStepClick?: (stepNumber: number) => void;
  /** آیا فقط گام‌های قبلی قابل کلیک باشند (پیش‌فرض: true) */
  clickablePreviousOnly?: boolean;
  /** کلاس‌های سی‌اس‌اس والد */
  className?: string;
  /** برچسب دسترس‌پذیری ناحیه ناوبری */
  ariaLabel?: string;
}

export function Stepper({
  steps,
  currentStep,
  onStepClick,
  clickablePreviousOnly = true,
  className,
  ariaLabel = "مراحل ثبت درخواست",
}: StepperProps) {
  const totalSteps = steps.length;
  if (totalSteps === 0) return null;

  // کلیدهای ناوبری صفحه‌کلید متناسب با جهت راست‌به‌چپ (RTL)
  // ArrowLeft = رفتن به گام بعدی در جهت خوانش فارسی
  // ArrowRight = بازگشت به گام قبلی
  const handleKeyDown = (e: React.KeyboardEvent, stepNum: number) => {
    if (!onStepClick) return;

    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (canClickStep(stepNum)) {
        onStepClick(stepNum);
      }
    } else if (e.key === "ArrowLeft" && currentStep < totalSteps) {
      e.preventDefault();
      if (!clickablePreviousOnly || currentStep + 1 <= currentStep) {
        onStepClick(currentStep + 1);
      }
    } else if (e.key === "ArrowRight" && currentStep > 1) {
      e.preventDefault();
      onStepClick(currentStep - 1);
    }
  };

  const canClickStep = (stepNum: number): boolean => {
    if (!onStepClick) return false;
    if (stepNum === currentStep) return false;
    if (clickablePreviousOnly) {
      return stepNum < currentStep;
    }
    return true;
  };

  return (
    <nav
      dir="rtl"
      aria-label={ariaLabel}
      className={cn("w-full py-4 select-none", className)}
    >
      <ol className="flex items-center justify-between w-full">
        {steps.map((step, idx) => {
          const stepNumber = idx + 1;
          const isCompleted = stepNumber < currentStep;
          const isCurrent = stepNumber === currentStep;
          const isUpcoming = stepNumber > currentStep;
          const isClickable = canClickStep(stepNumber);
          const isLast = idx === totalSteps - 1;

          return (
            <li
              key={step.id}
              className={cn(
                "relative flex items-center",
                !isLast && "flex-1",
              )}
            >
              {/* بخش دایره و عنوان گام */}
              <div className="flex flex-col items-center group relative z-10">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => isClickable && onStepClick?.(stepNumber)}
                  onKeyDown={(e) => handleKeyDown(e, stepNumber)}
                  aria-current={isCurrent ? "step" : undefined}
                  aria-label={`گام ${toPersianDigits(stepNumber)}: ${step.title}${isCompleted ? " (تکمیل شده)" : isCurrent ? " (در حال انجام)" : ""}`}
                  className={cn(
                    "flex h-9 w-9 sm:h-11 sm:w-11 items-center justify-center rounded-full font-bold text-xs sm:text-sm transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isCompleted && [
                      "bg-primary text-primary-foreground shadow-xs",
                      isClickable && "cursor-pointer hover:opacity-90 hover:scale-105 active:scale-95",
                    ],
                    isCurrent && [
                      "bg-background text-primary border-2 border-primary ring-4 ring-primary/20 font-black shadow-xs",
                      "cursor-default",
                    ],
                    isUpcoming && [
                      "bg-background text-muted-foreground border-2 border-border",
                      isClickable ? "cursor-pointer hover:border-primary/50 hover:text-foreground" : "cursor-not-allowed",
                    ],
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4 sm:h-5 sm:w-5 stroke-[2.5]" aria-hidden="true" />
                  ) : (
                    <span className="num font-bold">{toPersianDigits(stepNumber)}</span>
                  )}
                </button>

                {/* برچسب متنی گام */}
                <div className="mt-2 text-center max-w-[4.5rem] sm:max-w-[6.5rem]">
                  <span
                    className={cn(
                      "block text-[11px] sm:text-xs leading-4 transition-colors",
                      isCurrent && "font-black text-foreground",
                      isCompleted && "font-bold text-foreground group-hover:text-primary",
                      isUpcoming && "font-medium text-muted-foreground",
                    )}
                  >
                    {step.title}
                  </span>
                  {step.description && (
                    <span className="hidden sm:block mt-0.5 text-[10px] text-muted-foreground leading-3 truncate">
                      {step.description}
                    </span>
                  )}
                </div>
              </div>

              {/* خط متصل‌کننده (Connector Line) میان دایره‌ها */}
              {!isLast && (
                <div
                  aria-hidden="true"
                  className="flex-1 h-0.5 sm:h-1 mx-1.5 sm:mx-3 -mt-6 sm:-mt-6 rounded-full transition-colors duration-300 relative"
                >
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-300",
                      stepNumber < currentStep ? "bg-primary" : "bg-border",
                    )}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* نمونه استفاده کامل و تعاملی (Usage Example)                        */
/* ------------------------------------------------------------------ */

const WIZARD_STEPS: StepItem[] = [
  { id: "service", title: "خدمت", description: "پکیج یا آب‌تصفیه‌کن" },
  { id: "problem", title: "برند و مشکل", description: "شرح و ارسال تصاویر" },
  { id: "customer", title: "اطلاعات تماس", description: "نام و شماره همراه" },
  { id: "address", title: "آدرس", description: "منطقه و نشانی تهران" },
  { id: "review", title: "بازبینی", description: "تأیید نهایی درخواست" },
];

export function StepperUsageExample() {
  const [currentStep, setCurrentStep] = React.useState(2);
  const totalSteps = WIZARD_STEPS.length;

  const handleNext = () => {
    if (currentStep < totalSteps) setCurrentStep(currentStep + 1);
  };

  const handlePrev = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  return (
    <div
      dir="rtl"
      className="mx-auto w-full max-w-2xl rounded-3xl border border-border bg-background p-6 shadow-sm md:p-8"
    >
      <div className="border-b border-border pb-4 mb-6">
        <h3 className="text-lg font-extrabold text-foreground">ثبت درخواست تعمیر فوری</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          گام‌شمار راست‌چین یکپارچه ۵ مرحله‌ای همراه با ادغام تصویر در مرحله مشکل
        </p>
      </div>

      {/* کامپوننت گام‌شمار */}
      <Stepper
        steps={WIZARD_STEPS}
        currentStep={currentStep}
        onStepClick={(step) => setCurrentStep(step)}
      />

      {/* محتوای نمونه گام جاری */}
      <div className="mt-8 rounded-2xl border border-border bg-muted/30 p-5 sm:p-6">
        <div className="flex items-center justify-between pb-3 border-b border-border/80">
          <span className="text-xs font-bold text-primary">
            مرحله {toPersianDigits(currentStep)} از {toPersianDigits(totalSteps)}
          </span>
          <span className="text-xs text-muted-foreground">
            {WIZARD_STEPS[currentStep - 1].title}
          </span>
        </div>

        <div className="py-6 text-center space-y-3">
          {currentStep === 1 && (
            <div>
              <p className="text-sm font-bold text-foreground">انتخاب نوع خدمت و دستگاه</p>
              <p className="text-xs text-muted-foreground mt-1">تعمیر پکیج دیواری یا سرویس دستگاه تصفیه آب</p>
            </div>
          )}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-bold text-foreground">مشخصات برند، شرح مشکل و بارگذاری تصویر</p>
                <p className="text-xs text-muted-foreground mt-1">
                  عکس ارور یا پکیج را در همین مرحله بارگذاری کنید تا یک مرحله در ثبت صرفه‌جویی شود.
                </p>
              </div>
              <div className="rounded-xl border border-dashed border-border bg-background p-4 text-xs text-muted-foreground">
                کادر آپلود تصویر دستگاه یا کد خطا (حداکثر ۳ تصویر)
              </div>
            </div>
          )}
          {currentStep === 3 && (
            <div>
              <p className="text-sm font-bold text-foreground">اطلاعات تماس متقاضی</p>
              <p className="text-xs text-muted-foreground mt-1">نام خانوادگی و شماره موبایل برای ارسال پیامک هماهنگی</p>
            </div>
          )}
          {currentStep === 4 && (
            <div>
              <p className="text-sm font-bold text-foreground">نشانی و منطقه حضور تکنسین</p>
              <p className="text-xs text-muted-foreground mt-1">منطقه شهرداری، آدرس کامل، پلاک و واحد</p>
            </div>
          )}
          {currentStep === 5 && (
            <div>
              <p className="text-sm font-bold text-foreground">بازبینی و دریافت کد پیگیری</p>
              <p className="text-xs text-muted-foreground mt-1">بررسی صحت اطلاعات و ارسال نهایی با ضمانت خدمت</p>
            </div>
          )}
        </div>
      </div>

      {/* دکمه‌های ناوبری قبلی / بعدی */}
      <div className="mt-6 flex items-center justify-between pt-4 border-t border-border">
        <button
          type="button"
          disabled={currentStep <= 1}
          onClick={handlePrev}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-xl border border-border px-4 py-2.5 text-xs sm:text-sm font-bold transition-all",
            currentStep <= 1
              ? "cursor-not-allowed opacity-40 text-muted-foreground"
              : "cursor-pointer text-foreground hover:bg-muted active:scale-95",
          )}
        >
          <ChevronRight className="h-4 w-4" />
          <span>مرحله قبلی</span>
        </button>

        <button
          type="button"
          disabled={currentStep >= totalSteps}
          onClick={handleNext}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-xl bg-primary text-primary-foreground px-5 py-2.5 text-xs sm:text-sm font-bold shadow-xs transition-all",
            currentStep >= totalSteps
              ? "cursor-not-allowed opacity-40"
              : "cursor-pointer hover:opacity-90 active:scale-95",
          )}
        >
          <span>{currentStep === totalSteps - 1 ? "مشاهده بازبینی" : "مرحله بعدی"}</span>
          <ChevronLeft className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
