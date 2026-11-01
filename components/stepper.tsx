"use client";

/**
 * Stepper — مؤلفه گام‌شمار چندمرحله‌ای دسترس‌پذیر برای رابط‌های راست‌چین (React + Tailwind CSS).
 *
 * ویژگی‌های کلیدی
 * • گام‌های تکمیل‌شده: دارای علامت تیک (`Check`) و پس‌زمینه شاخص `bg-primary text-primary-foreground`.
 * • گام جاری: دارای کادر یا حلقه برجسته (`ring-2 ring-primary ring-offset-2`) و نشانگر `aria-current="step"`.
 * • سایر گام‌ها: دارای کادر خاکستری خنثی (`border-2 border-border text-muted-foreground`).
 * • خط اتصال رابط بین دایره‌ها: با پیشروی کاربر از خاکستری به رنگ اصلی (`bg-primary`) تغییر می‌کند.
 * • چیدمان کاملاً راست‌چین (`dir="rtl"`) با بهره‌گیری انحصاری از ویژگی‌های منطقی (start/end/ms/me/ps/pe).
 * • صفحه‌کلید و A11y: ناوبری با کلیدهای ArrowLeft (مرحله بعد در RTL) و ArrowRight (مرحله قبل در RTL)،
 *   پشتیبانی از Home و End، اعلام‌های متنی برای صفحه‌خوان‌ها.
 * • فرم درخواست تعمیرات با ۵ مرحله (ادغام مرحله تصاویر در مرحله ثبت مشکل):
 *   ۱. انتخاب خدمت ۲. شرح مشکل و بارگذاری تصویر ۳. اطلاعات تماس ۴. نشانی و زمان ۵. بازبینی و تایید نهایی.
 *
 * نمونه استفاده سریع
 *
 *   import { Stepper, StepItem } from "@/components/stepper";
 *
 *   const steps: StepItem[] = [
 *     { id: "service", title: "انتخاب خدمت", description: "پکیج، کولر یا تصفیه" },
 *     { id: "problem", title: "شرح مشکل و تصاویر", description: "برند، ایراد و عکس دستگاه" },
 *     { id: "customer", title: "اطلاعات تماس", description: "نام و شماره همراه" },
 *     { id: "address", title: "نشانی و زمان", description: "منطقه و آدرس دقیق" },
 *     { id: "review", title: "بازبینی و ثبت", description: "تایید نهایی اطلاعات" },
 *   ];
 *
 *   export function MyWizard() {
 *     const [current, setCurrent] = React.useState(1);
 *     return (
 *       <Stepper
 *         steps={steps}
 *         currentStep={current}
 *         onStepClick={(idx) => setCurrent(idx)}
 *       />
 *     );
 *   }
 */

import * as React from "react";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  FileText,
  Flame,
  ImagePlus,
  Loader2,
  MapPin,
  Phone,
  RotateCcw,
  ShieldCheck,
  Trash2,
  UploadCloud,
  User,
  Wrench,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/* ابزارهای کمکی، ارقام فارسی و فرمت مبالغ                            */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;

/** جداکننده‌ی هزارگان فارسی (U+066C) */
export const THOUSANDS_SEPARATOR = "٬";

/** تبدیل ارقام لاتین به ارقام فارسی (۰–۹) */
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

/** قالب‌بندی حجم فایل‌ها با ارقام فارسی */
export function formatFileSize(bytes: number): string {
  if (bytes >= 1048576) {
    const mb = (bytes / 1048576).toFixed(1);
    return `${toPersianDigits(mb)} مگابایت`;
  }
  const kb = Math.max(1, Math.round(bytes / 1024));
  return `${toPersianDigits(kb)} کیلوبایت`;
}

/** ترکیب کلاس‌های شرطی Tailwind بدون نیاز به کتابخانه اضافی */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/* ------------------------------------------------------------------ */
/* انواع و اینترفیس‌ها                                                */
/* ------------------------------------------------------------------ */

export type StepStatus = "complete" | "current" | "upcoming";

export interface StepItem {
  /** شناسه یکتای مرحله */
  id: string;
  /** عنوان مرحله (نمایش در رابط کاربری) */
  title: string;
  /** توضیح کوتاه زیر عنوان (اختیاری) */
  description?: string;
  /** برچسب مرحله اختیاری */
  optional?: boolean;
}

