# راهنمای کامل دیپلوی «آموزی سرویس» روی cPanel

این سند سه روش استقرار روی هاست اشتراکی cPanel (میزبان‌فا، ایران‌سرور، پارس‌پک و مشابه) را قدم‌به‌قدم توضیح می‌دهد:

| روش | مناسب برای | سرعت آپدیت‌های بعدی | نیاز به SSH/ترمینال |
|---|---|---|---|
| **الف) آپلود ZIP** | اولین دیپلوی، بدون دانش Git | متوسط (هر بار zip جدید) | فقط ترمینال cPanel |
| **ب) Git (گیت‌هاب + cPanel Git Version Control)** | کار جدی با آپدیت‌های مکرر | عالی (یک push، یک pull) | ترمینال cPanel |
| **ج) FTP / File Manager** | اصلاح فوری چند فایل، بدون هیچ ابزاری | ضعیف (فایل‌به‌فایل) | ندارند |

هر سه روش به همان زیرساخت مشترک وصل می‌شوند (دیتابیس MySQL + Setup Python App + Passenger)، پس **اول بخش «زیرساخت مشترک» را یک بار انجام دهید، سپس یکی از سه روش را انتخاب کنید.**

---

## ۰) زیرساخت مشترک (برای هر سه روش، یک بار)

### ۰.۱ — پیش‌نیازها

- دامنه متصل به هاست و **SSL فعال**: cPanel → SSL/TLS Status → Run AutoSSL
- پایتون ۳.۱۱+ در بخش Setup Python App هاست موجود باشد
- حدود ۳۰۰ مگابایت فضا (venv + staticfiles + مدیا)

### ۰.۲ — ساخت دیتابیس MySQL

1. cPanel → **MySQL® Databases**
2. در «Create New Database» یک نام بسازید، مثلاً `ostadb` — نام کامل می‌شود `cpaneluser_ostadb`
3. در «MySQL Users → Add New User» کاربر بسازید، مثلاً `ostauser` با رمز قوی — نام کامل: `cpaneluser_ostauser`
4. «Add User To Database» → تیک **ALL PRIVILEGES**
5. سه مقدار (نام کامل دیتابیس، نام کامل کاربر، رمز) را نگه دارید.

### ۰.۳ — ساخت اپ پایتون

cPanel → **Setup Python App** → Create Application:

| فیلد | مقدار |
|---|---|
| Python version | 3.11 یا بالاتر |
| Application root | `ostaapp` (یا هر پوشه‌ای — کد همین‌جا ریخته می‌شود) |
| Application URL | دامنه یا زیردامنه مورد نظر |
| Application startup file | `passenger_wsgi.py` |
| Application entry point | خالی |

بعد از Create، دستور فعال‌سازی virtualenv را **کپی کنید** (همه‌جا لازم است):

```
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
```

### ۰.۴ — محتوای آپلودی باید شامل چه باشد؟

**بله آپلود کنید:** `manage.py` ، `passenger_wsgi.py` ، `config/` ، `apps/` ، `templates/` ، `static/` ، `tools/` ، `requirements.txt` ، `.env.example` ، `.htaccess.example` ، `.gitignore`

**هرگز آپلود نکنید:** `.venv/` ، `.git/` ، `db.sqlite3` ، `media/` ، `staticfiles/` ، `logs/` ، `.env` (روی هاست از نو ساخته می‌شود با مقادیر واقعی)، `__pycache__/`

> نکته: `tools/tailwind/` فقط کد منبع CSS است؛ خروجی آماده در `static/css/app.css` هست. اگر می‌خواهید حجم آپلود کمتر شود می‌توانید `tools/` را کنار بگذارید — ولی آن‌وقت برای هر تغییر ظاهری باید لوکال rebuild بزنید. پیشنهاد: آپلودش نگه دارید.

### ۰.۵ — نصب و تنظیمات در ترمینال (بعد از آپلود کد با هر روشی)

cPanel → **Terminal**:

```bash
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
cd /home/USERNAME/ostaapp

pip install -r requirements.txt          # PyMySQL بدون کامپایل نصب می‌شود

cp .env.example .env
nano .env
```

در `.env` این مقادیر را واقعی کنید:

```ini
DJANGO_SECRET_KEY=<رشته تصادفی بلند — دستور تولید داخل فایل هست>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=amoziservice.com,www.amoziservice.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://amoziservice.com,https://www.amoziservice.com
DATABASE_URL=mysql://cpaneluser_ostauser:DB-PASSWORD@localhost:3306/cpaneluser_ostadb
DJANGO_SECURE_SSL_REDIRECT=True
KAVENEGAR_ENABLED=False
```

