# AGENTS.md — اوستا سرویس (Osta Service)

Persian RTL repair-booking site for boiler (پکیج) services in Tehran:
**Django 5.2 · Tailwind v4 · cPanel shared hosting (Passenger + PyMySQL) ·
Kavenegar SMS.** Public site + wizard (`/request/`), custom Persian admin
(`/admin/`), SMS notifications (mock by default).

## Mandatory on first touch of any task

1. **Read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) before changing
   anything.** It holds the verified architecture, decisions,
   design tokens, deployment facts and open questions.
2. Related deep dives: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
   (deploy facts & status) · [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md)
   (token inventory) · [`docs/SEARCH-CONSOLE-GUIDE.md`](docs/SEARCH-CONSOLE-GUIDE.md)
   (SEO/GEO runbook) · [`DEPLOY.md`](DEPLOY.md) (owner-facing cPanel runbook).
3. **Not a Git repo yet** — `git init` is possible but only with the
   owner's explicit approval (see PROJECT_CONTEXT §B.2/#L1).

## Key commands (local, Windows Git Bash or POSIX shell)

```bash
source .venv/Scripts/activate        # venv already exists
python manage.py runserver           # http://127.0.0.1:8000
python manage.py test                # full suite (13 test modules)
# Windows console only: prefix with PYTHONIOENCODING=utf-8 PYTHONUTF8=1
# (seed_site prints Persian; cp1256 console would UnicodeEncodeError)
python manage.py makemigrations && python manage.py migrate
python manage.py collectstatic --noinput   # required after any static change
cd tools/tailwind && npm install && npm run build   # only when new Tailwind classes appear
```

## Hard rules

- Persian UI is RTL — never flip templates to LTR or drop fa-IR.
- Colors/spacings/fonts ONLY from `tools/tailwind/tailwind.css` tokens;
  no invented hexes, no second design system, no hardcoded
  white/black (dark mode is `[data-theme="dark"]`).
- New icons must be added in BOTH `config/settings.py`
  (`ADMIN_ICON_CHOICES`) and `static/js/lucide-icons.js`.
- Inputs/labels/aria: wizard forms keep their
  `data-pattern` / `data-error-*` client hints, but the **server stays
  authoritative** (`apps/requests/forms.py` is the single source of regexes).
- Secrets: never write values into code, docs, or logs; config goes to
  `.env` (excluded from any zip per `DEPLOY.md` §0.4). Names-only when
  documenting variables.
- Do not touch `.env`, `db.sqlite3`, `media/`, or host data.
- Real SMS costs money: keep `KAVENEGAR_ENABLED=False` in dev; enabling
  it is an owner decision.
- Run the test suite after changes and report results honestly.
- Destructive, security-sensitive, costly, or hard-to-reverse actions
  (host changes, migrations on prod data, git remotes, deploy zips)
  require explicit owner approval.
- After significant architecture/deploy/design/workflow changes, **update
  `PROJECT_CONTEXT.md`** (and the related `docs/` file) in the same change.
