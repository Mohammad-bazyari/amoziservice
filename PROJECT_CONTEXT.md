# PROJECT_CONTEXT — آموزی سرویس (Amozi Service)

> **Knowledge base for AI agents and future developers.** Read this file
> before changing anything in the project. Last full audit: 2026-10-21.
> Confidence is labelled throughout: VERIFIED, PARTIALLY VERIFIED,
> INFERRED, UNKNOWN / NEEDS CONFIRMATION.

---

## 0. How this knowledge base was built

Sources actually inspected on 2026-10-21 (all paths relative to project root):

| Source | Evidence available |
|---|---|
| Source code | All of `apps/`, `config/`, `templates/`, `static/js`, `static/css`, `tools/tailwind` — VERIFIED |
| Docs in repo | `README.md`, `DEPLOY.md`, `.env.example`, `.htaccess.example`, `docs/SEARCH-CONSOLE-GUIDE.md` — VERIFIED |
| Git history | Initialized locally on 2026-11-01 (branch `main`) connected to GitHub repo `Mohammad-bazyari/amoziservice` per owner request — VERIFIED |
| Prior AI chat sessions | Not directly accessible in this environment; some context survives via the docs themselves and previous deliverables in the workspace (e.g. React prototype components). Anything recovered from chat summaries is labelled INFERRED |
| Deployment artifacts | `osta-deploy.zip` (staging bundle, zip timestamps Sep 2026), `passenger_wsgi.py`, `.htaccess.example`, cron instructions in `DEPLOY.md` — VERIFIED as files; **the live host itself was not verified** |
| Database | `db.sqlite3` (local), `host_data.json` (content fixture dump) — VERIFIED |
| Logs | `logs/django.log`, `logs/devserver-texture.log` — run up to 2026-10-19 |

### Historical information still needing recovery
- **Full commits / dates of decisions** — no Git repo here; if a Git repo or  repo or a prior chat archive exists elsewhere, share it and this file will be
  updated.
- **Domain name, DNS records, GSC/Bing property status** — see §H/J.
- **User preferences beyond those documented in §C** — see §C.

---

## A. Project overview

- **Project name:** آموزی سرویس (Amozi Service) — دامنه: `amoziservice.com` (نام قبلی: اوستا سرویس / `ostaservice.ir`; مخزن: `Mohammad-bazyari/amoziservice`)
- **Purpose:** Persian-language (**RTL, fully fa-IR**) repair-booking site
  for wall-mounted gas boilers (پکیج) in Tehran: customer submits a
  multi-step request online with photos; repair tech receives SMS; admin
  tracks it in a custom Persian Django admin panel.
- **Business goal:** local lead generation for a Tehran boiler-repair
  business; audiences are homeowners in Tehran (customers) and the
  owner/technician (admin users).
- **User journeys:**
  1. Public: home → services (`/services/<slug>/`) → brands → wizard
     (`/request/step/service|problem|customer|address|images/`) → review →
     submit → success with tracking code `BR-1234`; SMS notifications.
  2. Admin: `/admin/` (login + `/admin/pw-recover/` SMS recovery) →
     dashboard → requests (status, notes, SMS log at `/panel/sms/`),
     CMS (home/about/contact content, services, brands, articles, FAQ).
- **Stack (verified from `requirements.txt`, `tools/tailwind/package.json`):**

| Component | Choice | Version |
|---|---|---|
| Backend | Python / Django | Django 5.2.x (`>=5.2,<5.3`) |
| DB (local) | SQLite (`db.sqlite3`) | bundled Python |
| DB (host) | MySQL via **PyMySQL 1.1.2** (pure-Python shim `install_as_MySQLdb()` in `passenger_wsgi.py`) | shared-host friendly |
| Env / config | `.env` via python-dotenv 1.1.1 + dj-database-url 3.0.1 | — |
| Static serving | WhiteNoise 6.9.0 (CompressedManifestStaticFilesStorage) | — |
| Images | Pillow 11.3.0 | — |
| CSS | Tailwind CSS **v4** (`@tailwindcss/cli ^4.1.8`, source in `tools/tailwind/`) | built to `static/css/app.css` |
| JS | Vanilla + Alpine.js (vendored `static/js/alpine.min.js`) | no Node production runtime |
| Fonts | Vazirmatn woff2, self-hosted in `static/fonts/` (Regular/Medium/Bold/ExtraBold) | — |
| Icons | Lucide icon subset bundled in `static/js/lucide-icons.js` (70 lines) | ISC |
| SMS | Kavenegar REST (via `requests` 2.32.5) with mock provider locally | — |
| Host | cPanel shared hosting (میزبان‌فا etc.), Passenger + `passenger_wsgi.py` | — |

- **Dev stage:** feature-complete for launch; code mentions migration 0007
  (benefits→rows) as "الزامی" in DEPLOY.md, meaning deploys are actively
  expected. Local test suite passes in repo README (see §L for status).
- **Production status: UNKNOWN / NEEDS CONFIRMATION.** The codebase is fully
  deploy-ready; whether an actual domain/host got used was not verifiable
  from the workspace. Ask the owner for the live URL.