> جایگزین امن‌تر: همین متغیرها را در **Setup Python App → Environment variables** وارد کنید و `DATABASE_URL` را از `.env` حذف کنید.

سپس راه‌اندازی اولیه و بارگذاری اطلاعات:

**روش اول (پیشنهادی برای دیپلوی تمیز با دیتای واقعی قبلی):**
```bash
python manage.py migrate
python manage.py loaddata fixtures/production_data.json  # بارگذاری ۲۰ مقاله، برندها، تنظیمات و درخواست‌ها
python manage.py collectstatic --noinput                 # بدون این، صفحات ممکن است ۵۰۰ شوند!
```
*(یا می‌توانید قبل از دستورات بالا، فایل `fixtures/production_clean_mysql.sql` را مستقیم از phpMyAdmin ایمپورت کرده و سپس فقط `migrate` و `collectstatic` را اجرا کنید).*

**روش دوم (فقط برای راه‌اندازی تستی و خام بدون اطلاعات قبلی):**
```bash
python manage.py migrate
python manage.py seed_site               # محتوای اولیه خام (خدمات/برندها/CMS)
python manage.py collectstatic --noinput # بدون این، صفحات ممکن است ۵۰۰ شوند!
python manage.py seed_admin_accounts     # یا createsuperuser
```

`seed_admin_accounts` اکانت `mbazyari` با رمز `mbazyari` می‌سازد — **بعد از اولین ورود حتماً رمز را عوض کنید.**

برای بازیابی رمز ادمین با پیامک، شماره موبایل اکانت باید در پنل (کاربران ← اکانت ادمین ← فیلد موبایل) ثبت باشد؛ صفحه `/admin/pw-recover/` جدا از فرم ورود است.

### ۰.۶ — کارهای زمان‌بندی‌شده (Cron Jobs)

cPanel → **Cron Jobs** → برای هر خط یک رکورد:

```cron
# پاکسازی تصاویر موقتِ درخواست‌های نیمه‌کاره — روزی یک بار
0 3 * * * cd /home/USERNAME/ostaapp && source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate && python manage.py cleanup_request_tmp
```

(در حال حاضر فقط همین یک دستور زمان‌بندی لازم است؛ مولد یادآور سرویس دوره‌ای فعلاً در برنامه قرار نگرفته — اگر فعال شد خط دوم اضافه کنید.)

### ۰.۷ — .htaccess

File Manager → پوشه **Document Root دامنه** (جایی که Application URL به آن اشاره می‌کند) → `.htaccess.example` را Rename کنید به `.htaccess`.

کار آن: سرو مستقیم و سریع `staticfiles/` و `media/` توسط لایت‌اسپید، بستن دسترسی به `.env` و فایل‌های حساس، کش و فشرده‌سازی.

### ۰.۸ — تست دود (بعد از هر استقرار)

Setup Python App → **Restart** (یا ترمینال: `mkdir -p tmp && touch tmp/restart.txt`)، سپس:

| آدرس | انتظار |
|---|---|
| `https://yourdomain.com/` | صفحه اصلی با لوگو و شماره تماس، بخش مزایا/مراحل پر |
| `https://yourdomain.com/request/` | مرحله ۱ فرم (انتخاب خدمت) |
| `https://yourdomain.com/articles/` | فهرست مقالات |
| `https://yourdomain.com/admin/` | ورود پنل مدیریت (صفحه بازیابی رمز جدا: `/admin/pw-recover/`) |
| `https://yourdomain.com/sitemap.xml` | نقشه سایت |
| `https://yourdomain.com/robots.txt` | ۱۶ بلوک User-agent شامل بات‌های AI (GPTBot، PerplexityBot، ClaudeBot و...) |

بررسی سئو/GEO (اشاره به Rich Results Test گوگل کافی است):

- [ ] صفحه اصلی: اسکیمای LocalBusiness + FAQPage در سورس صفحه (جستجوی `application/ld+json`)
- [ ] صفحه خدمت/برند: Service + ItemList + BreadcrumbList
- [ ] مقاله‌ها: Article کامل (author/publisher/logo) + BreadcrumbList
- [ ] در سورس همه صفحات: تگ‌های twitter:card و og:image (fallback لوگو)

یک درخواست آزمایشی کامل ثبت کنید و در پنل ببینیدش. سپس:

