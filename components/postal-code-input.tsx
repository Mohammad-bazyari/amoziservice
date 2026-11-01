"use client";

/**
 * PostalCodeInput — میدان کد پستی ۱۰ رقمی برای فرم‌های راست‌چین (React + Tailwind).
 *
 * ویژگی‌ها
 * • میدان LTR است (dir="ltr") که ارقام به‌ترتیب غربی و ویرایش ساده بمانند؛
 *   نشان‌گرِ قُرمه (Mailbox) از lucide-react در سمت چهپ (end در RTL) می‌نشیند.
 * • نمایش با گروه‌بندی «۱۲۳۴۵-۶۷۸۹۰»: در حین تایپ ارقام فارسی می‌شوند و بعد
 *   از ۵ رقم، خط تیره خودکار می‌آید. مقدار ذخیره‌شده همیشه رشته‌ای از
 *   ۱۰ رقم لاتین (بدون خط تیره) است.
 * • ورودی فقط رقم را می‌پذیرد: صفحه‌کلید فیزیکی، صفحه‌کلید نیمه‌فارسی (عدد
 *   فارسی) و صفحه‌کلید موبایل (inputMode) همه به همان ۱۰ رقم لاتین نرمال
 *   می‌شوند. ستون‌بینی ارقام: فارسی/عربی/لاتین، بدون قلاب اضافه.
 * • اعتبار سنجی طول و رقم: «کد پستی باید ۱۰ رقم باشد.» — هیچ قاعده‌ی
 *   ساختاری جعلی (مثل «محدوده استان») اضافه نشده است.
 *   خطا فقط پس blur یا submit نشان داده می‌شود، هرگز با اولین حرف.
 * • دسترسی‌پذیری: برچسب داوری، aria-invalid و aria-describedby در خطا،
 *   حلقه‌ی فوکوس دیده‌شدنی، ناوبری کامل صفحه‌کلید (بومی input).
 *
 * نمونه استفاده
 *
 *   function AddressForm() {
 *     const [postalCode, setPostalCode] = React.useState("");
 *     const [showError, setShowError] = React.useState(false); // پس از blur/submit
 *
 *     return (
 *       <form dir="rtl">
 *         <PostalCodeInput
 *           id="postal-code"
 *           value={postalCode}
 *           onChange={setPostalCode}
 *           showError={showError}
 *           onBlur={() => setShowError(true)}
 *           // و در onSubmit هم showError=true بگذارید
 *         />
 *       </form>
 *     );
 *   }
 *
 * یا با قلاب useForm پروژه (components/form.tsx):
 *
 *   <PostalCodeInput
 *     {...form.field("postal_code")}
 *     id={form.fieldId("postal_code")}
 *     value={form.values.postal_code}
 *     onChange={(v) => form.setValue("postal_code", v)}
 *     onBlur={() => form.validateOnBlur("postal_code")}
 *     showError={form.touched.postal_code === true}
 *   />
 */

import * as React from "react";
import { Mailbox } from "lucide-react";
import { cn } from "./accordion";

/* ------------------------------------------------------------------ */
/* ابزارهای رقم                                                        */
/* ------------------------------------------------------------------ */

const PERSIAN_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"] as const;
const ARABIC_DIGITS = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"] as const;

/** هر رقم (لاتین/فارسی/عربی) را به رقم لاتین برمی‌گرداند؛ بقیه حذف می‌شوند. */
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

/** ارقام لاتین را به ارقام فارسی تبدیل می‌کند (برای نمایش). */
function toPersianDigitsSafe(value: string): string {
  return value.replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);
}

  /** سقف طول عرض واقعی input با dir="ltr" — جهت مدیریت صحیح ویرایش */
const MAX_DIGITS = 10;

/** ارقام را به گروه‌بندی «۱۲۳۴۵-۶۷۸۹۰» می‌سازد. */
function formatPostalCode(value: string): string {
  const digits = toLatinDigits(value).slice(0, MAX_DIGITS);
  const first = digits.slice(0, 5);
  const second = digits.slice(5, 10);
  if (!second) return toPersianDigitsSafe(first);
  return `${toPersianDigitsSafe(first)}-${toPersianDigitsSafe(second)}`;
}

/** پیام خطای فارسی — تنها قاعده/RESOURCE پروژه. */
export const POSTAL_CODE_ERROR = "کد پستی باید ۱۰ رقم باشد.";