- **Constraints / non-negotiables:**
  - Shared cPanel host: no SSH login, no compiled extensions, everything
    via cPanel Terminal / Setup Python App.
  - Persian UI, RTL, Persian digits where human-facing (`fa_digits` filter).
  - CMS-editable everything: templates must read from `SiteSettings`
    (`apps/core/models.py:8`) not hardcode.
  - Validation **shares the same regex between server and client**
    (`apps/requests/forms.py` exposes `PHONE_PATTERN`/`PHONE_ERROR`,
    `POSTAL_CODE_PATTERN`/`POSTAL_CODE_ERROR`, mirrored via
    `data-pattern`/`data-error-pattern` in `static/js/wizard-form.js`).
  - Production uploads count/size limits are env-config:
    `REQUEST_IMAGE_MAX_BYTES = 5 MB`, `REQUEST_IMAGE_MAX_COUNT = 3` (`config/settings.py:159-160`).

- **Implemented vs planned:**
  - Implemented: wizard (5 steps + review + submit with ajax-free
    progressive enhancement), request model with status history/notes/images
    and tracking codes `BR-####`, CMS for home/about/contact/services/
    brands/articles/FAQ, admin SMS recover flow, Kavenegar/SMS log with
    mock mode, sitemap + robots + JSON-LD schemas (
    `schema_organization.html`, `schema_website.html`, `schema_webpage.html`,
    service/brand/article/Article Markup, BreadcrumbList, FAQPage),
    dark-mode tuned by CSS variables in `tools/tailwind/tailwind.css`,
    custom Persian admin (`apps/core/admin.py` with `BaradaranAdminSite`),
    cron command `cleanup_request_tmp`.
  - Planned per docs: season-led article publishing workflow
    (`docs/SEARCH-CONSOLE-GUIDE.md`), maybe a periodic-service SMS reminder
    generator (explicitly "فعلاً در برنامه قرار نگرفته" in DEPLOY.md).
  - **Not implemented** (do not assume): accounts for customers,
    online payment, inventory/stock, multi-language.

---

## B. Project history and decisions (reconstructed)

| When | Decision / event | Evidence | Confidence |
|---|---|---|---|
| ~Sep 14 2026 | Project skeleton (first file timestamps in `osta-deploy.zip`, Sep 14) | zip timestamps | PARTIALLY VERIFIED |
| Sep 14 | Entry point chosen: Passenger + `passenger_wsgi.py`, config-from-env | `passenger_wsgi.py` docstring | VERIFIED |
| Sep 21 | Persian admin recovery-layer (`/admin/pw-recover/*`) and auth rules | `apps/accounts/urls.py`, `apps/accounts/recovery.py` | VERIFIED (code), date from zip |
| Sep 22–25 | CMS content built and fixtures exported (`host_data.json` timestamps up to Sep 25) | fixture JSON | PARTIALLY VERIFIED |
| Migration 0003…0007 chain | Per-service wizard options, `ServiceArea`, `Article`, brand `logo_theme`, homepage benefits → row model (0007) | filenames in `apps/content/migrations/` plus DEPLOY.md warnings | VERIFIED |
| Migration 0009 | `brand_logo_theme` added (dark card variant for light logos) | `apps/content/migrations/0009_brand_logo_theme.py` | VERIFIED |
| Migration 0011 | `HeroShowcase` model added to manage hero troubleshooting card & 3 article buttons from admin; 3 comprehensive boiler repair guides authored | `apps/content/models.py`, `apps/content/migrations/0011_heroshowcase.py` | VERIFIED |
| Oct 19–21 2026 | Accessibility/polish pass on wizard form and FAQ (aria-invalid, error summary, marquee, dark mode texture) visible in recent file mtimes and logs | file mtime, `logs/` | PARTIALLY VERIFIED (no Git) |
| Nov 03 2026 | Full production database restored from host dump (`ostaserv_osta.sql.gz`): 20 articles, 8 FAQs, 7 brands, 2 services, 10 requests, SiteSettings; adapted for schema evolutions (`accounts.0003`, `content.0009`); created `manage.py restore_host_dump`, exported `fixtures/production_data.json` and `fixtures/production_clean_mysql.sql` | `apps/core/management/commands/restore_host_dump.py`, `fixtures/*` | VERIFIED |
| Guideline | **Keep PyMySQL as the driver, never mysqlclient** — compiles are hard on shared hosts | comments in `requirements.txt` + `passenger_wsgi.py` | VERIFIED |
| Guideline | **Client-side validation is a hint; server stays authoritative** | `apps/requests/tests_wizard_form.py:159-164` ("test_server_still_rejects_what_the_client_hints_cannot_catch") | VERIFIED |
| Guideline | **No `.env` / `db.sqlite3` / `media/` in deploy zip.** The 2026-10-21 zip (`osta-deploy.zip`) violates this by containing `__pycache__/` — regenerate before next deploy. | `DEPLOY.md` §0.4 vs `unzip -l` | VERIFIED (mismatch) |
| Rejected (docs) | Direct `git push` to host / self-hosted bare repo — "SSH دسترسی خارجی معمولاً بسته است"; pull-from-cPanel-Terminal chosen instead | `DEPLOY.md` "روش ب" block | VERIFIED |
| Rejected (docs) | WhiteNoise bypass — `.htaccess` only speeds up media/static; Django stays the fallback | README §گام ۶ note | VERIFIED |
| Not chosen | Periodic service reminder generator | DEPLOY.md ۰.۶ parenthetical | VERIFIED (explicitly deferred) |