- [ ] در پنل، «گزارش پیامک» دو ردیف دارد: تعمیرکار + تأیید مشتری (اگر پیامک خاموش است، وضعیت mock)
- [ ] فرم ادمین «محتوای صفحه اصلی»: جدول مزایا/مراحل با ردیف‌های آماده دیده می‌شود
- [ ] فرم ادمین «خدمت»: انتخاب‌گر آیکون گرافیکی کار می‌کند
- [ ] در موبایل، منوی ادمین با دکمه ☰ (راست هدر) باز می‌شود؛ دکمه تم 🌙/☀️ کنار آن است
- [ ] میانبرهای Ctrl+S / Ctrl+E / Ctrl+Shift+S در فرم‌های پنل کار می‌کنند
- [ ] نوار ذخیره فقط دکمه‌های لازم را دارد (فرم خدمت فقط «ذخیره»)

بعد از تست دود، قدم بعدی معرفی سایت به موتورهای جستجو است:
**[docs/SEARCH-CONSOLE-GUIDE.md](docs/SEARCH-CONSOLE-GUIDE.md)** — ثبت در Google Search Console و Bing Webmaster (تأیید مالکیت، ارسال sitemap، IndexNow، مانیتورینگ هفتگی).

---

## روش الف — آپلود ZIP (ساده‌ترین مسیر اول)

### اولین دیپلوی

1. روی کامپیوتر خودتان از پوشه پروژه یک zip بسازید که فقط شامل موارد بخش ۰.۴ باشد (بدون `.venv`، `.git`، `db.sqlite3`، `media/`، `staticfiles/`، `logs/`، `.env`، `__pycache__/`).

   ویندوز: پوشه را باز کنید، این موارد را Ctrl+Click انتخاب و Exclude کنید، بعد راست‌کلیک → Send to → Compressed folder.
   یا با پاورشل:

   ```powershell
   Compress-Archive -Path manage.py,passenger_wsgi.py,config,apps,templates,static,tools,requirements.txt,.env.example,.htaccess.example,.gitignore -DestinationPath osta-deploy.zip
   ```

2. cPanel → **File Manager** → وارد پوشه Application root شوید (`/home/USERNAME/ostaapp`)
3. zip را آپلود → راست‌کلیک → **Extract** → zip را پاک کنید
4. ادامه از بخش ۰.۵ (نصب و تنظیمات) و ۰.۷ و ۰.۸

### آپدیت‌های بعدی با ZIP

1. zip جدید بسازید (**بدون** `.env` ، `media/` ، `db.sqlite3` — این‌ها روی هاست زندگی می‌کنند)
2. آپلود و Extract در همان پوشه — File Manager برای فایل هم‌نام **Replace** می‌پرسد؛ تأیید کنید
3. ترمینال:

```bash
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
cd ~/ostaapp
pip install -r requirements.txt            # فقط اگر requirements عوض شده
python manage.py migrate                   # ← این بار الزامی: مایگریشن ۰۰۰۷ (تبدیل JSON مزایا/مراحل به ردیف) + مایگریشن ۰۰۰۳ اکانتس (فیلدهای سوال امنیتی بازیابی)
python manage.py collectstatic --noinput   # الزامی: CSS/JS جدید (آیکون‌پیکر، میانبرها، تم ادمین)
touch tmp/restart.txt
```

> مایگریشن ۰۰۰۷ داده JSON «مزایا/مراحل» را به ردیف تبدیل می‌کند — محتوای ویرایش‌شده ادمین **از دست نمی‌رود**. ولی قبل از آپدیت، از دیتابیس بکاپ بگیرید (phpMyAdmin → Export). بعد از آپدیت، صفحه اصلی و فرم ادمین «محتوای صفحه اصلی» را چک کنید.

**ریسک این روش:** Extract بازنویسی کورکورانه است — اگر اشتباهی `.env` یا پوشه `media/` را در zip داشته باشید، روی داده واقعی می‌ریزد. قبل از هر zip، فهرست ۰.۴ را چک کنید.

---

## روش ب — Git (پیشنهادی برای آپدیت‌های مکرر)

### معماری

```
[لپ‌تاپ شما] --git push--> [گیت‌هاب (ریپوی خصوصی)] --git pull--> [هاست cPanel]
```

پوش‌ مستقیم به هاست (self-hosted bare repo + hook) هم ممکن است اما روی هاست‌های اشتراکی ایرانی دسترسی SSH خارجی معمولاً بسته است؛ مسیر پایدار، **pull از ترمینال cPanel** است.

### ب.۱ — ریپوی گیت‌هاب بسازید و کد را push کنید

روی کامپیوتر خودتان (داخل پوشه پروژه):

