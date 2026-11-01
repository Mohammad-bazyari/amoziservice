# اوستا سرویس — سایت تعمیر پکیج (جنگو + cPanel)

سایت فارسی RTL ثبت درخواست تعمیر پکیج، آماده استقرار روی هاست اشتراکی cPanel
(میزبان‌فا و مشابه). چون این هاست‌ها دسترسی SSH مستقیم نمی‌دهند، همه چیز برای
کار با **ترمینال cPanel** و **Setup Python App** تنظیم شده است.

## امکانات

- فرم چندمرحله‌ای ثبت درخواست (خدمت ← برند و مشکل ← تماس ← آدرس ← تصاویر ← بازبینی) با حفظ اطلاعات روی مرورگر کاربر
- پنل مدیریت فارسی با CMS کامل (خدمات، برندها، محتوای صفحه اصلی/درباره/تماس، سوالات متداول)
- مدیریت کاربران ادمین + بازیابی رمز عبور با پیامک
- اطلاع‌رسانی SMS با کاوه‌نگار (حالت شبیه‌سازی لوکال بدون ارسال واقعی)
- سئو: متا تگ‌ها، Schema.org، sitemap، robots، اسلاگ خودکار فارسی

## ساختار پروژه

```
├── manage.py
├── passenger_wsgi.py      ← نقطه ورود Passenger (cPanel)
├── config/                ← settings.py همه مقادیر حساس را از .env می‌خواند
├── apps/                  ← core, content, brands, services, requests,
│                             notifications, accounts
├── templates/  static/    ← قالب‌های RTL فارسی + فونت وزیرمتن (لوکال)
├── tools/tailwind/        ← کد منبع CSS (خروجی از پیش ساخته در static/)
├── .env.example           ← قالب متغیرهای محیطی
├── .htaccess.example      ← قالب .htaccess برای هاست
└── requirements.txt       ← شامل PyMySQL (سازگار با هاست اشتراکی)
```

## اجرای محلی

```bash
python -m venv .venv
# ویندوز:
.venv\Scripts\activate
# لینوکس/مک:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env        # ویندوز (لینوکس: cp)
python manage.py migrate
python manage.py seed_site    # داده اولیه سایت
python manage.py runserver
```

سپس `http://127.0.0.1:8000` را باز کنید. ادمین: `/admin/`
(کاربر ادمین اول را با `python manage.py seed_admin_accounts` یا
`createsuperuser` بسازید).

---

# استقرار روی cPanel (گام‌به‌گام)

## گام ۰ — پیش‌نیازها

- دامنه متصل به هاست و **SSL فعال** (cPanel → SSL/TLS Status → Run AutoSSL)
- نسخه پایتون ۳.۱۱ یا بالاتر در cPanel موجود باشد
- حدود ۳۰۰ مگابایت فضا (venv + staticfiles + مدیا)

## گام ۱ — ساخت دیتابیس MySQL

1. cPanel → **MySQL® Databases**
2. در «Create New Database» یک نام بسازید، مثلاً `ostadb`
   (نام کامل می‌شود `cpaneluser_ostadb`)
3. در «MySQL Users → Add New User» یک کاربر بسازید، مثلاً `ostauser`
   و رمز قوی بگذارید (نام کامل: `cpaneluser_ostauser`)
4. در «Add User To Database» کاربر را به دیتابیس اضافه کنید و تیک
   **ALL PRIVILEGES** را بزنید
5. این سه مقدار را نگه دارید؛ در گام ۴ لازم می‌شود.

## گام ۲ — ساخت اپ پایتون

cPanel → **Setup Python App**:

| فیلد | مقدار |
|---|---|
| Python version | 3.11 یا بالاتر |
| Application root | `ostaapp` (یا هر پوشه‌ای؛ همین فایل‌ها را آنجا آپلود می‌کنید) |
| Application URL | دامنه یا زیردامنه مورد نظر |
| Application startup file | `passenger_wsgi.py` |
| Application entry point | خالی بگذارید |

روی **Create** بزنید. دستور فعال‌سازی virtualenv که در صفحه بعد نشان می‌دهد را
**کپی کنید** (در گام ۳ لازم است) — چیزی شبیه:

```
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
```

## گام ۳ — آپلود کد

روی کامپیوتر خودتان از پوشه پروژه یک zip بسازید که این‌ها را **نداشته باشد**:

```
.venv/  .git/  db.sqlite3  media/  staticfiles/  logs/  .env  __pycache__/
```

سپس:

1. cPanel → **File Manager** → وارد پوشه Application root شوید
2. zip را آپلود و با راست‌کلیک → **Extract** باز کنید

## گام ۴ — ترمینال: نصب و تنظیمات

cPanel → **Terminal** (در میزبان‌فا همان ترمینال جای SSH است):

```bash
# ۱) فعال‌سازی virtualenv (دستور کپی‌شده از گام ۲)
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
cd /home/USERNAME/ostaapp

# ۲) نصب وابستگی‌ها (PyMySQL بدون کامپایل روی هاست اشتراکی کار می‌کند)
pip install -r requirements.txt

# ۳) ساخت فایل تنظیمات و پرکردن مقادیر واقعی
cp .env.example .env
nano .env
```

در `.env` این‌ها را واقعی کنید:

