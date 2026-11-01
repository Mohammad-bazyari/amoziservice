# راهنمای گام‌به‌گام ثبت سایت در Google Search Console و Bing Webmaster Tools

> **کِی این سند به کار می‌آید؟** بلافاصله بعد از اولین دیپلوی موفق روی cPanel (طبق `DEPLOY.md`) — یعنی وقتی `https://yourdomain.com/` با SSL سبز باز می‌شود.
>
> **چرا مهم است؟** این دو ابزار تنها راه رسمی «معرفی سایت به گوگل و بینگ» هستند. تا وقتی ثبت نکنید، گوگل ممکن است هفته‌ها صبر کند؛ و صفحات شما برای **Copilot** (که از ایندکس بینگ استفاده می‌کند) اصلاً دیده نمی‌شوند.

---

## ۰) پیش‌نیازها (۵ دقیقه)

قبل از شروع، مطمئن شوید:

- [ ] سایت روی دامنه اصلی باز می‌شود: `https://yourdomain.com/`
- [ ] SSL فعال است (قفل کنار آدرس) — GSC نسخه https را می‌خواهد
- [ ] `https://yourdomain.com/sitemap.xml` در مرورگر باز می‌شود و فهرست URLها را می‌بینید (حداقل ۲۵ آدرس: صفحه اصلی، خدمات، برندها، مقالات)
- [ ] `https://yourdomain.com/robots.txt` باز می‌شود و خط `Sitemap: https://yourdomain.com/sitemap.xml` را دارد
- [ ] به سی‌پنل دسترسی File Manager دارید

> اگر sitemap یا robots خطا داد، اول مشکل را در `DEPLOY.md` (بخش عیب‌یابی) حل کنید — sitemap خراب یعنی ثبت هم بی‌فایده است.

---

## ۱) Google Search Console — تأیید مالکیت

### گزینه A — فایل HTML (توصیه‌شده، ساده‌ترین)

