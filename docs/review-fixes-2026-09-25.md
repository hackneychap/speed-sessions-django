# Review fixes — 2026-09-25

Branch: `review-fixes`
Scope: security, deployment correctness, and test health for the Django/Vercel + Postgres app.

Full test suite after changes: **53 passed** (was 41 passed / 7 failed).
`python manage.py check --deploy`: only the dummy-key warning (all HSTS/SSL/cookie warnings resolved).

## Critical security

### Privilege escalation on the profile page
- **Problem:** `workouts/views.py` used `UserChangeForm` with `instance=request.user`, and the
  template rendered every field. `UserChangeForm` exposes `is_superuser`, `is_staff`, `groups`
  and `user_permissions`, so any logged-in user could make themselves a superuser.
- **Fix:** new `workouts/forms.py::ProfileForm` restricted to `first_name`, `last_name`, `email`;
  `profile_view` uses it.
- **Test:** `tests/test_profile.py::test_profile_view_cannot_escalate_privileges`.

### Community session data leak
- **Problem:** `communities/views.py` loaded another community's next workout for any
  authenticated visitor.
- **Fix:** only query `next_session` for members/managers.
- **Test:** `tests/test_communities.py::test_community_detail_view_permissions` (was failing).

### Secret hygiene
- `.gitignore`: `.env*` now ignores `.envold` / `.envoldold` (these contained live
  `DATABASE_URL` / `SECRET_KEY` and were stageable).
- `.dockerignore`: `.env` is no longer copied into Docker image layers; also ignores
  `media/`, `staticfiles/`, `db.sqlite3*`, `patch*.diff`, `dockerdjango`.

## Signup flow (was silently broken)
- **Problem:** the account adapter called `form.add_error()` during `save()`. Because allauth
  validates before `save()`, the errors were never shown and the user was still created.
- **Fix:** new `speed_sessions/forms.py::CustomSignupForm` validates in `clean()`
  (create-or-join required; code must exist; name must be unique/length-limited) and assigns
  the community in `save()`. Registered via `ACCOUNT_FORMS` in settings.
  `speed_sessions/adapter.py` reduced to a hook class.
- `join_code` deliberately takes precedence over `community_name`.
- `communities/models.py`: duplicate community names now get unique slugs (`run-club`,
  `run-club-2`, ...) instead of raising `IntegrityError`.
- **Tests:** `tests/test_adapter.py` rewritten to exercise the form (validation + persistence).

## Deployment correctness (Vercel + Postgres)

### Static files
- `STATICFILES_STORAGE` was removed in Django 5.1, so the WhiteNoise compressed manifest
  storage was silently inactive. Replaced with a `STORAGES` dict; added
  `WHITENOISE_MANIFEST_STRICT = False` for graceful degradation.

### Media / uploads
- Uploads were written to an ephemeral filesystem and only served when `DEBUG`.
- Added S3-compatible object storage via `django-storages` + `boto3`, activated by
  `AWS_STORAGE_BUCKET_NAME` (works with S3, Cloudflare R2, Backblaze B2, DO Spaces,
  Supabase, MinIO). `MEDIA_URL` derives from CDN/endpoint/bucket. Warns on Vercel otherwise.

### Stripe
- Was hardwired to test keys (`STRIPE_TEST_SECRET_KEY` in views/admin, `STRIPE_LIVE_MODE = False`).
- Now `STRIPE_LIVE_MODE` / `STRIPE_ACTIVE_SECRET_KEY` are env-driven; views/admin use the
  active key and guard against it being unset. Admin currency corrected USD -> GBP to match
  the checkout flow. `DJSTRIPE_WEBHOOK_SECRET` no longer defaults to a placeholder.

### Settings hardening
- Security headers (HSTS, SSL redirect, secure cookies, `SECURE_CONTENT_TYPE_NOSNIFF`,
  referrer policy) now apply on any non-DEBUG host, not just Vercel.
- `CSRF_TRUSTED_ORIGINS` also trusts `https://*.vercel.app` for preview deployments.
- `load_dotenv(override=False)` so real env vars win; `SECRET_KEY` required outside dev/test.
- DB defaults to `conn_max_age=0` (serverless-friendly), configurable via `DB_CONN_MAX_AGE`.
- Added `django.contrib.sites` (required by allauth social login); removed dead `USE_L10N`.

## Other fixes
- `merch/views.py`: cart validates item is listed and that size/colour are valid; checkout only
  includes listed items; fixed open redirect on `HTTP_REFERER` via
  `url_has_allowed_host_and_scheme`.
- `session_planner/views.py`: `get_schedule_form_view` / `apply_block_to_calendar_view` now
  enforce access (`_user_can_access_block`: owner, tradeable, or same community); malformed
  `group_vdot` and block multiplier no longer raise 500s.
- `merch/tasks.py`: email sender uses `settings.DEFAULT_FROM_EMAIL` (was a mismatched domain).
- Removed obsolete `patch.diff` / `patch2.diff`; removed unused `csrf_exempt` imports.

## Dependencies
- `requirements.txt`: added `django-storages[s3]` + `boto3`, pinned ranges for previously
  unpinned packages. Test tooling moved to `requirements-dev.txt`.

## Required external configuration
1. Vercel env for media: `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME` (+ `AWS_S3_ENDPOINT_URL` /
   `AWS_S3_CUSTOM_DOMAIN` for non-AWS providers).
2. Stripe: `STRIPE_LIVE_MODE=True` with live keys and a real `DJSTRIPE_WEBHOOK_SECRET`.
3. Deploy must run migrations (adds `django.contrib.sites`).

## Still open (needs product/deployment decisions)
- `vercel.json` still uses legacy `routes`; `build.sh` is not referenced there, and running
  `migrate` at build time is racy. Review the actual Vercel build settings.
- `update_order_status_view` authorises via the first order item only (multi-community orders).
- Django Tasks email has no worker configured for serverless; it may not run on Vercel.

## Vercel deploy repair (follow-up, 2026-09-25)
Two build blockers surfaced when deploying this branch:

1. **`SECRET_KEY` required at build time.** `settings.py` hard-failed when the key was
   missing and `DEBUG=False`, but the Vercel build runs `collectstatic`/`migrate` (which
   don't need a key). Fixed: build-time management commands
   (`collectstatic`, `migrate`, `makemigrations`, `showmigrations`, `check`) use a throwaway
   key; the running server still requires a real `SECRET_KEY`.

2. **`InconsistentMigrationHistory: Migration socialaccount.0001_initial is applied before
   its dependency sites.0001_initial`.** The production database had allauth's
   `socialaccount` migrations applied while `django.contrib.sites` was absent. Adding
   `sites` (required by allauth social login) made Django's consistency check refuse to run
   any `migrate`.
   Fixed with:
   - `speed_sessions/settings_repair.py` — same settings minus the `allauth.socialaccount*`
     apps, so its already-applied rows are treated as unknown and skipped by the check.
   - `build.sh` — runs `migrate sites --settings=speed_sessions.settings_repair` before the
     normal `migrate`. Idempotent; a no-op once `sites` is applied.

   Verified end-to-end against a simulated database: normal `migrate` raised
   `InconsistentMigrationHistory`, the repair applied `sites.0001`/`sites.0002`, and the
   subsequent normal `migrate` reported no pending migrations. The default
   `Site(id=1, domain='example.com')` is created (used by `SITE_ID = 1`).

