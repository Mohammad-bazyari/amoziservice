"use client";

/**
 * Form — فرم راست‌چین با اعتبارسنجی فارسی (React + Tailwind CSS).
 *
 * قطعه‌ها
 * • useForm — قلاب اعتبارسنجی با useState. هر میدان قواعد مرتب دارد و
 *   «اولین قاعده‌ی ناکام» پیام خطا را می‌دهد. اعتبارسنجی یک میدان پس از
 *   blur انجام می‌شود و هنگام ارسال، همه‌ی میدان‌ها یک‌جا بررسی می‌شوند.
 * • field(name) — id/name/value/onChange/onBlur/error (به‌همراه aria-invalid و
 *   aria-describedby) برمی‌گرداند تا مستقیماً روی Input پخش شود.
 * • FormErrors — خلاصه‌ی خطاها با پیوند به هر میدان؛ کلیک روی پیوند همان
 *   کنترل را فوکوس می‌کند.
 * • Input / Textarea / Select / FormField — کنترل‌های پایه با رنگ و فوکوس تم.
 *
 * توکن‌های لازم تم (رنگ اختراع نشده است)
 *   background · foreground · muted · muted-foreground · border · ring ·
 *   primary · primary-foreground · destructive
 *
 * قواعد فارسی و RTL
 * • dir="rtl" روی فرم؛ فاصله‌ها و حاشیه‌ها با ویژگی‌های منطقی (ps/pe/ms/me/start/end).
 * • هیچ letter-spacing روی متن فارسی اعمال نمی‌شود.
 * • اعداد دیدنی با ارقام فارسی؛ شمارش خطاها با toPersianDigits.
 * • فونت از توکن پروژه (--font-sans = Vazirmatn یا IRANSans).
 * • کنترل‌ها روی دسکتاپ text-sm و زیر @supports (-webkit-touch-callout:none)
 *   دقیقاً ۱۶px می‌شوند تا سافاری iOS صفحه را روی فوکوس بزرگ‌نمایی نکند.
 * • حرکت‌ها ۲۰۰ms و زیر prefers-reduced-motion خاموش.
 *
 * نمونه استفاده
 *
 *   function RequestForm() {
 *     const form = useForm({
 *       fields: {
 *         name: {
 *           label: "نام و نام خانوادگی",
 *           rules: [required("نام خود را بنویسید.")],
 *         },
 *         phone: {
 *           label: "شماره موبایل",
 *           rules: [
 *             required("شماره موبایل را وارد کنید."),
 *             matches(/^09\d{9}$/, "شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷)."),
 *           ],
 *         },
 *       },
 *       onSubmit: (values) => console.log(values),
 *     });
 *
 *     return (
 *       <Form form={form} aria-label="فرم درخواست تعمیر">
 *         <FormField label="نام و نام خانوادگی" htmlFor={form.fieldId("name")} required error={form.field("name").error}>
 *           <Input placeholder="مثلاً علی محمدی" {...form.field("name")} />
 *         </FormField>
 *         <FormField label="شماره موبایل" htmlFor={form.fieldId("phone")} required error={form.field("phone").error}>
 *           <Input inputMode="numeric" className="num" {...form.field("phone")} />
 *         </FormField>
 *         <button type="submit" className="...">ثبت درخواست</button>
 *       </Form>
 *     );
 *   }
 */

import * as React from "react";
import { AlertCircle, ChevronDown } from "lucide-react";
import { cn, toPersianDigits } from "./accordion";

/* ------------------------------------------------------------------ */
/* انواع                                                               */
/* ------------------------------------------------------------------ */

/** مقادیر فرم: نگاشت نام میدان → مقدار متنی. */
export type FormValues = Record<string, string>;

/** خطاها: نگاشت نام میدان → پیام فارسی (نبودِ کلید یعنی بدون خطا). */
export type FormErrorMap = Record<string, string>;

/**
 * یک قاعده‌ی اعتبارسنجی. اگر معتبر باشد چیزی برنمی‌گرداند؛ وگرنه پیام فارسی
 * را برمی‌گرداند. قواعد به ترتیب اجرا می‌شوند و اولین پیام برنده است.
 */
export type FieldRule = (
  value: string,
  values: FormValues,
) => string | null | undefined;

export type FieldConfig = {
  /** برچسب فارسی میدان — در خلاصه‌ی خطاها نمایش داده می‌شود. */
  label?: string;
  initialValue?: string;
  /** قواعد مرتب؛ اولین قاعده‌ی ناکام پیام خطا را می‌دهد. */
  rules?: FieldRule[];
};