Decisions future agents **must not reverse without asking**:
- Do not replace PyMySQL with mysqlclient.
- Do not switch static serving from WhiteNoise + collectstatic + manifest.
- Do not change the tracking-code format (`BR-####`, 4 digits).
- Do not remove the SMS-recovery flow at `/admin/pw-recover/*` or move it
  (it is deliberately registered BEFORE `admin.site.urls` in
  `config/urls.py:14-15` because admin has a catch-all).
- Do not change language `LANGUAGE_CODE="fa"` or the Iranian timezone default.
- Do not introduce a second design language or replace the Tailwind v4
  tokens in `tools/tailwind/tailwind.css`.

---

## C. Owner preferences & working style

Recovered from project docs and workspace artifacts. **Confirm** anything
marked inferred with the owner.

Confirmed (documented in repo docs, i.e. written down by/for the owner):
- Wants Persian-first docs (README, DEPLOY, SEARCH-CONSOLE guide all in fa).
- Cares about a smoke-test checklist after every deploy (DEPLOY.md ۰.۸).
- Values SEO: asked for a whole guide to Search Console/Bing + GEO
  (`docs/SEARCH-CONSOLE-GUIDE.md`).
- Wants safe, cheap updates: doc explicitly says "بکاپ دیتابیس بگیرید
  قبل از pull" and warns against blind overwrites from ZIP.
- Admin panel ergonomics matter (toolbar, mobile ☰ menu, Ctrl+S/E
  shortcuts, icon picker mentioned in the smoke checklist).
- Budget-conscious: SMS is mock until `KAVENEGAR_ENABLED=True`, because
  real SMS costs money.

Inferred (needs owner confirmation):
- Prefers step-by-step walkthroughs written for a cPanel beginner
  (all three deploy docs are written that way).
- Likes thorough regression/behavior testing before delivery (a
  jsdom behavior harness was previously used to validate React
  prototypes; see §F "components/").
- Working language: Persian.
- **Note:** `apps/accounts/management/commands/seed_admin_accounts.py`
  creates an admin account with username == password (`mbazyari`/`mbazyari`)
  on purpose per docs, with the documented rule "change it after first
  login". Agents must never weaken this helper but must also never treat
  the seeded pair as production credentials.

Expectation not yet inferred from evidence: whether the owner wants
agents to ask before any big refactor. **NEEDS CONFIRMATION** — default
to asking.

---

## D. Design system and visual language

**Source of truth = `tools/tailwind/tailwind.css` (built to
`static/css/app.css`). Never invent colors; cite from there.** Full token
inventory lives in [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) — read
that before any UI change. Highlights:

- **Philosophy (docstrings in the tailwind entry):**
  "professional, trustworthy, service-marketplace feel" for brand blues;
  warm amber `cta-*` for conversion moments. Persian, RTL, dark-mode-aware,
  texture-rich but low-contrast surfaces; Arabic-script typography
  (Vazirmatn) with human, friendly tone ("ثبت درخواست", not bureaucratic).
- **Brand palette:** `brand-50…950` blues (e.g. `--color-brand-600: #1d63f1`),
  `cta-400…700` ambers (`--color-cta-500: #f59e0b`). Neutrals are Tailwind slate.
- **Surfaces/texture:** page wash + grain via CSS variables
  (`--noise-image`, `--page-wash`, `--dot-ink`, `--grid-ink`, `--glow-ink`,
  `--sheen`) in `tools/tailwind/tailwind.css:96-125`; all token-based so
  `[data-theme="dark"]` flips everything at once. No hardcoded white/black.
- **Typography:** Vazirmatn self-hosted, 4 weights (400/500/700/800),
  `--font-sans` overrides Tailwind default. `.num { direction: ltr;
  unicode-bidi: embed; }` for Latin-digit-safe spans. Persian digits via
  `apps/core/templatetags/fa.py` (`fa_digits`).
- **Radii/emphasis:** `--radius-card: 1rem`, `--shadow-card` (soft,
  low-opacity slate). Focus ring: 2px solid `--color-brand-600`, offset 2.
- **Motion:** defined keyframes `fade-up` (0.5s) / `fade-in` (0.4s),
  plus faq pager grid-rows animation; global reduced-motion override.
- **Dark mode:** user-toggled via `data-theme="dark"` on `<html>`,
  anti-FOUC inline script in `templates/base.html:6-24` with `<meta name="color-scheme">`
  synchronization, persisted in `localStorage.theme`. Managed by `static/js/theme.js`
  with View Transitions API bidirectional expanding circular reveal animation (both Light->Dark and Dark->Light) from button click coordinates, full-screen circular overlay fallback for legacy browsers, concurrency guard against rapid clicks, rotating sun/moon morph, cross-tab sync,
  OS `prefers-color-scheme` dynamic listener, and `prefers-reduced-motion` compliance.
  Tailwind `dark:` variant maps to `[data-theme]` (`@custom-variant dark` in the tailwind entry).