1. بروید به **[search.google.com/search-console](https://search.google.com/search-console)** و با اکانت گوگل کسب‌وکار وارد شوید.
2. روی «Add property» کلیک کنید. دو نوع پراپرتی هست:
   - **Domain** (`yourdomain.com` — شامل همه ساب‌دامنه‌ها؛ فقط با DNS قابل تأیید) — قوی‌تر
   - **URL prefix** (`https://yourdomain.com/`) — با فایل HTML هم قابل تأیید ← **اگر دسترسی DNS ندارید این را انتخاب کنید**
3. گزینه **HTML file** را انتخاب کنید؛ گوگل یک فایل مثل `google1234567890abcdef.html` می‌دهد.
4. cPanel → **File Manager** → پوشه `public_html` → آپلود فایل.
5. تست: `https://yourdomain.com/google1234567890abcdef.html` باید محتوای فایل را نشان دهد.
6. برگردید به GSC و «Verify» را بزنید. ✅

> **اگر 404 گرفتید:** درخواست فایل گوگل باید **قبل از جنگو** پاس شود (جنگو مسیر ناشناخته را به صفحه 404 خودش می‌فرستد). فایل را دقیقاً در `public_html` بگذارید — زیر پوشه اپ جنگو نباشد. اگر باز 404 شد، در `.htaccess` همین بالای رول‌های موجود اضافه کنید:
> ```apache
> RewriteCond %{REQUEST_URI} !^/google
> ```

### گزینه B — تگ متا (اگر File Manager راحت‌تر نیست)

1. در GSC گزینه **HTML tag** را انتخاب کنید؛ متایی شبیه این می‌دهند:
   ```html
   <meta name="google-site-verification" content="abc123...">
   ```
2. در پروژه، فایل `templates/base.html` را باز کنید و این خط را داخل `<head>` (بعد از تگ‌های og) اضافه کنید:
   ```html
   <meta name="google-site-verification" content="abc123...">
   ```
3. طبق `DEPLOY.md` آپدیت و deploy کنید (روش ZIP یا Git)، بعد «Verify» را بزنید.

> مزیت روش A: نیازی به deploy نیست. مزیت روش B: با تغییر هاست هم پابرجاست چون داخل کد است.

### گزینه C — DNS TXT (پراپرتی Domain — کامل‌ترین پوشش)

اگر پنل دامنه (ایران‌سرور/میزبان‌فا/...) را دارید:

1. در GSC پراپرتی **Domain** بسازید؛ گوگل یک مقدار مثل `google-site-verification=abc123...` می‌دهد.
2. پنل دامنه → مدیریت DNS → Add Record:
   - Type: **TXT**
   - Host/Name: `@`
   - Value: مقدار گوگل
   - TTL: 3600
3. ۱۵ دقیقه تا چند ساعت صبر کنید و «Verify» را بزنید.

> پراپرتی Domain همه ساب‌دامنه‌ها و هر دو پروتکل http/https را یک‌جا پوشش می‌دهد؛ اگر دسترسی DNS دارید، همین بهترین انتخاب است.

---

## ۲) ارسال sitemap در GSC

1. منوی چپ → **Sitemaps**.
2. در فیلد، فقط `sitemap.xml` را وارد کنید (پیشوند دامنه خودکار پر می‌شود).
3. Submit → وضعیت باید «Success» باشد.
4. «Pages could not be read: 0» یا «0 discovered» در ابتدا طبیعی است — پردازش ۱ تا ۷ روز طول می‌کشد.

### گزارش‌های GSC که باید بشناسید

| گزارش | کجا | چه نگاه کنید |
|---|---|---|
| Performance | منوی چپ | کوئری‌هایی که در آن‌ها نمایش گرفته‌اید = فهرست واقعی کلیدواژه‌ها؛ ورودی تقویم محتوای بعدی |
| Pages (Indexing) | منوی چپ | «Crawled - currently not indexed» → محتوا باریک است؛ «Discovered - currently not indexed» → لینک داخلی کم است |
| Core Web Vitals | Experience | LCP زیر ۲.۵ ثانیه؛ فونت Vazirmatn از قبل preload شده و کمک می‌کند |
| Enhancements | منوی چپ | اسکیماهای سایت (FAQPage، Article، LocalBusiness، BreadcrumbList) باید بدون خطا بیایند |
| Manual Actions / Security | پایین منو | «No issues» یعنی جریمه‌ای ندارید |

> **چرخه محتوا با GSC:** بعد از هر مقاله جدید → GSC → **URL Inspection** → آدرس را بچسبانید → **Request Indexing**. این کار ایندکس را از هفته‌ها به روزها می‌رساند.

---

## ۳) Bing Webmaster Tools — تأیید و ثبت

**چرا بینگ؟** Copilot از ایندکس بینگ نقل‌قول می‌کند و Perplexity هم بخشی از نتایجش از بینگ است. برای GEO، بینگ دست‌کم به‌اندازه گوگل مهم است.

### تأیید مالکیت — سه مسیر

1. **Import از GSC (سریع‌ترین راه):** بروید به [bing.com/webmasters](https://www.bing.com/webmasters) → «Get started» → **Import from Google Search Console** → با همان اکانت گوگل وارد شوید و اجازه بدهید. پراپرتی و sitemap خودکار منتقل می‌شود. ✅
2. **XML file:** بینگ فایل `BingSiteAuth.xml` می‌دهد → آپلود در `public_html` (مثل روش A گوگل).
3. **CNAME:** در DNS دامنه رکورد CNAME با مقداری که بینگ می‌دهد بسازید.

### ارسال sitemap در بینگ

- اگر Import نکرده‌اید: بینگ → **Sitemaps** → Submit feed → `https://yourdomain.com/sitemap.xml`

### ایندکس فوری (IndexNow)

بعد از انتشار هر مقاله جدید، یک GET ساده:

```
https://api.indexnow.org/indexnow?url=https://yourdomain.com/articles/NEW-SLUG/&key=KEY
```

- `KEY` را در پنل بینگ (Settings → API key) می‌گیرید؛
- فایل `KEY.txt` با همان محتوا در `public_html` بگذارید (تأیید مالکیت برای IndexNow)؛
- سایت در `robots.txt` به Bingbot اجازه داده، پس مانع فنی وجود ندارد.

---

## ۴) مانیتورینگ — ۱۰ دقیقه در هفته

روتین هفتگی پیشنهادی:

1. **GSC → Performance:** کلیک/نمایش هفته را یادداشت کنید (روند مهم‌تر از عدد مطلق است).
2. **GSC → Pages:** خطای ایندکس جدید؟ کاننیکال‌های سایت روی همه صفحات هست؛ «Duplicate without user-selected canonical» نباید ببینید.
3. **GSC → Enhancements:** خطای جدید در schemaها؟ (مخصوصاً بعد از ویرایش FAQ یا مقاله در پنل)
4. **بینگ → Search Performance:** مقایسه با گوگل؛ اگر عقب‌تر است، سابمیت دستی مقاله جدید را جا نیندازید.
5. **مقاله جدید → GSC Request Indexing + بینگ IndexNow** — هر دو، هر بار.

> **نکته GEO:** پلتفرم‌های AI محتوای تازه را ترجیح می‌دهند (به‌روزرسانی در ۳۰ روز اخیر ≈ ۳.۲ برابر citation بیشتر در ChatGPT). روتین «انتشار → سابمیت → مانیتور» همین را تضمین می‌کند.

---

## عیب‌یابی رایج

| مشکل | علت و راه‌حل |
|---|---|
| تأیید گوگل fail می‌شود | فایل در مسیر اشتباه است یا کش Passenger — `touch tmp/restart.txt` و ۵ دقیقه صبر |
| sitemap خطا «Couldn't fetch» | دامنه در خط Sitemap robots.txt با آدرس فعلی فرق دارد؛ robots سایت دامنه را از request می‌سازد — با `https://` سایت را باز کنید و دوباره سابمیت کنید |
| «Crawled - currently not indexed» | محتوای صفحه باریک است؛ طبق الگوی GEO (پاسخ کوتاه اول + آمار + FAQ) تقویت و دوباره سابمیت کنید |
| Enhancements خطای FAQPage | FAQ با پاسخ خالی در پنل؟ پاسخ‌ها را در ادمین پر کنید |
| Enhancements خطای Article | مقاله بدون محتوا/تاریخ؟ فیلدها را در ادمین کامل کنید |
| بینگ ایندکس نمی‌کند | اول sitemap دستی، بعد URL Inspection هر صفحه مهم |
| «Page with redirect» | نسخه http به https ریدایرکت می‌شود — طبیعی است؛ فقط نسخه https را سابمیت کنید |

---

## چک‌لیست خروج از راهنما

- [ ] پراپرتی GSC تأیید شد (فایل HTML / تگ متا / DNS — یکی کافی است)
- [ ] `sitemap.xml` سابمیت شد و «Success» است
- [ ] پراپرتی بینگ ساخته شد (ترجیحاً Import از GSC) و sitemap آن هم تایید است
- [ ] فایل کلید IndexNow در `public_html` هست
- [ ] URL Inspection برای صفحه اصلی و ۲-۳ صفحه کلیدی انجام شد
- [ ] یادآوری هفتگی (تقویم/موبایل) برای روتین ۱۰ دقیقه‌ای تنظیم شد

معمولاً ۲ تا ۷ روز بعد اولین صفحات ایندکس می‌شوند. مقالات فصلی (مثل سرویس پیش از زمستان) را نزدیک فصل منتشر و فوراً سابمیت کنید تا بیشترین برد را از تقاضای فصلی ببرید.