/** هر میدان یا تنظیمات کامل است یا فقط آرایه‌ی قواعد. */
export type FieldDefinition = FieldConfig | FieldRule[];

export type UseFormOptions = {
  fields: Record<string, FieldDefinition>;
  /** پیشوند id کنترل‌ها؛ پیش‌فرض از useId ساخته می‌شود (بدون «:»). */
  idPrefix?: string;
  /** اعتبارسنجی هر میدان پس از blur (پیش‌فرض: روشن). */
  validateOnBlur?: boolean;
  /** پس از موفقیت اعتبارسنجی و ارسال فرم صدا زده می‌شود. */
  onSubmit?: (values: FormValues) => void | Promise<void>;
};

/** نوع عنصرهای فرم‌ی که field() برایشان مناسب است. */
export type FormControlElement =
  | HTMLInputElement
  | HTMLTextAreaElement
  | HTMLSelectElement;

/** آنچه field(name) برمی‌گرداند — آماده‌ی پخش روی Input. */
export type FieldBinding = {
  id: string;
  name: string;
  value: string;
  onChange: React.ChangeEventHandler<FormControlElement>;
  onBlur: React.FocusEventHandler<FormControlElement>;
  /** پیام خطای فارسی، یا "" وقتی میدان سالم است. */
  error: string;
  "aria-invalid"?: true;
  "aria-describedby"?: string;
};

export type UseFormReturn = {
  values: FormValues;
  errors: FormErrorMap;
  touched: Record<string, boolean>;
  submitted: boolean;
  submitting: boolean;
  /** نام میدان‌های دارای خطا، به ترتیب تعریف میدان‌ها. */
  errorFields: string[];
  isValid: boolean;
  field: (name: string) => FieldBinding;
  fieldId: (name: string) => string;
  errorId: (name: string) => string;
  setValue: (name: string, value: string) => void;
  setError: (name: string, message: string) => void;
  clearErrors: () => void;
  validateField: (name: string) => string;
  validateAll: () => FormErrorMap;
  handleSubmit: (event?: React.FormEvent<HTMLFormElement>) => void;
  focusField: (name: string) => void;
  reset: (nextValues?: FormValues) => void;
};

/* ------------------------------------------------------------------ */
/* قواعد آماده                                                         */
/* ------------------------------------------------------------------ */

/** میدان لازم است (خالی نباشد). */
export function required(message: string): FieldRule {
  return (value) => (value.trim() ? null : message);
}

/** مقدار با الگو بخواند. */
export function matches(pattern: RegExp, message: string): FieldRule {
  return (value) => (pattern.test(value) ? null : message);
}

/** طول متن در بازه‌ی مجاز باشد. */
export function length(
  { min, max }: { min?: number; max?: number },
  message: string,
): FieldRule {
  return (value) => {
    const size = value.trim().length;
    if (min !== undefined && size < min) return message;
    if (max !== undefined && size > max) return message;
    return null;
  };
}

/** پیام خطا فقط وقتی میدان پر شده باشد (برای قاعده‌های اختیاری). */
export function onlyWhenFilled(rule: FieldRule): FieldRule {
  return (value, values) => (value.trim() ? rule(value, values) : null);
}

/* ------------------------------------------------------------------ */
/* قلاب                                                               */
/* ------------------------------------------------------------------ */

function normalizeRules(
  fields: Record<string, FieldDefinition>,
): Record<string, FieldRule[]> {
  const map: Record<string, FieldRule[]> = {};
  for (const [name, definition] of Object.entries(fields)) {
    map[name] = Array.isArray(definition) ? definition : definition.rules ?? [];
  }
  return map;
}

function initialValues(fields: Record<string, FieldDefinition>): FormValues {
  const values: FormValues = {};
  for (const [name, definition] of Object.entries(fields)) {
    values[name] = Array.isArray(definition)
      ? ""
      : definition.initialValue ?? "";
  }
  return values;
}

/** قواعد را به ترتیب اجرا می‌کند و پیام اولین قاعده‌ی ناکام را برمی‌گرداند. */
function runRules(
  rules: FieldRule[],
  value: string,
  values: FormValues,
): string {
  for (const rule of rules) {
    const message = rule(value, values);
    if (message) return message;
  }
  return "";
}

