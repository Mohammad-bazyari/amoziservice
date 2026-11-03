# DESIGN_SYSTEM — آموزی سرویس (verified token reference)

> **Source of truth: [`tools/tailwind/tailwind.css`](../tools/tailwind/tailwind.css)**,
> built by `tools/tailwind/package.json` (`npm run build`) into
> [`static/css/app.css`](../static/css/app.css). This document *points at*
> that file; it never rivals it. When a token is missing here, read the
> source — do not invent values.
> Labels: **Implemented** / **Legacy** / **Proposed**.

---

## 1. Design philosophy

- Persian-first, RTL, human-toned local-service UX — friendly forms
  («ثبت درخواست»), not SaaS-dashboard chrome.
- Brand blues = trust/professionalism ("professional, trustworthy,
  service-marketplace feel" — comment in `@theme`), amber CTAs = warm,
  high-contrast conversion accents ("Accent for CTAs" comment).
- Depth comes from soft shadows, grain/texture washes and dot/glow
  utilities — all driven by CSS variables so **dark mode flips the whole
  chain at once, no hardcoded white/black** (comment block
  "سیستم بافت و عمق بصری").
- Accessibility as a rule, not an afterthought: visible brand-colored
  focus rings, `prefers-reduced-motion` global override, iOS 16px-input
  zoom fix, aria-driven components. Web-Interface-Guidelines-driven
  ("Respect users who opt out of non-essential motion" comment).

## 2. Color system — Implemented

### Theme tokens (Tailwind v4 `@theme`)
| Token group | Values | Notes |
|---|---|---|
| `--color-brand-50…950` | `#eef7ff` → `#152557` (full ramp in tailwind.css:40-53) | primary identity; e.g. `brand-600 #1d63f1` for actions/focus |
| `--color-cta-400…700` | `#ffb020`, `#f59e0b`, `#d97706`, `#b45309` | conversion accents, mobile CTA bar |
| neutrals | Tailwind slate (no custom palette) | surfaces, borders, text |
| semantic | Tailwind red family for errors (`border-red-400` invalid state), no custom success/warning tokens — **Proposed gap**: define success/warning if needed |

### Texture/depth variables (`:root` → `[data-theme="dark"]` overrides)
| Variable | Light | Dark |
|---|---|---|
| `--noise-image` | SVG feTurbulence grain (alpha 0.035) | darker warm-tinted grain (alpha 0.05) |
| `--dot-ink` | `rgb(2 32 71 / 0.05)` | `rgb(148 163 184 / 0.09)` |
| `--grid-ink` | `rgb(15 23 42 / 0.05)` | `rgb(148 163 184 / 0.06)` |
| `--glow-ink` | `rgb(51 130 252 / 0.07)` | `rgb(51 130 252 / 0.13)` |
| `--sheen` | white→transparent 42% | white 4%→transparent |
| `--page-wash` | two soft blue radials | blue + amber radials (dimmer) |

Background utilities: `bg-dot-grid`, `bg-line-grid` (44px), `bg-ambient-glow`,
`surface-sheen`, `texture-grain`, plus legacy-ish `bg-dots-white` /
`bg-dots-dark` (legacy pair kept; prefer the token versions).

### Interaction states
- Focus: `outline: 2px solid var(--color-brand-600); outline-offset: 2px`
  globally on `:focus-visible` (accordion overrides to inset −2px).
- Selected radio row: `border-brand-500 bg-brand-50 text-brand-800 ring-1 ring-brand-500`
  (dark: `bg-brand-950 text-brand-100`).
- Hover rows: `border-brand-300 bg-brand-50` (dark: `border-brand-500 bg-slate-800`).
- Invalid: `aria-invalid="true"` ⇒ red border + red focus (color is never
  the only signal — Persian error text + error summary accompany it).
- Open accordion item: `border-brand-200 shadow-card`; chevron rotates 45°
  and turns red when open.
- Buttons: `active:scale-[0.97]` on CTA bar links.

## 3. Typography — Implemented

- Family: `--font-sans: "Vazirmatn", Vazirmatn, Tahoma, ui-sans-serif,
  system-ui, sans-serif`. Self-hosted woff2 weights **400/500/700/800**
  in `static/fonts/` (Regular, Medium, Bold, ExtraBold); Regular+Bold
  preloaded in `templates/base.html:39-41`.
- All Latin digits rendered inside `<span class="num">…</span>` get
  `direction: ltr; unicode-bidi: embed` (keeps numbers LTR inside RTL text).
- Persian digits for human-facing numbers: `fa_digits` filter
  (`apps/core/templatetags/fa.py` pattern).
- Scale in practice: body `text-sm`/`text-base`, headings bold→extrabold;
  inputs `text-sm font-bold` inside the wizard (16px on iOS touch devices
  via `@supports (-webkit-touch-callout: none)`); FAQ answer `text-sm
  leading-8`; marquee names `text-xs`. No custom `--font-*` size tokens —
  standard Tailwind sizes.
- **RTL rule:** templates set `dir="rtl"`/`lang="fa"` (metas), marquee
  keyframes run `translateX(0 → +50%)` because of right-to-left reading.

## 4. Spacing, layout, radii, elevation

- Radius: `--radius-card: 1rem`; large cards `rounded-2xl`(1.25rem) for
  marquee chips/accordion; small controls `rounded-xl`.
- Elevation: `--shadow-card: 0 1px 2px rgb(15 23 42 / 0.06),
  0 8px 24px -12px rgb(15 23 42 / 0.12)`; lighter `shadow-sm` in marquee
  nav chips.
- Containers: `max-w-6xl px-4` page sections (faq), `max-w-lg grid-cols-2`
  mobile CTA bar.
- Z-index: mobile conversion bar `z-40`; sticky elements stay in the
  40-band; no other z conventions found.
- Breakpoints: Tailwind default (`sm` 640, `md` 768 — mobile CTA bar is
  `md:hidden`, marquee chips enlarge at `sm`).

## 5. Theme mechanics (dark/light)

- Toggle button `.theme-toggle` (sun/moon icons) calls inline
  `window.toggleTheme()` in `templates/base.html:57-72`; state persisted
  as `localStorage.theme`; anti-FOUC inline script applies
  `data-theme="dark"` before first paint (`base.html:8-17`); default =
  `prefers-color-scheme`.
- Tailwind dark variant bound to the attribute:
  `@custom-variant dark (&:where([data-theme="dark"] *, [data-theme="dark"]));`
- `[x-cloak]{display:none!important}` for Alpine pre-hide.
- **Rule for new UI:** use slate + token variables + `dark:` variants;
  text-theme colors only (page shell: `bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-200`).
- Known inconsistency: none found in current templates (first pass of a
  hardcode audit happened during the texture refactor; keep it clean).

## 6. Motion — Implemented

- Keyframes `fade-up` (0.5s ease-out, 12px rise) and `fade-in` (0.4s)
  exposed as tailwind animations `animate-fade-up` / `animate-fade-in`.
- Brand marquee: 30s linear infinite `brand-marquee-scroll`; pauses on
  hover/focus-within/`.brand-marquee--paused`; manual nav via
  `static/js/marquee-nav.js`.
- FAQ: `grid-template-rows 0fr→1fr` 200ms ease-out (`measure-free`
  animation), chevron `transition-[transform,color] 200ms`.
- Reduced motion: global `*` override to 0.01ms + marquee animation off;
  accordion still fully operable.
- Feedback: `active:scale-[0.97]` press effect on mobile CTAs, subtle
  `hover:-translate-y-0.5` on brand chips.

## 7. Icons & assets — Implemented

- **Lucide subset** bundled in `static/js/lucide-icons.js`; wrapper
  `<svg data-lucide="name">` rendered server-side by the `lucide`
  template tag, hydrated on load (no CDN, no runtime dependency).
- **The icon drawer is closed:** service icons must come from
  `ADMIN_ICON_CHOICES` (`config/settings.py:118-130`: flame, droplets,
  wrench, zap, gauge, timer, shield-check, clipboard-check, phone-call,
  search-check, target). New icon = edit BOTH that tuple and
  `lucide-icons.js`.
- Sizing: `w-4 h-4` (CTA bar) / `size-5` (accordion chevron) typical.
- Logos: `static/img/logo.svg` (site logo + favicon fallback +
  og:image fallback), brand logos `static/img/brands/*.svg`
  (ariston, baxi, butane, chappee, iran-radiator, lorch, optima),
  article images `static/img/articles/`.
- Brand-logo dual-theme cards: `brand-marquee__logo` (light card) vs
  `brand-marquee__logo--on-dark` (dark card); driven by `Brand.logo_theme`
  admin field — a logo's SVG has contrast on exactly one background, so
  that card does not follow the site theme (rule documented in CSS comment).

## 8. Component conventions (source files)

| Component | Authoritative source | Patterns |
|---|---|---|
| Page shell / header / footer / sticky mobile CTA | `templates/base.html`, `templates/partials/header.html` (198 l.), `footer.html` (87 l.) | mobile bar = 2 CTAs: ثبت درخواست (cta bg) + tel (brand bg), both `font-extrabold` |
| Wizard inputs/selects/radios | `tools/tailwind/tailwind.css` `@layer components` (wizard-* block, ~154-205) | `.wizard-select`, `.wizard-input`, `.wizard-radios label` rows; error via `[aria-invalid]`; dark-mode overrides in same block |
| Brand marquee | same file `.brand-marquee*` blocks | fixed chip `h-20 w-36 sm:h-24 sm:w-44`, fade masks at 8%/92%, pause affordances |
| Marquee nav buttons | `.marquee-nav` blocks | circular 11×11 white chips, ring, press-scale |
| FAQ accordion | `.faq-accordion*` blocks + `static/js/accordion.js` + `templates/partials/faq_block.html` | WAI-ARIA accordion: trigger `aria-expanded`/`aria-controls`, roving arrow/Home/End focus, panel `inert` when closed |
| Toast | `static/js/wizard-toast.js` (classes generated) | compiled into app.css via `@source "../../static/js"` |
| Django messages | `templates/partials/django_messages.html` | standard alerts |
| Error pages | `templates/400/403/404/500.html` | same shell |
| Admin panel | `templates/admin/`, `apps/core/admin.py` (`BaradaranAdminSite`) + `apps/core/admin_toolbar.py`, `static/css/admin-*.css`, `static/js/admin-*.js` | Persian admin, toolbar mixin (Ctrl+S/E/Shift+S), icon picker, horizontal-scroll dependents |
| React prototypes (NOT shipped) | `components/*.tsx` (accordion, faq, form, phone-input, postal-code-input, toast) + `.tscheck/tsconfig.json` | behavioral test sandbox; no Django import; keep out of the deploy zip |

## 9. Adding new UI — checklist

1. Colors only from `brand-*` / `cta-*` / slate / the CSS variables;
   no raw hex in templates or a new palette.
2. Both themes: check `data-theme="dark"` rendering; use `dark:` variants
   and/or token variables.
3. RTL-safe: test direction-sensitive items (arrows `arrow-left/right`,
   text alignment) in RTL context.
4. Accessibility: visible focus, aria state on dynamic components,
   reduced-motion respected, color never the sole error indicator.
5. If a Tailwind class is newly used → rebuild CSS (`tools/tailwind`,
   `npm run build`) or run `collectstatic` on the host — missing
   compiled class = missing style, not an error.
6. Regenerate a `python manage.py test` run; wizard/UI behavior has test
   coverage that templates must keep satisfying
   (`apps/requests/tests_wizard_form.py`, `apps/core/tests.py`).