```bash
git init
git add .
git commit -m "Initial deploy"
# در گیت‌هاب یک ریپوی **خصوصی** بسازید (مثلاً osta-service) و:
git remote add origin https://github.com/YOUR-USER/osta-service.git
git branch -M main
git push -u origin main
```

`.gitignore` پروژه از قبل درست است: `.env` ، `db.sqlite3` ، `media/` ، `staticfiles/` ، `.venv/` و لاگ‌ها را وارد ریپو **نمی‌کند** — چیزی حساس بالا نمی‌رود.

### ب.۲ — هاست را به ریپو وصل کنید

اگر ریپو **خصوصی** است (پیشنهادی)، یک توکن بسازید: گیت‌هاب → Settings → Developer settings → Personal access tokens (classic) → Generate → تیک `repo` → توکن را کپی کنید.

در cPanel → **Git™ Version Control** → Create:

| فیلد | مقدار |
|---|---|
| Clone URL | `https://YOUR-TOKEN@github.com/YOUR-USER/osta-service.git` |
| Repository path | `/home/USERNAME/ostaapp` (همان Application root) |
| Repository name | osta-service |

Create را بزنید — cPanel خودش clone می‌کند و کد در پوشه می‌نشیند.
(برای ریپوی عمومی، توکن لازم نیست؛ فقط URL را بدهید.)

### ب.۳ — ادامه مثل روش مشترک

از بخش ۰.۵ (نصب و تنظیمات) ادامه دهید — یک بار برای همیشه.

### ب.۴ — گردش کار آپدیت (این است که این روش را می‌ارزد)

هر تغییر، دو طرف:

```bash
# روی کامپیوتر شما:
git add .
git commit -m "توضیح تغییر"
git push

# در ترمینال cPanel:
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
cd ~/ostaapp
git pull
pip install -r requirements.txt            # فقط اگر requirements عوض شده
python manage.py migrate                   # ← این بار الزامی: مایگریشن ۰۰۰۷ (تبدیل JSON مزایا/مراحل) + مایگریشن ۰۰۰۳ اکانتس (فیلدهای سوال امنیتی بازیابی)
python manage.py collectstatic --noinput   # الزامی: CSS/JS جدید (آیکون‌پیکر، میانبرها، تم ادمین)
touch tmp/restart.txt
```

> قبل از pullِ این نسخه، بکاپ دیتابیس بگیرید؛ مایگریشن ۰۰۰۷ JSON مزایا/مراحل را به ردیف تبدیل می‌کند (بدون از دست رفتن محتوا، ولی بکاپ همیشه شرط احتیاط است).

می‌توانید این بلوک را در یک اسکریپت `deploy.sh` روی هاست ذخیره کنید و بعد از هر pull فقط `bash deploy.sh` بزنید.

**قانون طلایی:** هرگز `.env` و `media/` را commit نکنید و فایل‌های تغییر‌کرده محلی روی هاست را با pull قاطی نکنید — اگر ترمینال هنگام pull خطای «local changes would be overwritten» داد:

```bash
git stash          # تغییرات محلی هاست را کنار می‌گذارد
git pull
# git stash drop   # اگر مطمئنید تغییرات محلی لازم نبودند
```

---

## روش ج — FTP / File Manager (اصلاح فوری)

برای تغییر ۲-۳ فایلی، یا وقتی دسترسی ترمینال هم موقتاً در دسترس نیست.

### با File Manager (بدون نرم‌افزار اضافه)

cPanel → File Manager → مسیر پوشه → فایل را انتخاب → Edit → ذخیره → در Setup Python App دکمه **Restart**.

### با FTP

1. cPanel → **FTP Accounts** → یک اکانت بسازید (یا از اکانت اصلی cPanel استفاده کنید)
2. با FileZilla وصل شوید:
   - Host: `ftp://yourdomain.com` ، پورت `21`
   - User/Pass: همان اکانت FTP (برای اکانت اصلی، نام کاربری cPanel)
3. کد را فایل‌به‌فایل (یا پوشه‌به‌پوشه) بکشید و رها کنید — FileZilla برای بازنویسی سؤال می‌پرسد
4. **همیشه بعد از FTP، ری‌استارت لازم است:** `touch ~/ostaapp/tmp/restart.txt` در ترمینال، یا دکمه Restart در پنل. (اگر ترمینال ندارید، در Setup Python App تب Configuration → دکمه Run pip → بدون تغییر Cancel هم باعث ری‌استارت می‌شود.)