export function useForm({
  fields,
  idPrefix,
  validateOnBlur = true,
  onSubmit,
}: UseFormOptions): UseFormReturn {
  // id پایدار و امن برای انتخابگر CSS (useId کاراکتر «:» دارد).
  const reactId = React.useId().replace(/[:]/g, "");
  const prefix = idPrefix ?? `form-${reactId}`;

  const fieldId = React.useCallback((name: string) => `${prefix}-${name}`, [prefix]);
  const errorId = React.useCallback(
    (name: string) => `${prefix}-${name}-error`,
    [prefix],
  );

  const rules = React.useMemo(() => normalizeRules(fields), [fields]);
  const names = React.useMemo(() => Object.keys(fields), [fields]);

  const [values, setValues] = React.useState<FormValues>(() =>
    initialValues(fields),
  );
  const [errors, setErrors] = React.useState<FormErrorMap>({});
  const [touched, setTouched] = React.useState<Record<string, boolean>>({});
  const [submitted, setSubmitted] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);

  // مرجع‌ها تا فراخوانی‌های پایدار همیشه تازه‌ترین مقدار را ببینند.
  const rulesRef = React.useRef(rules);
  rulesRef.current = rules;
  const namesRef = React.useRef(names);
  namesRef.current = names;
  const valuesRef = React.useRef(values);
  const touchedRef = React.useRef(touched);
  const submittedRef = React.useRef(submitted);

  const writeError = React.useCallback((name: string, message: string) => {
    setErrors((previous) => {
      if ((previous[name] ?? "") === message) return previous;
      const next = { ...previous };
      if (message) next[name] = message;
      else delete next[name];
      return next;
    });
  }, []);

  /** یک میدان را بررسی می‌کند و نتیجه را در errors می‌نویسد. */
  const validateField = React.useCallback(
    (name: string, nextValues?: FormValues) => {
      const current = nextValues ?? valuesRef.current;
      const message = runRules(
        rulesRef.current[name] ?? [],
        current[name] ?? "",
        current,
      );
      writeError(name, message);
      return message;
    },
    [writeError],
  );

  const setValue = React.useCallback(
    (name: string, value: string) => {
      const next = { ...valuesRef.current, [name]: value };
      valuesRef.current = next;
      setValues(next);
      // پیش از اولین blur پیام نشان نده؛ بعد از آن خطا همان لحظه اصلاح شود.
      if (touchedRef.current[name] || submittedRef.current) {
        validateField(name, next);
      }
    },
    [validateField],
  );

  const setError = React.useCallback(
    (name: string, message: string) => {
      writeError(name, message);
    },
    [writeError],
  );

  const clearErrors = React.useCallback(() => setErrors({}), []);

  const handleChange = React.useCallback(
    (name: string): React.ChangeEventHandler<FormControlElement> =>
      (event) => setValue(name, event.target.value),
    [setValue],
  );

  const handleBlur = React.useCallback(
    (name: string): React.FocusEventHandler<FormControlElement> =>
      () => {
        const nextTouched = { ...touchedRef.current, [name]: true };
        touchedRef.current = nextTouched;
        setTouched(nextTouched);
        if (validateOnBlur) validateField(name);
      },
    [validateField, validateOnBlur],
  );

  const focusField = React.useCallback(
    (name: string) => {
      const element = document.getElementById(fieldId(name));
      if (element instanceof HTMLElement) element.focus();
    },
    [fieldId],
  );

  const validateAll = React.useCallback((): FormErrorMap => {
    const current = valuesRef.current;
    const next: FormErrorMap = {};
    for (const name of namesRef.current) {
      const message = runRules(rulesRef.current[name] ?? [], current[name] ?? "", current);
      if (message) next[name] = message;
    }
    setErrors(next);
    return next;
  }, []);

  const handleSubmit = React.useCallback(
    (event?: React.FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      submittedRef.current = true;
      setSubmitted(true);
      // همه‌ی میدان‌ها لمس‌شده می‌شوند تا پیام‌ها پایدار بمانند.
      const allTouched: Record<string, boolean> = {};
      for (const name of namesRef.current) allTouched[name] = true;
      touchedRef.current = allTouched;
      setTouched(allTouched);

      const allErrors = validateAll();
      const firstInvalid = namesRef.current.find((name) => allErrors[name]);
      if (firstInvalid) {
        focusField(firstInvalid);
        return;
      }

      const result = onSubmit?.(valuesRef.current);
      if (result && typeof (result as Promise<void>).then === "function") {
        setSubmitting(true);
        Promise.resolve(result).finally(() => setSubmitting(false));
      }
    },
    [focusField, onSubmit, validateAll],
  );

  const reset = React.useCallback(
    (nextValues?: FormValues) => {
      const next = nextValues ?? initialValues(fields);
      valuesRef.current = next;
      touchedRef.current = {};
      submittedRef.current = false;
      setValues(next);
      setErrors({});
      setTouched({});
      setSubmitted(false);
      setSubmitting(false);
    },
    [fields],
  );

  const field = React.useCallback(
    (name: string): FieldBinding => {
      const error = errors[name] ?? "";
      return {
        id: fieldId(name),
        name,
        value: values[name] ?? "",
        onChange: handleChange(name),
        onBlur: handleBlur(name),
        error,
        ...(error
          ? {
              "aria-invalid": true as const,
              "aria-describedby": errorId(name),
            }
          : {}),
      };
    },
    [errorId, errors, fieldId, handleBlur, handleChange, values],
  );

  const errorFields = React.useMemo(
    () => names.filter((name) => Boolean(errors[name])),
    [names, errors],
  );

  return {
    values,
    errors,
    touched,
    submitted,
    submitting,
    errorFields,
    isValid: errorFields.length === 0,
    field,
    fieldId,
    errorId,
    setValue,
    setError,
    clearErrors,
    validateField: (name: string) => validateField(name),
    validateAll,
    handleSubmit,
    focusField,
    reset,
  };
}