- **RTL specifics:** template `dir="rtl"`; icon set includes explicit
  `arrow-left`/`arrow-right` variants; marquee keyframes use +50% (not -50%)
  because reading direction is right-to-left (documented comment in the CSS).
- **Icon set:** Lucide names enumerated in `ADMIN_ICON_CHOICES`
  (`config/settings.py:118-130`) — the icon-picker for services picks from
  this list only; adding a new icon means editing **both** that settings
  tuple and `static/js/lucide-icons.js`.
- **Distinctive marking:** brand logos are themed deliberately — a light
  card stays light even in dark mode (`Brand.logo_theme`,
  `apps/content/migrations/0009_brand_logo_theme.py`, comment in the CSS
  `.brand-marquee__logo` block) because the SVGs only have contrast on one
  background.

### Components (verified, with source files)
| Area | Where | Notes |
|---|---|---|
| Site header/footer/buttons | `templates/partials/header.html`, `templates/partials/footer.html` | backdrop-blur glassmorphic header, pill navigation, circular reveal theme toggle, refined quick links, dark footer with brand ambient glow; sticky mobile conversion bar in `templates/base.html` |
| Homepage & Hero Showcase | `templates/home.html` | Dynamic word-rotate hero, dual glassmorphism showcase cards (desktop & mobile) with ambient pulse dot, service cards with top sheen & hover lift, brand scroller with edge fade masks & manual prev/next navigation, 4-step process cards with large watermark digits, final CTA banner |
| Request wizard inputs & radios | `@layer components` in `tools/tailwind/tailwind.css:154-205` (wizard-input/radios) + error styling via `[aria-invalid]` | dark-mode variants, completed step checkmarks & active ring in `templates/requests/wizard.html` |
| Marquee (brand logos) | `.brand-marquee*` in same file, JS in `static/js/marquee-nav.js` | smooth card step on prev/next click, pause-on-interaction, seamless drift resumption without jump, touch swipe, keyboard arrows, reduced-motion safe |
| FAQ accordion | `.faq-accordion*` in same file, JS in `static/js/accordion.js`, partial `templates/partials/faq_block.html` | grid-template-rows animation, WAI-ARIA pattern with arrow-key roving focus, sticky 2/5 intro column with quick-link badge |
| Toast / quick notifications | `static/js/wizard-toast.js` (classes generated here) | Tailwind `@source "../../static/js"` keeps them compiled |
| Lucide icons | `static/js/lucide-icons.js` hydrates `svg[data-lucide]` | server renders wrapper via custom `lucide` templatetag from `apps/core/templatetags/fa.py` |
| Error pages | `templates/400.html`, `403.html`, `404.html`, `500.html` | custom handlers in `config/urls.py:40-43` |
| React prototypes (dev-only, not shipped) | `components/*.tsx` + `.tscheck/tsconfig.json` | used as behavior-test playground for wizard inputs (constitute no production UI) |
| Admin styles | `static/css/admin-theme.css`, `static/css/admin-icon-picker.css`, `static/css/admin-mobile.css`, `apps/core/admin_toolbar.py` (ToolbarMixin), `static/js/admin-*.js` shortcuts/dependents | Persian SaaS admin design system; dual-theme (light/dark data-admin-theme), KPI dashboard, responsive drawer |

**Anti-patterns to avoid:** hardcoded colors instead of tokens; adding a
new icon without the settings tuple; forgetting `@supports
(-webkit-touch-callout: none)` 16px input sizing rule for iOS zoom
(`<16px` inputs trigger browser zoom — rule lives right below
`input.wizard-input`); shipping text animations without
`prefers-reduced-motion` guard.

---

## E. Website / design references

- **Verified references (from within repo docs):**
  - Lucide icons — the site bundles a hand-picked subset of Lucide
    `<https://lucide.dev>` (header comment in `static/js/lucide-icons.js`).
  - Kavenegar REST docs (`https://kavenegar.com/rest.html`) — SMS API.
  - WIX/GEO guidance references in `docs/SEARCH-CONSOLE-GUIDE.md`
    (Google Search Console, Bing Webmaster, IndexNow).
- **Inferred / inspiration sources:** No external "reference site" is
  recorded anywhere in the workspace. The color palette comments
  ("service-marketplace feel") suggest Tailwind-y service-marketplace
  inspiration (e.g. Kinern/Truckee-like apps) but nothing is confirmed —
  do not fabricate a reference.
- **What stays unique to this project:** Persian RTL layout, the
  brand-logo marquee with dual-theme card behavior, the wizard UX with
  progressive enhancement (works without JS), the Kavenegar + BR-#### SMS
  confirmation loop.

---

## F. Technical architecture