export interface StepperProps {
  /** آرایه‌ای از اطلاعات مراحل */
  steps: StepItem[];
  /** ایندکس مرحله جاری (مبتنی بر صفر: 0 تا steps.length - 1) */
  currentStep: number;
  /** رویداد کلیک روی مرحله (مثلاً برای بازگشت به مراحل قبلی) */
  onStepClick?: (stepIndex: number) => void;
  /** جهت نمایش: افقی (پیش‌فرض) یا عمودی */
  orientation?: "horizontal" | "vertical";
  /** امکان کلیک فقط روی مراحل تکمیل‌شده (پیش‌فرض: true) */
  allowClickCompleted?: boolean;
  /** کلاس‌های سی‌اس‌اس سفارشی */
  className?: string;
  /** برچسب دسترس‌پذیری برای ناوبری مراحل */
  ariaLabel?: string;
}

/* ------------------------------------------------------------------ */
/* مؤلفه اصلی Stepper                                                 */
/* ------------------------------------------------------------------ */

export function Stepper({
  steps,
  currentStep,
  onStepClick,
  orientation = "horizontal",
  allowClickCompleted = true,
  className,
  ariaLabel = "مراحل ثبت درخواست",
}: StepperProps) {
  const isVertical = orientation === "vertical";
  const stepListRef = React.useRef<HTMLOListElement>(null);

  // ناوبری کیبورد بین مراحل با رعایت قواعد RTL:
  // در زبان فارسی راست‌به‌چپ، پیکان چپ یعنی حرکت رو به جلو (گام بعد)
  // و پیکان راست یعنی حرکت رو به عقب (گام قبل).
  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (!onStepClick) return;

    let targetIndex: number | null = null;
    if (e.key === "ArrowLeft") {
      // در RTL پیکان چپ به جلو می‌رود
      if (index + 1 < steps.length && (allowClickCompleted ? index + 1 <= currentStep : true)) {
        targetIndex = index + 1;
      }
    } else if (e.key === "ArrowRight") {
      // در RTL پیکان راست به عقب می‌رود
      if (index - 1 >= 0) {
        targetIndex = index - 1;
      }
    } else if (e.key === "Home") {
      targetIndex = 0;
    } else if (e.key === "End") {
      targetIndex = allowClickCompleted ? Math.min(currentStep, steps.length - 1) : steps.length - 1;
    }

    if (targetIndex !== null) {
      e.preventDefault();
      onStepClick(targetIndex);
      // انتقال فوکوس به دکمه هدف
      const buttons = stepListRef.current?.querySelectorAll<HTMLButtonElement>("button[data-step-button]");
      buttons?.[targetIndex]?.focus();
    }
  };

  return (
    <nav aria-label={ariaLabel} dir="rtl" className={cn("w-full select-none", className)}>
      <ol
        ref={stepListRef}
        className={cn(
          isVertical ? "flex flex-col gap-4" : "flex items-center justify-between gap-1 sm:gap-2",
        )}
      >
        {steps.map((step, index) => {
          const status: StepStatus =
            index < currentStep ? "complete" : index === currentStep ? "current" : "upcoming";
          const isInteractive = Boolean(
            onStepClick && (allowClickCompleted ? index <= currentStep : true),
          );
          const isLast = index === steps.length - 1;

          return (
            <li
              key={step.id}
              className={cn(
                "relative flex items-center",
                isVertical ? "w-full" : "flex-1 last:flex-initial",
              )}
            >
              <div
                className={cn(
                  "group flex items-center gap-2.5 sm:gap-3",
                  isVertical ? "w-full" : "min-w-0 flex-1",
                )}
              >
                {/* دکمه یا نگهدارنده نشانگر مرحله */}
                <button
                  type="button"
                  data-step-button
                  disabled={!isInteractive}
                  onClick={() => isInteractive && onStepClick?.(index)}
                  onKeyDown={(e) => handleKeyDown(e, index)}
                  aria-current={status === "current" ? "step" : undefined}
                  tabIndex={isInteractive ? 0 : -1}
                  className={cn(
                    "relative flex shrink-0 items-center justify-center rounded-full transition-all duration-200",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                    isInteractive && status !== "current" && "cursor-pointer hover:scale-105 active:scale-95",
                    !isInteractive && "cursor-default",
                    // استایل‌های وضعیتی بر اساس نیازمندی دقیق کاربر:
                    // • گام تکمیل‌شده: تیک و bg-primary
                    // • گام جاری: کادر حلقه‌ای ring
                    // • سایر گام‌ها: کادر خاکستری
                    status === "complete" &&
                      "h-9 w-9 sm:h-10 sm:w-10 bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
                    status === "current" &&
                      "h-9 w-9 sm:h-10 sm:w-10 border-2 border-primary bg-background text-primary font-bold ring-4 ring-primary/20 dark:ring-primary/30 shadow-sm",
                    status === "upcoming" &&
                      "h-9 w-9 sm:h-10 sm:w-10 border-2 border-border bg-muted/30 text-muted-foreground font-medium",
                  )}
                  aria-label={`مرحله ${toPersianDigits(index + 1)}: ${step.title} ${
                    status === "complete"
                      ? "(تکمیل شده)"
                      : status === "current"
                      ? "(در حال تکمیل)"
                      : "(در انتظار)"
                  }`}
                >
                  {status === "complete" ? (
                    <Check className="h-4 w-4 sm:h-5 sm:w-5 stroke-[2.5]" aria-hidden="true" />
                  ) : (
                    <span className="text-xs sm:text-sm">{toPersianDigits(index + 1)}</span>
                  )}
                </button>

                {/* متون مرحله (عنوان و توضیح) */}
                <div className={cn("min-w-0 flex-1 text-start", !isVertical && "hidden md:block")}>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "truncate text-xs sm:text-sm font-bold transition-colors",
                        status === "current" && "text-primary",
                        status === "complete" && "text-foreground",
                        status === "upcoming" && "text-muted-foreground",
                      )}
                    >
                      {step.title}
                    </span>
                    {step.optional && (
                      <span className="shrink-0 text-[10px] text-muted-foreground/80">
                        (اختیاری)
                      </span>
                    )}
                  </div>
                  {step.description && (
                    <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
                      {step.description}
                    </p>
                  )}
                </div>
              </div>

              {/* خط اتصال رابط بین دایره‌ها */}
              {!isLast && (
                <div
                  aria-hidden="true"
                  className={cn(
                    isVertical
                      ? "absolute start-4 sm:start-5 top-10 -bottom-4 w-0.5"
                      : "mx-1.5 sm:mx-3 h-0.5 flex-1 min-w-3 sm:min-w-6",
                    "transition-colors duration-300",
                    index < currentStep ? "bg-primary" : "bg-border dark:bg-muted",
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/* نمونه پیاده‌سازی فرم ثبت درخواست پکیج با ادغام تصاویر در مرحله مشکل   */
/* ------------------------------------------------------------------ */

export interface UploadedFileItem {
  id: string;
  name: string;
  size: number;
  previewUrl: string;
}

export function RequestWizardStepperExample() {
  // تعریف دقیق ۵ مرحله مطابق درخواست کاربر
  const wizardSteps: StepItem[] = [
    {
      id: "service",
      title: "انتخاب خدمت",
      description: "نوع دستگاه تعمیری",
    },
    {
      id: "problem",
      title: "شرح مشکل و تصاویر",
      description: "برند، ایراد و بارگذاری عکس",
    },
    {
      id: "customer",
      title: "اطلاعات تماس",
      description: "مشخصات هماهنگی",
    },
    {
      id: "address",
      title: "نشانی و زمان",
      description: "آدرس و زمان اعزام",
    },
    {
      id: "review",
      title: "بازبینی و ثبت",
      description: "تایید نهایی درخواست",
    },
  ];

  // وضعیت فرم
  const [currentStep, setCurrentStep] = React.useState(0);
  const [selectedService, setSelectedService] = React.useState("boiler");
  const [brand, setBrand] = React.useState("بوتان");
  const [problemDescription, setProblemDescription] = React.useState("افت فشار مکرر و گرم نشدن آب مصرفی");
  const [images, setImages] = React.useState<UploadedFileItem[]>([]);
  const [fullName, setFullName] = React.useState("رضا محمدی");
  const [phone, setPhone] = React.useState("09121234567");
  const [district, setDistrict] = React.useState("منطقه ۵ (صادقیه - پونک)");
  const [address, setAddress] = React.useState("بزرگراه اشرفی اصفهانی، خیابان گلستان، پلاک ۱۲، واحد ۳");
  const [preferredTime, setPreferredTime] = React.useState("صبح (۹ تا ۱۳)");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isSubmitted, setIsSubmitted] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState("");

  // هزینه کارشناسی اولیه طبق استانداردهای پروژه
  const inspectionFee = 350000;

  // شبیه‌سازی افزودن تصویر
  const handleAddSampleImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    if (images.length >= 3) {
      setErrorMessage("حداکثر ۳ تصویر می‌توانید بارگذاری کنید.");
      return;
    }

    setErrorMessage("");
    const file = files[0];
    const newImage: UploadedFileItem = {
      id: Math.random().toString(36).substring(2, 9),
      name: file.name,
      size: file.size,
      previewUrl: URL.createObjectURL(file),
    };

    setImages((prev) => [...prev, newImage]);
    e.target.value = "";
  };

  const handleRemoveImage = (id: string) => {
    setImages((prev) => prev.filter((img) => img.id !== id));
  };

  const handleNext = () => {
    setErrorMessage("");
    if (currentStep === 2 && (!fullName.trim() || !phone.trim())) {
      setErrorMessage("لطفاً نام و شماره همراه خود را وارد کنید.");
      return;
    }
    if (currentStep === 3 && !address.trim()) {
      setErrorMessage("لطفاً نشانی دقیق محل را وارد کنید.");
      return;
    }

    if (currentStep < wizardSteps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      // ثبت نهایی
      setIsSubmitting(true);
      setTimeout(() => {
        setIsSubmitting(false);
        setIsSubmitted(true);
      }, 900);
    }
  };

  const handlePrev = () => {
    setErrorMessage("");
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setIsSubmitted(false);
    setImages([]);
  };

  return (
    <div
      dir="rtl"
      className="mx-auto w-full max-w-3xl rounded-2xl border border-border bg-background p-4 sm:p-6 md:p-8 shadow-sm transition-all"
    >
      {/* سربرگ فرم */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-5">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-foreground">
            ثبت درخواست تعمیر لوازم خانگی
          </h2>
          <p className="mt-1 text-xs sm:text-sm text-muted-foreground">
            مرحله {toPersianDigits(currentStep + 1)} از {toPersianDigits(wizardSteps.length)}:{" "}
            <span className="font-bold text-foreground">{wizardSteps[currentStep].title}</span>
          </p>
        </div>
        <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-bold text-primary">
          <ShieldCheck className="h-4 w-4" />
          <span>تضمین قطعات اصل</span>
        </div>
      </div>

      {/* کامپوننت گام‌شمار Stepper */}
      <div className="mb-8">
        <Stepper
          steps={wizardSteps}
          currentStep={currentStep}
          onStepClick={(step) => {
            setErrorMessage("");
            setCurrentStep(step);
          }}
        />
      </div>

      {/* پیام خطای فرم */}
      {errorMessage && (
        <div
          role="alert"
          className="mb-5 flex items-center gap-2.5 rounded-xl border border-destructive/30 bg-destructive/10 p-3.5 text-xs sm:text-sm font-bold text-destructive"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* محتوای گام‌های فرم */}
      <div className="min-h-[280px]">
        {isSubmitted ? (
          /* وضعیت نهایی پس از ثبت */
          <div className="flex flex-col items-center justify-center py-8 text-center animate-fade-in">
            <div className="grid h-16 w-16 place-items-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-10 w-10 stroke-[2.2]" />
            </div>
            <h3 className="mt-4 text-lg sm:text-xl font-extrabold text-foreground">
              درخواست شما با موفقیت ثبت شد
            </h3>
            <p className="mt-2 max-w-md text-xs sm:text-sm leading-6 text-muted-foreground">
              کد پیگیری شما <span className="font-bold text-primary num">BR-۸۴۹۲</span> است.
              کارشناس فنی جهت هماهنگی ساعت اعزام ظرف ۱۵ دقیقه آینده با شما تماس خواهد گرفت.
            </p>
            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs sm:text-sm font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                <RotateCcw className="h-4 w-4" />
                ثبت درخواست جدید
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* گام ۱: انتخاب خدمت */}
            {currentStep === 0 && (
              <div className="space-y-4">
                <label className="block text-sm font-bold text-foreground">
                  نوع دستگاهی که نیاز به تعمیر دارد را انتخاب کنید:
                </label>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {[
                    { id: "boiler", title: "تعمیر پکیج دیواری و زمینی", desc: "رفع ارور، افت فشار، سرویس دوره‌ای", icon: Flame },
                    { id: "purifier", title: "سرویس دستگاه تصفیه آب", desc: "تعویض فیلترها، رفع نشتی و افت خروجی", icon: Wrench },
                    { id: "radiator", title: "هواگیری و رسوب‌زدایی رادیاتور", desc: "گرم نشدن پره‌ها و مدار شوفاژ", icon: Flame },
                    { id: "cooler", title: "تعمیر و شارژ گاز کولر گازی", desc: "سرمایش ضعیف، سرویس فصلی", icon: Wrench },
                  ].map((s) => {
                    const Icon = s.icon;
                    const isSelected = selectedService === s.id;
                    return (
                      <button
                        type="button"
                        key={s.id}
                        onClick={() => setSelectedService(s.id)}
                        className={cn(
                          "flex items-start gap-3 rounded-xl border p-4 text-start transition-all cursor-pointer",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                          isSelected
                            ? "border-primary bg-primary/5 text-primary ring-1 ring-primary shadow-xs"
                            : "border-border bg-background hover:border-primary/40 hover:bg-muted/30 text-foreground",
                        )}
                      >
                        <div
                          className={cn(
                            "grid h-10 w-10 shrink-0 place-items-center rounded-lg transition-colors",
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted text-muted-foreground",
                          )}
                        >
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-bold text-foreground">{s.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{s.desc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* گام ۲: شرح مشکل و بارگذاری تصویر (ادغام تصاویر در این گام) */}
            {currentStep === 1 && (
              <div className="space-y-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="brand-select"
                      className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                    >
                      برند یا مارک دستگاه:
                    </label>
                    <select
                      id="brand-select"
                      value={brand}
                      onChange={(e) => setBrand(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="بوتان">بوتان (Butane)</option>
                      <option value="ایران رادیاتور">ایران رادیاتور (Iran Radiator)</option>
                      <option value="شاپه">شاپه (Chappee)</option>
                      <option value="آریستون">آریستون (Ariston)</option>
                      <option value="باکسی">باکسی (Baxi)</option>
                      <option value="لورچ">لورچ (Lorch)</option>
                      <option value="سایر">سایر مارک‌ها</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="problem-quick"
                      className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                    >
                      ایراد اصلی مشاهده‌شده:
                    </label>
                    <select
                      id="problem-quick"
                      onChange={(e) => setProblemDescription(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="افت فشار مکرر و گرم نشدن آب مصرفی">افت فشار مکرر و آب ولرم</option>
                      <option value="نشتی آب از زیر بدنه یا اتصالات">نشتی آب از مدار یا لوله‌ها</option>
                      <option value="روشن نشدن و نمایش کد خطا روی برد">دستگاه روشن نمی‌شود / کد ارور</option>
                      <option value="انفجاری روشن شدن و صدای شدید پمپ">صدای غیرعادی و لرزش</option>
                      <option value="رادیاتورها سرد هستند ولی آب مصرفی داغ است">رادیاتورها گرم نمی‌شوند</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="problem-desc"
                    className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                  >
                    توضیحات تکمیلی خرابی:
                  </label>
                  <textarea
                    id="problem-desc"
                    rows={2}
                    value={problemDescription}
                    onChange={(e) => setProblemDescription(e.target.value)}
                    placeholder="در صورت وجود پیام خطا یا توضیحی درباره شرایط خرابی، بنویسید..."
                    className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs sm:text-sm leading-6 text-foreground placeholder:text-muted-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                {/* بخش بارگذاری تصاویر (ادغام‌شده در گام ثبت مشکل) */}
                <div className="rounded-xl border border-dashed border-border bg-muted/20 p-4 sm:p-5">
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2">
                      <ImagePlus className="h-4 w-4 text-primary" />
                      <span className="text-xs sm:text-sm font-bold text-foreground">
                        تصویر دستگاه یا ارور نمایشگر (اختیاری)
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground font-medium">
                      حداکثر {toPersianDigits(3)} تصویر تا ۵ مگابایت
                    </span>
                  </div>

                  <p className="text-xs leading-5 text-muted-foreground mb-4">
                    ارسال تصویر پلاک یا صفحه نمایش ارور، عیب‌یابی را دقیق‌تر و اعلام هزینه تلفنی را
                    سریع‌تر می‌کند.
                  </p>

                  {/* دراپ‌زون و دکمه انتخاب فایل */}
                  <label className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-primary/40 bg-background/80 px-4 py-6 text-center transition hover:border-primary hover:bg-primary/5 cursor-pointer">
                    <UploadCloud className="h-8 w-8 text-primary" />
                    <span className="text-xs sm:text-sm font-bold text-foreground">
                      برای انتخاب تصویر کلیک کنید
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      فرمت‌های مجاز: JPG ،PNG یا WebP
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      className="sr-only"
                      onChange={handleAddSampleImage}
                    />
                  </label>

                  {/* لیست تصاویر انتخاب‌شده */}
                  {images.length > 0 && (
                    <ul className="mt-3.5 space-y-2" aria-label="تصاویر انتخاب شده">
                      {images.map((img) => (
                        <li
                          key={img.id}
                          className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background p-2.5 text-xs"
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <img
                              src={img.previewUrl}
                              alt={img.name}
                              className="h-9 w-9 rounded-md object-cover border border-border"
                            />
                            <div className="min-w-0">
                              <p className="truncate font-bold text-foreground">{img.name}</p>
                              <p className="text-[10px] text-muted-foreground num">
                                {formatFileSize(img.size)}
                              </p>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveImage(img.id)}
                            className="rounded-lg p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition cursor-pointer"
                            aria-label={`حذف تصویر ${img.name}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}

            {/* گام ۳: اطلاعات تماس */}
            {currentStep === 2 && (
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="client-name"
                    className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                  >
                    نام و نام خانوادگی متقاضی:
                  </label>
                  <div className="relative">
                    <input
                      id="client-name"
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="مثال: رضا محمدی"
                      className="w-full rounded-xl border border-border bg-background ps-10 pe-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground placeholder:text-muted-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <User className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="client-phone"
                    className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                  >
                    شماره تلفن همراه (جهت تماس تکنسین):
                  </label>
                  <div className="relative">
                    <input
                      id="client-phone"
                      type="tel"
                      dir="ltr"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="09121234567"
                      className="w-full rounded-xl border border-border bg-background ps-10 pe-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground placeholder:text-muted-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary num text-end"
                    />
                    <Phone className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    پیامک تایید درخواست و نام تکنسین به این شماره ارسال می‌گردد.
                  </p>
                </div>
              </div>
            )}

            {/* گام ۴: نشانی و زمان */}
            {currentStep === 3 && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="district-select"
                      className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                    >
                      منطقه تهران:
                    </label>
                    <select
                      id="district-select"
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="منطقه ۲ (سعادت‌آباد - شهرک غرب)">منطقه ۲ (سعادت‌آباد - شهرک غرب)</option>
                      <option value="منطقه ۳ (ونک - میرداماد - ظفر)">منطقه ۳ (ونک - میرداماد - ظفر)</option>
                      <option value="منطقه ۵ (صادقیه - پونک)">منطقه ۵ (صادقیه - پونک)</option>
                      <option value="منطقه ۶ (یوسف‌آباد - امیرآباد)">منطقه ۶ (یوسف‌آباد - امیرآباد)</option>
                      <option value="منطقه ۲۲ (چیتگر - دریاچه)">منطقه ۲۲ (چیتگر - دریاچه)</option>
                      <option value="سایر مناطق ۲۲گانه">سایر مناطق تهران</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="timing-select"
                      className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                    >
                      بازه زمانی ترجیحی مراجعه:
                    </label>
                    <select
                      id="timing-select"
                      value={preferredTime}
                      onChange={(e) => setPreferredTime(e.target.value)}
                      className="w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-xs sm:text-sm font-bold text-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    >
                      <option value="فوری (کمتر از ۲ ساعت)">اعزام فوری (کمتر از ۲ ساعت)</option>
                      <option value="صبح (۹ تا ۱۳)">شیفت صبح (۹ تا ۱۳)</option>
                      <option value="عصر (۱۴ تا ۱۸)">شیفت بعدازظهر (۱۴ تا ۱۸)</option>
                      <option value="شب (۱۹ تا ۲۲)">شیفت شب (۱۹ تا ۲۲)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="full-address"
                    className="mb-1.5 block text-xs sm:text-sm font-bold text-foreground"
                  >
                    نشانی دقیق محل و پلاک:
                  </label>
                  <div className="relative">
                    <textarea
                      id="full-address"
                      rows={2}
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="خیابان، کوچه، پلاک، زنگ یا طبقه..."
                      className="w-full rounded-xl border border-border bg-background ps-10 pe-3.5 py-2.5 text-xs sm:text-sm leading-6 text-foreground placeholder:text-muted-foreground shadow-xs transition focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <MapPin className="absolute start-3 top-3 h-4 w-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
              </div>
            )}

            {/* گام ۵: بازبینی و تایید نهایی */}
            {currentStep === 4 && (
              <div className="space-y-4">
                <div className="rounded-xl border border-border bg-muted/10 p-4 sm:p-5">
                  <h4 className="flex items-center gap-2 text-xs sm:text-sm font-bold text-foreground mb-3 pb-2 border-b border-border">
                    <FileText className="h-4 w-4 text-primary" />
                    خلاصه مشخصات درخواست شما
                  </h4>

                  <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                    <div>
                      <dt className="text-muted-foreground">خدمت و برند:</dt>
                      <dd className="font-bold text-foreground mt-0.5">
                        تعمیر پکیج دیواری — برند {brand}
                      </dd>
                    </div>

                    <div>
                      <dt className="text-muted-foreground">نام متقاضی و شماره:</dt>
                      <dd className="font-bold text-foreground mt-0.5">
                        {fullName} (<span className="num">{toPersianDigits(phone)}</span>)
                      </dd>
                    </div>

                    <div className="sm:col-span-2">
                      <dt className="text-muted-foreground">شرح ایراد دستگاه:</dt>
                      <dd className="text-foreground mt-0.5 leading-6">{problemDescription}</dd>
                    </div>

                    <div>
                      <dt className="text-muted-foreground">تصاویر پیوست شده:</dt>
                      <dd className="font-bold text-foreground mt-0.5">
                        {images.length > 0 ? (
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {toPersianDigits(images.length)} تصویر ضمیمه شد
                          </span>
                        ) : (
                          <span className="text-muted-foreground">بدون تصویر</span>
                        )}
                      </dd>
                    </div>

                    <div>
                      <dt className="text-muted-foreground">زمان اعزام انتخابی:</dt>
                      <dd className="font-bold text-foreground mt-0.5">{preferredTime}</dd>
                    </div>

                    <div className="sm:col-span-2">
                      <dt className="text-muted-foreground">محدوده و نشانی:</dt>
                      <dd className="text-foreground mt-0.5 leading-6">
                        {district} — {address}
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* برآورد هزینه کارشناسی اولیه */}
                <div className="flex items-center justify-between rounded-xl border border-primary/20 bg-primary/5 p-4 text-xs sm:text-sm">
                  <div>
                    <p className="font-bold text-foreground">هزینه عیب‌یابی و ایاب‌وذهاب تکنسین:</p>
                    <p className="mt-0.5 text-[11px] text-muted-foreground">
                      هزینه نهایی پس از بررسی حضوری و قبل از شروع کار توافق می‌گردد.
                    </p>
                  </div>
                  <span className="text-base font-extrabold text-primary">
                    {formatToman(inspectionFee)}
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* دکمه‌های ناوبری مراحل */}
      {!isSubmitted && (
        <div className="mt-8 flex items-center justify-between gap-3 border-t border-border pt-4 sm:pt-6">
          {currentStep > 0 ? (
            <button
              type="button"
              onClick={handlePrev}
              disabled={isSubmitting}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-4 py-2.5 text-xs sm:text-sm font-bold text-foreground shadow-xs transition hover:bg-muted active:scale-98 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer disabled:opacity-50"
            >
              {/* در RTL آیکن قبل رو به راست اشاره می‌کند */}
              <ArrowRight className="h-4 w-4" />
              مرحله قبل
            </button>
          ) : (
            <div />
          )}

          <button
            type="button"
            onClick={handleNext}
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-xs sm:text-sm font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90 active:scale-98 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary cursor-pointer disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                در حال ثبت اطلاعات...
              </>
            ) : currentStep === wizardSteps.length - 1 ? (
              <>
                تایید و ثبت نهایی
                <Check className="h-4 w-4 stroke-[2.5]" />
              </>
            ) : (
              <>
                مرحله بعد
                {/* در RTL آیکن بعد رو به چپ اشاره می‌کند */}
                <ArrowLeft className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