/**
 * برچسب فارسی میدان‌های دارای خطا (برای خلاصه‌ی خطاها).
 * خارج از قلاب نگه داشته شده تا FormErrors به آن دسترسی داشته باشد.
 */
function labelFor(fields: Record<string, FieldDefinition>, name: string): string {
  const definition = fields[name];
  if (definition && !Array.isArray(definition) && definition.label) {
    return definition.label;
  }
  return name;
}

/* ------------------------------------------------------------------ */
/* استایل مشترک کنترل‌ها                                               */
/* ------------------------------------------------------------------ */

/**
 * کنترل‌های فرم: متن دسکتاپ text-sm، ولی روی iOS دقیقاً ۱۶px تا سافاری
 * صفحه را روی فوکوس بزرگ‌نمایی نکند.
 */
const controlClasses = cn(
  "w-full rounded-xl border border-border bg-background font-sans text-foreground",
  "px-3.5 py-2.5 text-sm leading-6",
  "[@supports(-webkit-touch-callout:none)]:text-[16px]",
  "placeholder:text-muted-foreground",
  "transition-colors duration-200 motion-reduce:transition-none",
  "outline-none focus-visible:border-primary",
  "focus-visible:ring-2 focus-visible:ring-ring",
  "focus-visible:ring-offset-2 focus-visible:ring-offset-background",
  "disabled:cursor-not-allowed disabled:opacity-60",
  "aria-[invalid=true]:border-destructive",
  "aria-[invalid=true]:focus-visible:ring-destructive",
);

/* ------------------------------------------------------------------ */
/* کنترل‌های پایه                                                      */
/* ------------------------------------------------------------------ */

/**
 * error روی کنترل مصرف می‌شود و هرگز به DOM نمی‌رود؛ اگر پیام بدهید و
 * aria-invalid هم ست نکرده باشید، خودش آن را ست می‌کند.
 */
type InvalidControlledProps = {
  /** پیام خطای فارسی — فقط برای مصرف‌کننده، نه برای DOM. */
  error?: string;
};

export type InputProps = React.ComponentPropsWithoutRef<"input"> &
  InvalidControlledProps;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ className, error, ...rest }, ref) {
    return (
      <input
        ref={ref}
        {...rest}
        aria-invalid={error ? true : rest["aria-invalid"]}
        className={cn(controlClasses, className)}
      />
    );
  },
);

export type TextareaProps = React.ComponentPropsWithoutRef<"textarea"> &
  InvalidControlledProps;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ className, error, ...rest }, ref) {
    return (
      <textarea
        ref={ref}
        {...rest}
        aria-invalid={error ? true : rest["aria-invalid"]}
        className={cn(controlClasses, "min-h-24 resize-y", className)}
      />
    );
  },
);

export type SelectProps = React.ComponentPropsWithoutRef<"select"> &
  InvalidControlledProps;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ className, error, children, ...rest }, ref) {
    return (
      <div className="relative">
        <select
          ref={ref}
          {...rest}
          aria-invalid={error ? true : rest["aria-invalid"]}
          // «end» در RTL سمت چپ است، پس شورون با ویژگی منطقی می‌نشیند.
          className={cn(controlClasses, "appearance-none pe-9", className)}
        >
          {children}
        </select>
        <ChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute end-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        />
      </div>
    );
  },
);