### Directory tree (key files)
```
config/          settings.py, urls.py, sitemaps.py, wsgi.py
apps/
  core/          models.py (SiteSettings singleton), views.py, common.py
                 (TimeStampedModel, SlugAutoMixin, SEOMixin), admin.py,
                 admin_toolbar.py, templatetags/fa.py,
                 management/commands/seed_site.py, context_processors.py
  content/       Brand, Service, ServiceArea, ProblemOption, HomePageItem,
                 HomePageContent, AboutPageContent, ContactPageContent,
                 Article, FAQ, Page
  brands/        ProxyBrand (proxy over content.Brand for /brands/ URLs)
  services/      thin URL/view layer over content.Service
  requests/      ServiceRequest, RequestStatusHistory, RequestNote,
                 RequestImage; forms.py wizard forms; views.py wizard views;
                 management/commands/cleanup_request_tmp.py
  notifications/ SmsTemplate, SmsLog; services/kavenegar.py (mock or real)
  accounts/      User(AbstractUser + phone), /admin/pw-recover/* recovery,
                 seed_admin_accounts command, admin dashboard views
templates/        base.html, home.html, about.html, contact.html, faq.html,
                  robots.txt, error pages, partials/, requests/ (wizard),
                  admin/ (customized Django admin), services/, brands/,
                  content/
static/           css/ (app.css, admin-*.css), js/, fonts/, img/ (logo.svg,
                  brands/, articles/), plus .htaccess.example at root
tools/tailwind/   Tailwind v4 source css (built → static/css/app.css)
docs/             SEARCH-CONSOLE-GUIDE.md
logs/             django.log, devserver-texture.log
```

### Routing (verified `config/urls.py`)
| URL | App | Note |
|---|---|---|
| `/` | core (+ content for articles) | home page |
| `/about/`, `/contact/`, `/faq/` | core | static-ish info pages |
| `/services/`, `/services/<slug>/` | services | Service + SEO |
| `/brands/` | brands | ProxyBrand |
| `/request/step/<step>/`, `/request/review/`, `/request/submit/`, `/request/success/<code>/` | requests | wizard |
| `/articles/`, `/articles/<slug>/` | content | blog |
| `/panel/sms/<id>/status\|retry/` | notifications | staff-only SMS status |
| `/admin/` | accounts (before admin) then `admin.site.urls` | recovery must precede admin catch-all |
| `/sitemap.xml`, `/robots.txt` | core/config | TemplateView + SITEMAPS |
| `handler400/403/404/500` | core.views | custom error pages |

