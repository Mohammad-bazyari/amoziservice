"use client";

/**
 * PhoneInput — میدان شماره موبایل ایران برای فرم‌های راست‌چین (React + Tailwind).
 *
 * ویژگی‌ها
 * • میدان خودش dir="ltr" است تا ارقام و ویرایش به‌ترتیب طبیعی پیش بروند؛
 *   آیکن Smartphone از lucide-react با ویژگی‌های منطقی (end در RTL) می‌نشیند.
 * • نمایش با ارقام فارسی و گروه‌بندی «۰۹۱۲ ۱۲۳ ۴۵۶۷»؛ مقدار ذخیره‌شده
 *   همیشه رشته‌ای از ۱۱ رقم لاتین «09xxxxxxxxx» است (تلویزیون هم user
 *   ارقام فارسی تایپ کند، هم «+98…» بنویسد، نتیجه یکی است).
 * • نرمال‌سازی ورودی: حذف +98 و 0098، حذف صفرِ بلعیده‌شده، تبدیل ارقام
 *   فارسی/عربی به لاتین. قاعده‌ی اعتبار فقط طول و رقم و «09» است؛
 *   هیچ قاعده‌ی ساختاری جعلی اضافه نشده است.
 * • اپراتور از پیش‌شماره‌ی ۴ رقمی تشخیص داده می‌شود (همراه اول، ایرانسل،
 *   رایتل) و کنار میدان نشان داده می‌شود؛ ناشناخته بدون شکل است.
 * • inputMode="tel" و autoComplete="tel-national" — کیبورد عددی و
 *   پرکردن خودکار شماره ملی تلفن.
 * • اعتبارسنجی فقط طول/رقم: خطا فقط پس از blur یا submit (هرگز با
 *   اولین فشار کلید), aria-invalid + aria-describedby، حلقه‌ی فوکوس.
 *
 * توکن‌های تم: border/background/foreground/primary/ring/muted-destructive —
 * هیچ رنگ اختراع‌شده‌ای نیست. فونت از font-sans پروژه (IRANSans/Vazirmatn)؛
 * روی متن فارسی هرگز letter-spacing بیاید نیست. کنترل روی دسکتاپ text-sm
 * و زیر @supports (-webkit-touch-callout:none) دقیقاً 16px می‌شود (iOS).
 * حرکت‌ها ۲۰۰ms و زیر prefers-reduced-motion خاموش.
 *
 * نمونه استفاده
 *
 *   function ContactForm() {
 *     const [phone, setPhone] = React.useState("");
 *     const [showError, setShowError] = React.useState(false); // پس از blur/submit
 *
 *     const invalid = showError && !isValidPhone(phone);
 *
 *     return (
 *       <form dir="rtl" onSubmit={() => setShowError(true)}>
 *         <PhoneInput
 *           id="customer-phone"
 *           value={phone}
 *           onChange={setPhone}
 *           showError={showError}
 *           onBlur={() => setShowError(true)}
 *         />
 *         {invalid && <p className="text-destructive">…</p>}
 *       </form>
 *     );
 *   }
 *
 * یا با قلاب useForm پروژه (components/form.tsx):
 *
 *   <PhoneInput
 *     {...form.field("customer_phone")}
 *     value={form.values.customer_phone}
 *     onChange={(next) => form.setValue("customer_phone", next)}
 *     showError={form.touched.customer_phone === true}
 *   />
 */

import * as React from "react";
import { Smartphone } from "lucide-react";
import { cn } from "./accordion";

/* ------------------------------------------------------------------ */
/* ابزارهای رقم و نرمال‌سازی                                            */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;
const ARABIC_DIGITS = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"] as const;

/** ارقام فارسی/عربی/لاتین را به لاتین تبدیل می‌کند؛ بقیه حذف (نه جاگذاری). */
function toLatinDigits(value: string): string {
  let out = "";
  for (const char of value) {
    const persian = PERSIAN_DIGITS.indexOf(char as (typeof PERSIAN_DIGITS)[number]);
    if (persian >= 0) {
      out += String(persian);
      continue;
    }
    const arabic = ARABIC_DIGITS.indexOf(char as (typeof ARABIC_DIGITS)[number]);
    if (arabic >= 0) {
      out += String(arabic);
      continue;
    }
    if (char >= "0" && char <= "9") out += char;
  }
  return out;
}