/* ------------------------------------------------------------------ */
/* پوشش برچسب/راهنما/خطا                                               */
/* ------------------------------------------------------------------ */

export type FormFieldProps = {
  label: string;
  /** باید با id کنترل یکسان باشد (form.fieldId(name)). */
  htmlFor: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
};

export function FormField({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
  className,
}: FormFieldProps) {
  const hintId = `${htmlFor}-hint`;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label
        htmlFor={htmlFor}
        className="font-sans text-sm font-bold text-foreground"
      >
        {label}
        {required ? (
          <>
            <span aria-hidden="true" className="ms-1 text-destructive">
              *
            </span>
            <span className="sr-only">(الزامی)</span>
          </>
        ) : null}
      </label>
      {children}
      {hint && !error ? (
        <p id={hintId} className="text-xs leading-6 text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="text-xs font-bold leading-6 text-destructive">{error}</p>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* خلاصه‌ی خطاها                                                       */
/* ------------------------------------------------------------------ */

export type FormErrorsProps = {
  /** خروجی useForm. */
  form: UseFormReturn;
  /** برچسب‌های فارسی میدان‌ها (همان fields که به useForm داده‌اید). */
  fields?: Record<string, FieldDefinition>;
  title?: string;
  className?: string;
};

/**
 * خلاصه‌ی خطاها بالای فرم: هر خطا یک پیوند دارد که همان میدان را فوکوس
 * می‌کند. نقش alert آن را برای صفحه‌خوان اعلام می‌کند.
 */
export function FormErrors({
  form,
  fields = {},
  title = "لطفاً این موارد را اصلاح کنید",
  className,
}: FormErrorsProps) {
  const headingId = React.useId();
  const names = form.errorFields;
  if (names.length === 0) return null;

  return (
    <div
      role="alert"
      aria-labelledby={headingId}
      className={cn(
        "rounded-xl border border-destructive/40 bg-destructive/5 p-4",
        "font-sans text-sm text-foreground",
        className,
      )}
    >
      <p
        id={headingId}
        className="flex flex-wrap items-center gap-x-2 gap-y-1 font-bold text-destructive"
      >
        <AlertCircle aria-hidden="true" className="size-4 shrink-0" />
        {title}
        {/* شمارش با ارقام فارسی */}
        <span className="font-normal text-muted-foreground">
          ({toPersianDigits(names.length)} مورد)
        </span>
      </p>
      <ul className="mt-2 flex flex-col gap-1.5 ps-6">
        {names.map((name) => (
          <li key={name} className="list-disc marker:text-destructive">
            <a
              href={`#${form.fieldId(name)}`}
              onClick={(event) => {
                // پیوند باید کنترل را فوکوس کند، نه فقط صفحه را بپراند.
                event.preventDefault();
                form.focusField(name);
              }}
              className={cn(
                "rounded text-destructive underline",
                "underline-offset-4 decoration-destructive/40 hover:decoration-destructive",
                "outline-none focus-visible:ring-2 focus-visible:ring-ring",
                "focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              <span className="font-bold">
                {labelFor(fields, name)}
              </span>
              <span className="text-muted-foreground">
                {": "}
                {form.errors[name]}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* فرم                                                                 */
/* ------------------------------------------------------------------ */

export type FormProps = Omit<
  React.ComponentPropsWithoutRef<"form">,
  "form" | "onSubmit" | "noValidate"
> & {
  form: UseFormReturn;
  /** خلاصه‌ی خطاها بالای فرم؛ پیش‌فرض روشن. */
  showErrorSummary?: boolean;
  /** برچسب‌های فارسی میدان‌ها برای خلاصه‌ی خطاها. */
  fields?: Record<string, FieldDefinition>;
  summaryTitle?: string;
};

/**
 * پوسته‌ی فرم: dir="rtl"، اعتبارسنجی خودمان (noValidate) و خلاصه‌ی خطاها.
 */
export function Form({
  form,
  fields,
  showErrorSummary = true,
  summaryTitle,
  children,
  className,
  ...rest
}: FormProps) {
  return (
    <form
      dir="rtl"
      noValidate
      onSubmit={form.handleSubmit}
      className={cn("flex flex-col gap-5 font-sans text-foreground", className)}
      {...rest}
    >
      {showErrorSummary ? (
        <FormErrors form={form} fields={fields} title={summaryTitle} />
      ) : null}
      {children}
    </form>
  );
}

export default Form;