**محدودیت‌های FTP:** migrate و collectstatic با FTP نمی‌شود (دستور پایتون است) — پس برای هر تغییر مدل یا استاتیک ناچار به ترمینال/cPanel هستید. FTP فقط برای آپلود فایل تمیز است.

---

## بعد از اولین دیپلوی — تنظیمات عملیاتی

### فعال‌سازی پیامک واقعی (کاوه‌نگار)

1. در kavenegar.com ثبت‌نام کنید و از پنل کاربری **API Key** بگیرید
2. خط فرستنده (Sender) را از پشتیبانی کاوه‌نگار فعال کنید
3. در `.env` (یا Environment variables پنل):

```ini
KAVENEGAR_ENABLED=True
KAVENEGAR_API_KEY=xxxx
KAVENEGAR_SENDER=10008663
```

4. `touch tmp/restart.txt` بزنید. با یک درخواست آزمایشی، وضعیت ارسال را در **پنل ← گزارش پیامک (SmsLog)** چک کنید — باید `sent` شود.

تا وقتی `KAVENEGAR_ENABLED=False` است هیچ پیامکی (و هزینه‌ای) ندارد؛ پیام‌ها فقط در جدول گزارش ذخیره می‌شوند.

### بکاپ

- **دیتابیس:** cPanel → phpMyAdmin → Export (هفته‌ای یک بار کافی است)
- **مدیا (عکس‌های درخواست‌ها):** File Manager → zip پوشه `media/`
- هر دو را روی کامپیوتر خودتان نگه دارید؛ بکاپ خودکار هاست هم معمولاً فعال است.

### امنیت — چک‌لیست نهایی

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` تصادفی و مخصوص هاست (نه همان مقدار لوکال)
- [ ] `DJANGO_SECURE_SSL_REDIRECT=True` و AutoSSL فعال
- [ ] رمز اکانت‌های ادمین عوض شده
- [ ] شماره موبایل اکانت ادمین ثبت شده (برای بازیابی رمز با پیامک)
- [ ] `.htaccess` سرورِ مستقیم `.env` را بسته (تست: `https://yourdomain.com/.env` باید 403 بدهد)
- [ ] ریپوی گیت‌هاب **خصوصی** است و `.env` در هیچ کاممی نیست
- [ ] Cron پاکسازی `media/tmp` فعال است (بخش ۰.۶)
- [ ] در پنل (تنظیمات ← پیامک) کلیدهای «پیامک تعمیرکار» و «پیامک تأیید به مشتری» مطابق میل تنظیم شده‌اند

---

## عیب‌یابی سریع

| مشکل | چک کنید |
|---|---|
| صفحه ۵۰۰ | تب «Errors» در Setup Python App + فایل `logs/django.log` |
| استاتیک‌ها ۴۰۴ یا ۵۰۰ | `collectstatic --noinput` زده‌اید؟ (پروژه مانیفست وایت‌نویز را چک می‌کند) |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` شامل دامنه واقعی با/بدون www |
| خطای CSRF در ورود ادمین | `DJANGO_CSRF_TRUSTED_ORIGINS` با `https://` و دامنه کامل |
| اتصال دیتابیس | نام کاربر/دیتابیس حتماً با پیشوند `cpaneluser_` کامل باشد |
| تغییرات اعمال نمی‌شود | `touch tmp/restart.txt` فراموش نشود |
| `ModuleNotFoundError: MySQLdb` | `pip install -r requirements.txt` با virtualenv فعال زده شده؟ (PyMySQL شیم را در passenger_wsgi نصب می‌کند) |
| `App not found` / Passenger | Application startup file دقیقاً `passenger_wsgi.py` باشد |
| صفحه اصلی بعد از آپدیت ارور دیتابیس می‌دهد | `python manage.py migrate` اجرا نشده (مثلاً مایگریشن ۰۰۰۷ محتوای صفحه اصلی) |
| در ادمین منوی کناری با ☰ باز نمی‌شود | کش مرورگر — یک رفرش سخت (Ctrl+F5) بزنید؛ CSS با هش نسخه سرو می‌شود |
| آیکون‌ها خالی‌اند | `collectstatic --noinput` بعد از آخرین تغییرات زده نشده |

## تست‌ها بعد از استقرار

```bash
source /home/USERNAME/virtualenv/ostaapp/3.11/bin/activate
cd ~/ostaapp
python manage.py test
```

هر سه روش به یک نتیجه می‌رسند؛ تفاوت فقط در «هر بار آپدیت چقدر وقت می‌گیرد» است. اگر بیش از دو-سه بار در ماه آپدیت خواهید داشت، از همان اول **روش Git** را راه بیندازید.