```ini
DJANGO_SECRET_KEY=<یک رشته تصادفی بلند — دستور تولید داخل فایل هست>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=mysql://cpaneluser_ostauser:DB-PASSWORD@localhost:3306/cpaneluser_ostadb
KAVENEGAR_ENABLED=False
```

نکته: به‌جای ویرایش فایل، می‌توانید همین متغیرها را در خود
**Setup Python App → Environment variables** هم وارد کنید (امن‌تر است؛ آنگاه
خط `DATABASE_URL` را از `.env` حذف کنید تا آن‌جا ملاک باشد).

ذخیره در nano: `Ctrl+O` بعد `Enter`، خروج: `Ctrl+X`.

## گام ۵ — مایگریشن، داده اولیه، استاتیک، ادمین

همچنان در ترمینال با virtualenv فعال:

```bash
python manage.py migrate
python manage.py seed_site            # محتوای اولیه سایت (خدمت/برند/CMS)
python manage.py collectstatic --noinput
python manage.py seed_admin_accounts  # یا: python manage.py createsuperuser
```

`seed_admin_accounts` اکانت `mbazyari` را با رمز `mbazyari` می‌سازد —
**بعد از اولین ورود رمز را عوض کنید** (بخش تغییر رمز در پنل).

## گام ۶ — .htaccess

در File Manager وارد **Document Root دامنه** شوید (همان پوشه‌ای که Application
URL به آن اشاره می‌کند)، فایل `.htaccess.example` را با **Rename** به
`.htaccess` تغییر نام دهید.

این فایل: سرو مستقیم و سریع `media/` و `staticfiles/` توسط لایت‌اسپید،
بستن دسترسی به `.env` و فایل‌های حساس، کش و فشرده‌سازی.

> اگر WhiteNoise را دست نزنید حتی بدون این فایل هم استاتیک‌ها از خود جنگو سرو
> می‌شوند؛ `.htaccess` فقط سرعت و امنیت را بهتر می‌کند.

## گام ۷ — ری‌استارت و تست دود

در Setup Python App روی **Restart** بزنید (یا در ترمینال:
`mkdir -p tmp && touch tmp/restart.txt`)، بعد این‌ها را در مرورگر چک کنید:

| آدرس | انتظار |
|---|---|
| `https://yourdomain.com/` | صفحه اصلی با لوگو و شماره تماس |
| `https://yourdomain.com/request/` | مرحله ۱ فرم (انتخاب خدمت) |
| `https://yourdomain.com/admin/` | ورود پنل مدیریت |
| `https://yourdomain.com/sitemap.xml` | نقشه سایت |

یک درخواست آزمایشی کامل ثبت کنید و در پنل ببینیدش.

## گام ۸ — فعال‌سازی پیامک واقعی (کاوه‌نگار)

1. در kavenegar.com ثبت‌نام کنید و از پنل کاربری یک **API Key** بگیرید
2. خط فرستنده (Sender) را از پشتیبانی کاوه‌نگار فعال کنید
3. در `.env` (یا Environment variables پنل):

```ini
KAVENEGAR_ENABLED=True
KAVENEGAR_API_KEY=xxxx
KAVENEGAR_SENDER=10008663
```

4. `touch tmp/restart.txt` بزنید. با ثبت یک درخواست آزمایشی، ارسال را در
   **پنل → گزارش پیامک (SmsLog)** چک کنید — وضعیت باید `sent` شود.

تا وقتی `KAVENEGAR_ENABLED=False` است هیچ پیامکی و پولی ارسال نمی‌شود؛
پیام‌ها فقط در جدول گزارش ذخیره می‌شوند.

## به‌روزرسانی سایت (آپدیت‌های بعدی)

```bash
cd /home/USERNAME/ostaapp
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
# کد جدید را آپلود/extract کنید (فایل‌های .env و media/ و db را جایگزین نکنید!)
pip install -r requirements.txt     # اگر requirements عوض شده
python manage.py migrate            # اگر migration جدید دارید
python manage.py collectstatic --noinput   # اگر فایل استاتیک عوض شده
touch tmp/restart.txt
```

**یادآوری مهم:** اگر فایل استاتیک جدیدی (عکس/فونت/JS) اضافه کردید و
`collectstatic` را نزدید، صفحات ممکن است ۵۰۰ شوند — چون پروژه مانیفست
استاتیک را بررسی می‌کند.

## بکاپ

- **دیتابیس:** cPanel → phpMyAdmin → Export (هفته‌ای یک بار کافی است)
- **مدیا (عکس‌های درخواست‌ها):** File Manager → zip پوشه `media/`
- هر دو را روی کامپیوتر خودتان نگه دارید؛ بکاپ خودکار هاست هم معمولاً فعال است.

## عیب‌یابی سریع

| مشکل | چک کنید |
|---|---|
| صفحه ۵۰۰ | «Errors» در Setup Python App + فایل `logs/django.log` |
| استاتیک‌ها ۴۰۴/۵۰۰ | `python manage.py collectstatic --noinput` زده‌اید؟ |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` شامل دامنه واقعی است؟ |
| خطای CSRF در ورود ادمین | `DJANGO_CSRF_TRUSTED_ORIGINS` با `https://` دامنه را دارد؟ |
| اتصال دیتابیس | نام کاربر/دیتابیس حتماً با پیشوند cpaneluser کامل باشد |
| تغییرات کد اعمال نمی‌شود | `touch tmp/restart.txt` را فراموش نکنید |

## تست‌ها

```bash
python manage.py test
```