/** ارقام لاتین را به فارسی (برای نمایش) برمی‌گرداند. */
function toPersianDigitsValue(value: string): string {
  return value.replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

/** طول مجاز شماره موبایل ایران: ۱۱ رقم لاتین. */
export const PHONE_LENGTH = 11;

/**
 * نرمال‌سازی: ارقام هرکیبورد → لاتین؛ «+98…» و «0098…» و صفرِ بلعیده‌شده
 * حذف؛ خروجی ۱۱ رقم «09xxxxxxxxx» یا آنچه مانده (برای پیام مفید طول).
 */
export function normalizePhone(raw: string): string {
  let digits = toLatinDigits(raw).replace(/[^\d]/g, "");
  if (digits.startsWith("0098")) {
    digits = digits.slice(4);
  } else if (
    (raw.trimStart().startsWith("+") || digits.length === 12) &&
    digits.startsWith("98")
  ) {
    digits = digits.slice(2);
  }
  if (digits.length === PHONE_LENGTH - 1 && digits.startsWith("9")) {
    digits = `0${digits}`;
  }
  // سقف ۱۱ رقم — همان رفتار PostalCodeInput با سقف ۱۰ رقم.
  return digits.slice(0, PHONE_LENGTH);
}

/** بررسی طول و رقم — تنها قاعده: دقیقاً ۱۱ رقم با پیش‌شماره 09. */
export function isValidPhone(value: string): boolean {
  return /^09\d{9}$/.test(value);
}

/** پیام خطای فارسی — متن واحد با فرم درخواست (messages.py سمت سرور). */
export const PHONE_ERROR = "شماره موبایل معتبر نیست؛ مثال: ۰۹۱۲۱۲۳۴۵۶۷";

/* ------------------------------------------------------------------ */
/* اپراتور                                                             */
/* ------------------------------------------------------------------ */

/** پیش‌شماره ۴ رقمی → نام اپراتور؛ فهرست صریح، هیچ قاعده‌ی جعلی نیست. */
const PREFIX_OPERATORS: Record<string, string> = {
  "0910": "همراه اول", "0911": "همراه اول", "0912": "همراه اول",
  "0913": "همراه اول", "0914": "همراه اول", "0915": "همراه اول",
  "0916": "همراه اول", "0917": "همراه اول", "0918": "همراه اول",
  "0919": "همراه اول", "0990": "همراه اول", "0991": "همراه اول",
  "0992": "همراه اول", "0993": "همراه اول", "0994": "همراه اول",
  "0996": "همراه اول",
  "0930": "ایرانسل", "0933": "ایرانسل", "0935": "ایرانسل",
  "0936": "ایرانسل", "0937": "ایرانسل", "0938": "ایرانسل",
  "0939": "ایرانسل", "0941": "ایرانسل",
  "0920": "رایتل", "0921": "رایتل", "0922": "رایتل", "0923": "رایتل",
};

/** نام اپراتور برای نمایش؛ ناشناخته → رشته‌ی خالی (هیچ چیز نشان نده). */
export function operatorFor(value: string): string {
  const digits = normalizePhone(value);
  if (!isValidPhone(digits)) return "";
  return PREFIX_OPERATORS[digits.slice(0, 4)] ?? "";
}

/* ------------------------------------------------------------------ */
/* نمایش و گروه‌بندی                                                    */
/* ------------------------------------------------------------------ */

/** «09121234567» → «۰۹۱۲ ۱۲۳ ۴۵۶۷» (ارقام فارسی، فاصله‌ی نازک). */
function formatPhone(value: string): string {
  const digits = normalizePhone(value).slice(0, PHONE_LENGTH);
  const parts = [digits.slice(0, 4), digits.slice(4, 7), digits.slice(7, 11)];
  return toPersianDigitsValue(parts.filter(Boolean).join(" "));
}

/* ------------------------------------------------------------------ */
/* استایل                                                              */
/* ------------------------------------------------------------------ */

/**
 * همان کنترل‌کلاس‌های form.tsx/postal-code-input.tsx — text-sm روی دسکتاپ،
 * 16px روی iOS تا سافاری صفحه را روی فوکوس بزرگ‌نمایی نکند؛ رنگ‌ها فقط
 * از توکن‌های تم و حلقه‌ی فوکوس همیشه دیده‌شدنی.
 */
const CONTROL_CLASSES = cn(
  "w-full rounded-xl border border-border bg-background font-sans text-foreground",
  "px-3.5 py-2.5 text-sm leading-6",
  "[@supports(-webkit-touch-callout:none)]:text-[16px]",
  "placeholder:text-muted-foreground",
  "transition-colors duration-200 motion-reduce:transition-none",
  "outline-none focus-visible:border-primary",
  "focus-visible:ring-2 focus-visible:ring-ring",
  "focus-visible:ring-offset-2 focus-visible:ring-offset-background",
  "disabled:cursor-not-allowed disabled:opacity-60",
);

/* ------------------------------------------------------------------ */
/* کامپوننت                                                            */
/* ------------------------------------------------------------------ */

export type PhoneInputProps = {
  /** شناسه برای label htmlFor — دسترسی‌پذیری الزامی است. */
  id: string;
  /** مقدار کنترل‌شده: ۱۱ رقم لاتین «09xxxxxxxxx» یا "". */
  value: string;
  /** مقدار ذخیره‌شده را برمی‌گرداند: ۱۱ رقم لاتین بدون فاصله. */
  onChange: (value: string) => void;
  /**
   * خطا را نشان بده یا نه. این کامپوننت خودش خطا نمی‌سازد؛ showError پس
   * از blur و submit روشن می‌شود (هرگز با اولین فشار کلید).
   */
  showError?: boolean;
  /** برچسب فارسی — پیش‌فرض «شماره موبایل». */
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  /** پس از خروج میدان (برای روشن شدن showError در مصرف‌کننده). */
  onBlur?: () => void;
  /** پخش روی فرم: name برای ارسال بومی. */
  name?: string;
  autoComplete?: string;
  className?: string;
  /** شناسه‌ی توضیح دیگر (مثلاً hint) که با پیام خطا ترکیب می‌شود. */
  "aria-describedby"?: string;
};

export function PhoneInput({
  id,
  value,
  onChange,
  showError = false,
  label = "شماره موبایل",
  placeholder = "۰۹۱۲ ۱۲۳ ۴۵۶۷",
  disabled = false,
  onBlur,
  name,
  autoComplete = "tel-national",
  className,
  "aria-describedby": describedBy,
}: PhoneInputProps) {
  const errorId = `${id}-error`;
  const digits = normalizePhone(value).slice(0, PHONE_LENGTH);
  const invalid = showError && !isValidPhone(digits);
  const operator = operatorFor(digits);

  const described = [
    ...(invalid ? [errorId] : []),
    ...(describedBy ? [describedBy] : []),
  ]
    .filter(Boolean)
    .join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5 font-sans", className)}>
      <span className="flex items-baseline justify-between gap-2">
        <label htmlFor={id} className="text-sm font-bold text-foreground">
          {label}
        </label>
        {/*
          نام اپراتور فقط وقتی شماره ۱۱ رقم معتبر است دیده می‌شود؛
          بدون هیچ رنگ اختراعی — text-muted-foreground.
        */}
        <span
          aria-live="polite"
          className={cn(
            "text-xs font-bold leading-6 text-muted-foreground",
            "transition-opacity duration-200 motion-reduce:transition-none",
            operator ? "opacity-100" : "opacity-0",
          )}
        >
          {operator || "\u00A0"}
        </span>
      </span>
      {/*
        dir="ltr": شماره از سمت چپ تایپ و ویرایش می‌شود؛ آیکن گوشی
        در انتهای خط (به end نامیده می‌شود — در RTL همان سمت چپ).
      */}
      <div className="relative">
        <input
          id={id}
          name={name}
          type="tel"
          dir="ltr"
          inputMode="tel"
          autoComplete={autoComplete}
          maxLength={PHONE_LENGTH + 6} // جای «+98» و فاصله‌های تایپ
          value={formatPhone(digits)}
          onChange={(event) => onChange(normalizePhone(event.target.value))}
          onBlur={() => onBlur?.()}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={invalid || undefined}
          aria-describedby={described}
          className={cn(
            CONTROL_CLASSES,
            "pe-11", // فضا برای آیکن در انتهای خط (end)
            invalid && "border-destructive focus-visible:ring-destructive",
          )}
        />
        <Smartphone
          aria-hidden="true"
          className="pointer-events-none absolute end-3 top-1/2 size-5 -translate-y-1/2 text-muted-foreground"
        />
      </div>
      {invalid ? (
        <p
          id={errorId}
          role="alert"
          className="text-xs font-bold leading-6 text-destructive"
        >
          {PHONE_ERROR}
        </p>
      ) : null}
    </div>
  );
}

export default PhoneInput;
