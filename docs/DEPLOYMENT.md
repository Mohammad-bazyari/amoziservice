# DEPLOYMENT — agent-facing facts (آموزی سرویس)

> **This is NOT a duplicate runbook.** The authoritative, step-by-step
> deploy procedure for the owner lives in [`../DEPLOY.md`](../DEPLOY.md)
> (Persian, cPanel-focused). This file records the *verified infrastructure
> facts, current deployment status, and open questions* so a future AI
> agent can reason about deployment without re-auditing the repo.
> Confidence labels: VERIFIED / PARTIALLY VERIFIED / UNKNOWN / NEEDS CONFIRMATION.

---

## 1. Hosting architecture (target)

| Element | Value | Source |
|---|---|---|
| Provider | cPanel shared hosting (میزبان‌فا و مشابه) — no SSH from outside, no C-compiler reliability | VERIFIED (DEPLOY.md §۰.۱, requirements comments) |
| App server | Phusion Passenger via "Setup Python App", startup file `passenger_wsgi.py` | VERIFIED |
| Entry point | `passenger_wsgi.py`: installs PyMySQL as `MySQLdb`, sets `DJANGO_SETTINGS_MODULE=config.settings`, loads `.env` next to the file | VERIFIED |
| Runtime | Python 3.11+ on host; locally 3.13 was used | PARTIALLY VERIFIED (pycache tags) |
| Web server | LiteSpeed (cPanel), direct-serving of `staticfiles/` and `media/` via `.htaccess` after rename of `.htaccess.example` | VERIFIED (DEPLOY.md §۰.۷) |
| Static pipeline | WhiteNoise `CompressedManifestStaticFilesStorage` — Django serves if `.htaccess` is absent; **broken manifest ⇒ possible 500s** | VERIFIED (`config/settings.py` STORAGES DEPLOY.md FAQ) |
| Database (host) | MySQL (prefixes: full names become `cpaneluser_<name>`); driver PyMySQL 1.1.2 installed into venv | VERIFIED targets; LIVE credentials UNKNOWN |
| Database (dev) | SQLite at `db.sqlite3` when `DATABASE_URL` unset | VERIFIED (`config/settings.py`) |
| Cron | `0 3 * * *` daily `python manage.py cleanup_request_tmp` (media/tmp cleanup) | VERIFIED as documented; not verified as configured on host |
| Process restart | `mkdir -p tmp && touch tmp/restart.txt` or Setup Python App → Restart | VERIFIED |

## 2. Deployment procedure (summary — full detail in DEPLOY.md)

1. One-time: MySQL database + user (cPanel → MySQL® Databases), Setup
   Python App (root `ostaapp`, startup `passenger_wsgi.py`), AutoSSL.
2. Upload code — **allowed**: `manage.py`, `passenger_wsgi.py`, `config/`,
   `apps/`, `templates/`, `static/`, `tools/`, `requirements.txt`,
   `.env.example`, `.htaccess.example`, `.gitignore`.
   **Forbidden in the bundle**: `.venv/`, `.git/`, `db.sqlite3`, `media/`,
   `staticfiles/`, `logs/`, `.env`, `__pycache__/`.
3. In cPanel Terminal (activated venv): `pip install -r requirements.txt`,
   `cp .env.example .env` + fill real values, then
   `migrate` → `seed_site` → `collectstatic --noinput` →
   `seed_admin_accounts` (or `createsuperuser`).
4. Rename `.htaccess.example` → `.htaccess` in the domain's document root.
5. Restart (`touch tmp/restart.txt`) and run the §7 smoke checklist.
6. Updates afterwards: re-upload, or (preferred) `git pull` inside cPanel
   Terminal; re-run pip/migrate/collectstatic only when the relevant part
   changed; always `touch tmp/restart.txt`.

Three documented transports: **ZIP upload** (first deploy),
**Git pull from a private GitHub repo** (recommended for frequent updates),
**FTP/File Manager** (2–3 file hotfixes; cannot run migrate/collectstatic).