### Data flow
Public wizard → `apps/requests/views.py` step views → session-based
in-browser draft (same logic as README docstring: "حفظ اطلاعات روی مرورگر
کاربر") (`apps/requests/messages.py`) → submit creates `ServiceRequest` +
images → `apps/notifications/services/dispatcher.py` sends SMS (mock or
Kavenegar) to the tech & customer → SmsLog rows → admin sequences status
updates through `ServiceRequest.set_status()` (writes `RequestStatusHistory`).

### Auth & security
- `AUTH_USER_MODEL = "accounts.User"` (AbstractUser + phone field,
  `apps/accounts/migrations/0002_user_phone.py`).
- Customers never log in; admin-only. Password recovery at
  `/admin/pw-recover/*` (`apps/accounts/recovery.py`) has TWO paths:
  **SMS code** (uses `SmsTemplate`) and **security question**
  (added 2026-10-22): instructions in step 1, secondary button
  «بازیابی با سوال امنیتی»; fields `User.security_question` /
  `User.security_answer_hash` (salted hash via `hash_answer`, set ONLY
  through the interactive `python manage.py set_security_question` —
  never in code/docs; answer matching is whitespace/case-normalized).
  Both paths converge on `/pw-recover/reset/` (needs session
  verified=True). Question path has per-IP throttle (20 attempts/hour)
  and 5 tries-per-session lockout. Accounts migration 0003 required on
  next host deploy.
- Env sprawl — all secrets in `.env`. Never write them into templates:
  `KAVENEGAR_API_KEY` is server-side only (`config/settings.py:163-165`
  comment).
- Production hardening block in `config/settings.py:178-188` (cookies
  secure, SSL redirect, HSTS 1y, X-Frame-Options DENY, nosniff).
- Upload limits: 10 MB POST, 5 MB/image, 3 images/request.
- Logging to rotating file `logs/django.log` (2 MB × 3 backups,
  `config/settings.py:190-212`). **Privacy note:** SMS mock sends logged at
  INFO include recipient phone numbers; keep logs out of public repos
  (they're gitignored via `*.log` + `logs/` unreachable in .gitignore —
  actually only `*.log` is listed; the folder name itself is not, but every
  file inside matches `*.log`).

### Sitemaps / feeds
`config/sitemaps.py` defines SITEMAPS for services/brands/articles/static
+ `robots.txt` is a Django template that mentions AI bots
(GPTBot, PerplexityBot, ClaudeBot — the DEPLOY.md smoke-check says
"۱۶ بلوک User-agent").

### Testing
Unit + behavioral suites in every app (`apps/*/tests*.py`, 13 test modules
total, including wizard-UI and recovery tests). Run with
`python manage.py test`.

### Dev-only artifacts that must not ship
- `components/*.tsx` + `_setup.ts` React prototype/sandbox (removed
  `_setup.ts` etc. after previous sessions — the clean set in
  `components/` is `accordion|faq|form|phone-input|postal-code-input|toast.tsx`,
  `.tscheck/tsconfig.json` typechecks them, no runtime dependency in Django).
- `.tscheck/`, `.venv/`, `__pycache__/`, `db.sqlite3`, `logs/`,
  `media/`, `staticfiles/`, `host_data.json`, `host_flush_content.py`,
  `osta-deploy.zip` (staging artifact).

---

## G. Development environment and commands

Verified from README + existing venv:
- **OS:** developed on Windows (project path contains `tamirgah baradaran`;
  `.venv` present) — Linux/macOS paths documented in README as well.
- **Runtime:** Python 3.13 detected in cached pyc names (`cpython-313`);
  the host targets Python 3.11+ (cPanel Setup Python App).
- **Package manager:** pip + venv. Node/npm only under `tools/tailwind/`
  for CSS rebuilds.
- **Install & run:**
  ```bash
  python -m venv .venv
  .venv/Scripts/activate      # Windows Git Bash
  pip install -r requirements.txt
  cp .env.example .env        # fill in
  python manage.py migrate
  python manage.py seed_site              # first-content seed (818 lines)
  python manage.py seed_admin_accounts
  python manage.py runserver              # http://127.0.0.1:8000
  ```
- **CSS rebuild (only when Tailwind classes are newly used):**
  ```bash
  cd tools/tailwind && npm install && npm run build
  ```
  Output goes to `../../static/css/app.css`. The built file ships with the
  repo, so Node is *not* needed just to edit templates.
- **Tests:** `python manage.py test`
  **Windows console caveat (VERIFIED 2026-10-21):** plain `python
  manage.py test` fails with 11 `UnicodeEncodeError` errors because the
  Windows console uses cp1256 and `seed_site.py` prints Persian text
  (`seed_site.py:438` `self.stdout.write("Created service: …")`). Run
  tests with UTF-8 output: `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python
  manage.py test` — with that, the full suite passes (exit 0). cPanel
  Linux hosts are unaffected.
- **Static files:** `python manage.py collectstatic --noinput`
  (WhiteNoise requires it after any static change; missing collectstatic
  can 500 pages due to manifest lookup).
- **Troubleshooting (verbatim from DEPLOY.md)**: see `docs/DEPLOYMENT.md`
  of this repo and `DEPLOY.md` عیب‌یابی table.
- **Common local pitfalls:**
  - `.env` missing → SECRET_KEY falls back to dev key + DEBUG True.
  - `MEDIA/` folders created automatically by the save() of SiteSettings.
  - `host_flush_content.py` (not fully audited by this KB) seems to reload
    content from `host_data.json` into db.sqlite3 — read its source before
    touching it. PARTIALLY VERIFIED.

---

## H. Deployment and infrastructure

Full step-by-step runbook lives in **`DEPLOY.md`** (root); agent-facing
status/facts live in **`docs/DEPLOYMENT.md`** (created alongside this
file). Key verified facts:

- **Target:** cPanel shared hosting (میزبان‌فا, ایران‌سرور, پارس‌پک),
  PHP-less; Passenger via `passenger_wsgi.py`, MySQL via PyMySQL shim.
- **Three documented deploy methods:** ZIP upload (first deploy),
  Git pull in cPanel Terminal (recommended for updates, repo must be private),
  FTP/File-Manager for tiny hotfixes.
- **.htaccess** roles: serve `media/` & `staticfiles/` directly by
  LiteSpeed, block `.env` and hidden files, caching & compression
  (`.htaccess.example` at repo root).
- **Cron:** nightly `cleanup_request_tmp` (only scheduled command so far).
- **Smoke-check checklist:** reproduced in `docs/DEPLOYMENT.md` §7.
- **Current status: UNKNOWN.** No evidence in workspace of an actual
  deployed production host (no domain, no GSC access, no screenshot of the
  live site). The only deployment artifacts present are repo-level
  (`osta-deploy.zip`, `passenger_wsgi.py`, `.htaccess.example`).
  **NEEDS CONFIRMATION from owner: domain name, hosting account provider,
  whether AutoSSL ran, GSC/Bing verification done (guide written but not
  confirmed applied, `docs/SEARCH-CONSOLE-GUIDE.md` ch0 prerequisites
  unchecked).**

### Environment variables (names only; values live in `.env`)
Production/core: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`,
`DJANGO_TIME_ZONE`, `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_HSTS_SECONDS`.

SMS: `KAVENEGAR_ENABLED`, `KAVENEGAR_API_KEY`, `KAVENEGAR_SENDER`.

**Golden rules:** real secret never in templates; set on cPanel via
"Setup Python App → Environment variables" or via `.env` next to
`passenger_wsgi.py`. Local default is SQLite and DEBUG=True; on host
DATABASE_URL + DEBUG=False.
`.gitignore` (root) correctly excludes `.env`, `db.sqlite3`, `media/`,
`staticfiles/`, `__pycache__/`, `.venv/`.

### Secrets audit performed 2026-10-21
| Location | Finding | Action needed |
|---|---|---|
| `.env` (local) | exists; not readable here (ignored tool-side) | Keep out of any repo/zip — already the `_`-policy in `.gitignore` |
| `.env.example` | placeholders only, safe | none |
| `requirements.txt`, `README`, `DEPLOY.md` | contain no credentials; the seeded admin pair (`mbazyari`) is **not** a secret—it's a boot account documented "change after first login" | none (keep changing) |
| `host_data.json` | content fixture only (no secrets found) | replace or exclude from any public bundle |
| `logs/django.log` | contains phone numbers (per SMS mock), no API keys found | never upload; `*.log` already gitignored |
| `osta-deploy.zip` | contains `__pycache__/` (contradicts DEPLOY.md §0.4 list) | regenerate a clean zip before next deploy |
| SMS API key | **never verified configured**; docs say how but status unknown | Owner: check cPanel env or `.env`; rotate if it was ever shared in a chat |

**No raw secret values appear in this file or docs/**
(`.env` itself is not read by this KB build).

---

## I. Integrations & credentials inventory

| Service | Purpose | Where used | Env vars | Status |
|---|---|---|---|---|
| Kavenegar REST | SMS to technician + SMS verification code for admin pw recovery | `apps/notifications/services/kavenegar.py`, `apps/accounts/recovery.py` | `KAVENEGAR_API_KEY`, `KAVENEGAR_SENDER`, `KAVENEGAR_ENABLED` | `UNKNOWN` — docs written; whether registered/key generated was not verifiable |
| Google Search Console | SEO submission & monitoring | `docs/SEARCH-CONSOLE-GUIDE.md` | n/a (UI-based) | not verified done |
| Bing Webmaster Tools / IndexNow | GEO on AI engines (Copilot, Perplexity) | `docs/SEARCH-CONSOLE-GUIDE.md` | n/a (uses a key file in `public_html`, `KEY.txt` inside the panel) | not verified done |
| cPanel (Setup Python App, MySQL, Cron, File Manager) | host | `DEPLOY.md` | none | host details unknown |
| GitHub (amoziservice) | code transport for the git-pull update flow | `DEPLOY.md` §b.1–2 | SSH key / PAT, never commit it | Initialized 2026-11-01, remote origin configured (`Mohammad-bazyari/amoziservice`) |
| No other third-party APIs found in code | — | — | — | — |

Rotation instructions (when needed): only-owner-manageable, cPanel env vars
or `.env` under passenger_wsgi; regenerate API key from Kavenegar panel and
update env, then `touch tmp/restart.txt`.

---

## J. SEO, analytics, public-web config

(Audited against templates and docs; live index status un-verified.)

- **Domain / canonical:** unknown (owner must confirm). Canonical is built
  dynamically from `request.build_absolute_uri` in `templates/base.html:22`.
- **robots.txt:** Django-rendered from `templates/robots.txt` — includes
  16 User-agent blocks including AI crawlers
  (GPTBot, PerplexityBot, ClaudeBot, …; VERIFIED in template) plus a
  `Sitemap:` line built from the request host.
- **sitemap.xml:** `config/sitemaps.py` + registrered SITEMAPS in
  `config/urls.py:24-32`.
- **Structured data (per page, VERIFIED in templates):**
  - site-wide: `Organization`, `WebSite`, `WebPage` — see
    `templates/partials/schema_organization.html`, `schema_website.html`,
    `schema_webpage.html`.
  - FAQ page: `FAQPage` JSON-LD built from the FAQ model
    (`templates/faq.html:10-25`).
  - service page: `Service`, `ItemList`, `BreadcrumbList` (per
    DEPLOY.md ۰.۸ checklist); article page: full `Article` with
    author/publisher/logo + `BreadcrumbList` in
    `templates/content/article_detail.html`.
  - Tags: `twitter:card`, `og:*` (with logo fallback), keyword meta,
    `robots` block override per template.
- **Analytics / advertising:** NONE FOUND in templates or docs
  (no Google Analytics or other tracker). If the owner adds one, update
  this file.
- **Search-Console plan:** documented step-by-step in
  `docs/SEARCH-CONSOLE-GUIDE.md`, includes weekly 10-min monitoring loop
  and IndexNow for Bing/Copilot; **not verified as executed.**
- **Core Web Vitals:** addressed by local fonts (preload Vazirmatn bold +
  regular in `templates/base.html:39-41`), minified Tailwind build,
  low JS footprint (Alpine + a few small vanilla scripts); LCP goal
  <2.5s stated in the guide.
- **Accessibility:** semantic headings, aria states on accordion
  (`aria-expanded`/`aria-controls`/`inert` in `static/js/accordion.js`),
  wizard forms emit `aria-invalid`/`aria-describedby` + error summary
  (`apps/requests/forms.py: WizardAriaMixin`), Perserve visible
  focus rings.

---

## K. Known bugs, technical debt & unresolved issues

| # | Issue | Evidence | Status | Confidence |
|---|---|---|---|---|
| 1 | `osta-deploy.zip` contains `__pycache__/` violating DEPLOY.md §0.4 rule | `unzip -l` 2026-10-21 | open — regenerate zip before next deploy | high |
| 2 | Git repo initialized and connected to GitHub (`Mohammad-bazyari/amoziservice`) | git status 2026-11-01 | resolved — repo initialized with `main` branch | high |
| 3 | Kavenegar is mock by default in every environment unless explicitly enabled; real SMS never verified E2E | `.env.example` flag + `logs/django.log` mock lines | verify a real SMS right after first live deploy | medium |
| 4 | `host_data.json` is a raw fixture of customer-facing content including timestamps; it currently lives at repo root and could drift from admin edits | file tree | decide: archive under `docs/` or remove once real DB exists | medium |
| 5 | Previous session left pieces of a React prototype workflow (`components/*.tsx`, `.tscheck/`) with unused-in-prod risk | file tree | DOCUMENTED (this file §F) — keep out of deploy zip | high |
| 6 | Logs include recipient phone numbers (from SMS mock tests) | `logs/django.log` | low risk locally; never publish logs | medium |
| 7 | The strict "El error post-signin" item in DEPLOY's smoke checklist checks six admin/UX points — no automated test covers them; they need manual QA per deploy | DEPLOY.md ۰.۸ | accept manual for now | medium |
| 8 | No analytics tool installed on the public site (see §J) — if the owner cares about traffic metrics, pick & wire one | code inspection | owner decision | low |
| 9 | `host_flush_content.py` purpose not fully audited | file list | read source before running it again | low |

### Previously fixed (verified resolved)
- SiteSettings business-name rename propagates across related CMS text
  fields (`SiteSettings.propagate_business_rename`, `apps/core/models.py:86-113`,
  covered by `BusinessRenamePropagationTests` in `apps/core/tests.py:96`).
- Wizard form validation regexes shared and tested
  (`apps/requests/tests_wizard_form.py:140-151` —
  `test_phone_rule_is_shared_between_server_and_client` and the analogous
  postal-code test pass).

---

## L. Roadmap & next actions

### Critical blockers (agree with owner first)
1. Confirm/establish the production deployment (host access, domain).
   Without it, nothing else ships. → update `docs/DEPLOYMENT.md` §0 with facts.
2. Decide Git strategy: `git init` + push to a private GitHub repo
   (enables DEPLOY.md "روش ب"). *Agent note: the user has not authorized
   remote creation or pushes; you must ask first.*
3. Re-generate a clean `osta-deploy.zip` (profile 0.4 list) if the ZIP
   path is to be used.

### High priority
- Real Kavenegar signup + line registration; verify both SMS paths
  (tech on new request, customer confirmation, admin recovery).
- Execute `docs/SEARCH-CONSOLE-GUIDE.md` end-to-end, then verify and log
  [done] status in that doc + here.
- Post-deploy smoke test from `DEPLOY.md` §۰.۸, then record the result.

### Medium priority
- Add automated covers for the manual smoke items (DEPLOY ۰.۸) where
  feasible (e.g. short admin UX tests in `apps/core/tests.py` style).
- Decide on `host_data.json` (`docs/fixture/`?), keep a real database as
  source of truth once deployed.
- Log rotation & log privacy hygiene (`*.log` already gitignored).
- Consider a single-language `robots.txt` `Disallow`/`Allow` polish for
  other AI agents (currently covered 16 bots — verify against newer
  algos on next content cycle).

### Low priority / future ideas (from docs, not agreed)
- Periodic-service SMS reminder generator (explicitly deferred in DEPLOY ۰.۶).
- Analytics tool selection (none chosen yet).
- Possibly track core-web-vitals in production once the host is live.

---

## M. Critical rules for future AI agents

1. **Read this file first** and cite it back ("here's what's already there")
   before proposing anything architectural.
2. Inspect actual sources before assuming; never implement from memory
   of other frameworks (everything here is tailwind-v4-on-Django-5 with
   Persian RTL).
3. **Preserve the existing visual identity**: use the tokens in
   `tools/tailwind/tailwind.css` (and `docs/DESIGN_SYSTEM.md`); never
   introduce arbitrary colors, spacing systems, "AI-generated" generic
   dashboards, or a second design system.
4. Both themes: every UI change must respect light and dark (`data-theme`)
   and tokenize via CSS variables, never hardcode white/black.
5. Persian RTL: keep templates `dir="rtl"`, Persian digits via `fa_digits`,
   `.num` for latin-digit spans; test icon direction with `arrow-left`/`-right`.
6. Never silently remove features, files, or warnings; if a template emits
   context referenced by tests, its behavior can't change without editing
   the matching test.
7. Server stays authoritative: client validations are hints; never let a
   UI change weaken server-side rules.
8. Never hardcode secrets; new config goes into `.env` /
   cPanel env vars, and name it in this KB (not its value).
9. Run `python manage.py test` and typecheck (`npx tsc --noEmit -p .tscheck/`
   if touching `components/`) after any code change; report failures honestly.
10. Never commit or push without explicit user authorization; never
    touch `.env`, `db.sqlite3`, `media/`, or logs on the host.
11. Update this knowledge base (`PROJECT_CONTEXT.md` and the `docs/`
    companions) whenever a meaningful architecture, deployment,
    design-system, or workflow decision changes.
12. Ask before destructive/expensive/irreversible actions: real SMS sends,
    database migrations on the host, edits to production content, removal
    of anything from CMS models, and any git remote setup.
13. When the owner's request conflicts with rules 3–9, surface the
    conflict explicitly instead of guessing.

---

## File map quick reference (paths are clickable here)
- [DEPLOY.md](DEPLOY.md) — full cPanel runbook (owner-facing).
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — agent-facing deploy facts.
- [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) — token inventory.
- [docs/SEARCH-CONSOLE-GUIDE.md](docs/SEARCH-CONSOLE-GUIDE.md) — SEO/GEO runbook.
- [tools/tailwind/tailwind.css](tools/tailwind/tailwind.css) — design tokens.
- [passenger_wsgi.py](passenger_wsgi.py) — entry point.