/** بررسی طول و رقم — تنها قاعده‌ی معنایی: دقیقاً ۱۰ رقم (لاتین). */
export function isValidPostalCode(value: string): boolean {
  return /^\d{10}$/.test(value);
}

/* ------------------------------------------------------------------ */
/* استایل                                                              */
/* ------------------------------------------------------------------ */

/**
 * همان کنترل‌کلاس‌های form.tsx — text-sm روی دسکتاپ، ۱۶px روی iOS تا سافاری
 * صفحه را روی فوکوس بزرگ‌نمایی نکند. رنگ‌ها فقط از توکن‌های تم.
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

export type PostalCodeInputProps = {
  /** شناسه برای label htmlFor — دسترسی‌پذیری الزامی است. */
  id: string;
  /** مقدار کنترل‌شده: ۱۰ رقم لاتین (یا "" ). */
  value: string;
  /** مقدار ذخیره‌شده را برمی‌گرداند: ۱۰ رقم لاتین بدون خط تیره. */
  onChange: (value: string) => void;
  /**
   * خطا را نشان بده یا نه. این کامپوننت خودش خطا نمی‌سازد؛ فقط قاعده را
   * دارد. showError پس از blur و submit روشن می‌شود (هرگز با اولین تایپ).
   */
  showError?: boolean;
  /** برچسب فارسی — پیش‌فرض «کد پستی (اختیاری)». */
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  /** پس از خروج میدان (برای فعال کردن showError در مصرف‌کننده). */
  onBlur?: () => void;
  /** پخش روی form: name برای ارسال فرم بومی. */
  name?: string;
 autoComplete?: string;
  className?: string;
  "aria-describedby"?: string;
};

export function PostalCodeInput({
  id,
  value,
  onChange,
  showError = false,
  label = "کد پستی",
  placeholder = "۱۲۳۴۵-۶۷۸۹۰",
  disabled = false,
  onBlur,
  name,
  autoComplete = "postal-code",
  className,
  "aria-describedby": describedBy,
}: PostalCodeInputProps) {
  const errorId = `${id}-error`;
  const digits = toLatinDigits(value).slice(0, MAX_DIGITS);
  const invalid = showError && !isValidPostalCode(digits);
  const described = [
    ...(invalid ? [errorId] : []),
    ...(describedBy ? [describedBy] : []),
  ].join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5 font-sans", className)}>
      <label
        htmlFor={id}
        className="text-sm font-bold text-foreground"
      >
        {label}
      </label>
      {/*
        dir="ltr": ویرایش «۱۲۳۴۵-۶۷۸۹۰» باید از سمت چپ پیش برود.
        نشان‌گر قُرمه در انتهای خط (end در RTL صفحه) همان چپ باکس است؛
        بنابراین آیکن با ps (شروع جدید لوجیکال) فاصله می‌گیرد و input
        با pe فضای آیکن را خالی می‌گذارد.
      */}
      <div className="relative">
        <input
          id={id}
          name={name}
          type="text"
          dir="ltr"
          inputMode="numeric"
          autoComplete={autoComplete}
          maxLength={MAX_DIGITS + 1}
          // pattern عمداً ست نمی‌شود: مقدار نمایشی فیلد فارسی و خط‌دار
          // («۱۲۳۴۵-۶۷۸۹۰») است و pattern لاتینِ بومی مرورگر روی آن همیشه
          // می‌شکست و سابمیت ناتیو را بلاک می‌کرد. اعتبارسنجی فقط با قاعده
          // همین کامپوننت است (خطا پس از blur/submit، هرگز با اولین کلید)؛
          // سرور (کد پستی در forms.py) هم مرجع نهایی می‌ماند.
          value={formatPostalCode(digits)}
          onChange={(event) => onChange(toLatinDigits(event.target.value).slice(0, MAX_DIGITS))}
          onBlur={() => onBlur?.()}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={invalid || undefined}
          aria-describedby={described}
          className={cn(
            CONTROL_CLASSES,
            "pe-11 text-start", // فضا برای آیکن در سمت چپ (end با RTL والد)
            invalid && "border-destructive focus-visible:ring-destructive",
          )}
        />
        <Mailbox
          aria-hidden="true"
          className="pointer-events-none absolute end-3 top-1/2 size-5 -translate-y-1/2 text-muted-foreground"
        />
      </div>
      {invalid ? (
        <p
          id={errorId}
          role="alert"
          className="flex items-center gap-1.5 text-xs font-bold text-destructive"
        >
          {POSTAL_CODE_ERROR}
        </p>
      ) : null}
    </div>
  );
}

export default PostalCodeInput;