## 3. Domain & DNS checklist

- [x] Domain connected to hosting — VERIFIED: `amoziservice.com` / `www.amoziservice.com` -> `88.135.68.30`.
- [x] Nameservers — VERIFIED: `dns1.mizbanfadns.net` ... `dns4.mizbanfadns.net`.
- [x] SSL (Let's Encrypt / AutoSSL) — VERIFIED: Valid for `amoziservice.com`, `*.amoziservice.com` (Oct 2026 - Jan 2027).
- [ ] Host `.env` / Setup Python App `DJANGO_ALLOWED_HOSTS` includes `amoziservice.com,www.amoziservice.com`.
- [ ] Host `.env` / Setup Python App `DJANGO_CSRF_TRUSTED_ORIGINS` includes `https://amoziservice.com,https://www.amoziservice.com`.

## 4. SSL / TLS

Mechanism: cPanel AutoSSL (`DEPLOY.md` §۰.۱) + Django-level
`DJANGO_SECURE_SSL_REDIRECT=True`, HSTS 1 year
(`DJANGO_HSTS_SECONDS=31536000`), secure cookies — all applied when
`DEBUG=False` (`config/settings.py:178-188`).
Renewal: automatic via cPanel. Status on the real host: UNKNOWN.

## 5. Environment-variable inventory (names and purpose only)

| Var | Purpose | Where configured |
|---|---|---|
| `DJANGO_SECRET_KEY` | signing key — must be random & deployment-specific | `.env` next to `passenger_wsgi.py`, or Setup Python App → Environment variables |
| `DJANGO_DEBUG` | must be `False` on host | same |
| `DJANGO_ALLOWED_HOSTS` | comma list incl. `www` | same |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://`-prefixed origins for admin POSTs | same |
| `DJANGO_TIME_ZONE` | default `Asia/Tehran` | same |
| `DJANGO_SECURE_SSL_REDIRECT` | prod HTTPS redirect (default True) | same |
| `DJANGO_HSTS_SECONDS` | HSTS lifetime (default 31536000) | same |
| `DATABASE_URL` | `mysql://cpaneluser_dbuser:PASSWORD@localhost:3306/cpaneluser_dbname` | same (password must NOT be committed to this repo) |
| `KAVENEGAR_ENABLED` | `True` switches mock → real SMS (billing!) | same |
| `KAVENEGAR_API_KEY` | Kavenegar API key — server-side only, never rendered to templates | same |
| `KAVENEGAR_SENDER` | sender line (e.g. `10008663`) | same |

Placeholders live in `.env.example`; real values live ONLY in `.env` /
cPanel panel env vars. Backup of the `.env` is the owner's job; the file
is effectively irreplaceable from the repo. **Never print these values;
never commit `.env`.**

## 6. Database migration & backup procedure

- Migrations: `python manage.py migrate` inside the activated cPanel venv.
  Notably migration `content.0007` converts homepage benefits JSON →
  relational rows; DEPLOY.md requires a **phpMyAdmin → Export backup
  first** and asserts no content loss.
- Backups (from DEPLOY.md "بکاپ"):
  - Database: cPanel → phpMyAdmin → Export — weekly recommended.
  - Media: zip the `media/` folder via File Manager.
  - Host-level automatic backups are expected but NOT verified.
- Recovery path re-install-on-new-host: create DB → import SQL export →
  restore `media/` → redeploy code (this exact order is NOT yet written in
  DEPLOY.md; treat as the sensible default and test only with owner consent).

## 7. Post-deployment verification checklist (reproduced from DEPLOY.md §۰.۸)

| URL | Expected |
|---|---|
| `/` | homepage renders (benefits/steps populated, logo + phone) |
| `/request/` | wizard step 1 (service choice) |
| `/articles/` | article list |
| `/admin/` | login; `/admin/pw-recover/` is a separate page |
| `/sitemap.xml` | valid sitemap |
| `/robots.txt` | 16 User-agent blocks incl. AI bots (GPTBot, PerplexityBot, ClaudeBot…) |

Then a full test request end-to-end; check the two SmsLog rows (mock
status if SMS disabled), admin content forms (homepage benefits table,
service icon picker), mobile admin menu (☰ + 🌙/☀️ toggle), panel
shortcuts Ctrl+S / Ctrl+E / Ctrl+Shift+S, and minimal save-bars per form.
Finally verify `https://<domain>/.env` returns 403.

## 8. Rollback procedure

Not explicitly documented in DEPLOY.md. Sensible default consistent with
the doc's update flow (treat as PARTIALLY VERIFIED policy):

1. Codes: with Git method — `git log --oneline`, `git checkout <previous-tag>`
   then re-run pip/collectstatic if pinned deps/static changed, restart.
   With ZIP method — you keep the previous zip? (not evidenced; ask owner).
2. Database: restore latest phpMyAdmin export if a migration went wrong.
3. Always `touch tmp/restart.txt` after rollback and re-run the §7 smoke list.

## 9. Troubleshooting (verified from DEPLOY.md عیب‌یابی)

| Symptom | First checks |
|---|---|
| HTTP 500 | Setup Python App "Errors" tab + `logs/django.log` |
| Static 404/500 | `collectstatic --noinput` (manifest lookup!); also admin ☰ menu caching — force refresh |
| DisallowedHost | allowed hosts incl. domain with and without `www` |
| CSRF on admin login | CSRF_TRUSTED_ORIGINS with `https://` + full domain |
| DB connect fail | full `cpaneluser_` prefixed names |
| Change not visible | `touch tmp/restart.txt` |
| `ModuleNotFoundError: MySQLdb` | pip install in the *activated* venv (shim lives in `passenger_wsgi.py`) |
| Passenger "App not found" | startup file exactly `passenger_wsgi.py` |
| Homepage DB error after update | migrations not run (e.g. content.0007) |
| Empty icons | `collectstatic` after last static change |

## 10. Deployment history — what was actually done

| Fact | Status |
|---|---|
| `osta-deploy.zip` bundle exists (built May/Sep 2026 mix of dates; includes config/apps/tools per §0.4, but ALSO `__pycache__/`) | VERIFIED file; plan-audit needed — regenerate before any next ZIP deploy |
| Whether the zip was uploaded to any host | UNKNOWN |
| Any production URL serving this app | UNKNOWN / NEEDS CONFIRMATION |
| Any live migration / seed content on a host MySQL | UNKNOWN |
| Real SMS ever sent | UNKNOWN (logs show only mock sends) |
| GSC / Bing property claimed | UNKNOWN (the guide exists but its checklists are unchecked) |

### Open questions for the owner (ask these before touching deployment)
1. Site live? URL and hosting provider?
2. Domain DNS managed by which registrar (needed for Domain-property GSC)?
3. Was Setup Python App + MySQL configured, and what came of AutoSSL?
4. Any Kavenegar API key already issued (and has it ever been shared in a chat — needs rotation)?
5. Preferred update method going forward: ZIP or Git-from-private-repo?

## 11. Known operational risks

- **Local test runs on a Windows console need UTF-8 env overrides**
  (`PYTHONIOENCODING=utf-8 PYTHONUTF8=1`): otherwise every test class that
  seeds via `seed_site` errors on Persian `stdout.write` calls
  (`UnicodeEncodeError`, cp1256 console). Linux/cPanel hosts are
  unaffected. Not a code bug — do not remove the Persian seed output.
- Manifest-static 500s after adding static files without collectstatic.
- Blind ZIP extract can overwrite production `.env` / `media/` — the
  bundle list must be hand-checked every time (DEPLOY.md's own warning).
- SMS costs money once enabled; accidental `KAVENEGAR_ENABLED=True` + a
  crawling test script can drain the line credit — keep it False in dev.
- Only one scheduled cleanup cron; nothing alerts if it stops.
- `*.log` is gitignored (good) but local logs hold real phone numbers;
  keep them private.
