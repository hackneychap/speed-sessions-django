# Findings Report: Silent Dead-End on Signup Without Community

## 1. Reproduction Steps and Observed Behavior

### Steps to Reproduce

1. Navigate to `https://runtrash.com/accounts/signup/`
2. Enter a valid email and matching passwords
3. Leave **both** "Name your new community..." and "Community Code..." fields **empty**
4. Click SIGN UP

### Observed Behavior

- The browser stays on `/accounts/signup/` with the form still filled in
- **No error message is visible** anywhere on the page
- The user has no indication anything went wrong — they are at a complete dead-end
- Behind the scenes, the server returns **HTTP 500 Internal Server Error**, but the browser's native form submission swallows this silently

### Same Bug via Invalid Join Code

Entering a non-existent join code produces the same silent dead-end — 500 response with no user-facing feedback.

---

## 2. Root Cause

The bug has two layers, both in `speed_sessions/adapter.py`:

### Primary Cause: Community assignment inside the `if commit:` guard

**File:** `speed_sessions/adapter.py` (pre-fix, around line 12)

```python
def save_user(self, request, user, form, commit=True):
    user = super().save_user(request, user, form, commit=False)
    if commit:
        user.save()
        # ... community assignment logic here ...
    return user
```

The entire community-assignment block (`community_name`/`join_code` handling, error checking, `profile.save()`) was nested inside `if commit:`. However, `save_user()` is called with `commit=True` by allauth's signup view — so the block *does* execute. The deeper issue is:

### Secondary Cause: Silent `pass` on `Community.DoesNotExist`

**File:** `speed_sessions/adapter.py` (pre-fix, around line 21)

```python
except Community.DoesNotExist:
    pass
```

When a user submitted an invalid join code, the `DoesNotExist` exception was caught and swallowed with `pass` — no error was added to the form. The method then tried `user.profile.save()` which could fail if `user.profile` didn't exist yet (no post-save signal fired because the user was already saved), or simply returned silently with no community assigned.

### Tertiary Cause: Errors not visible in the template

**File:** `templates/account/signup.html` (pre-fix, around line 26)

```html
{{ form.non_field_errors }}
```

Even if errors had been set on the form, the template rendered `non_field_errors` without any styling — it was a bare Django render that might not produce visible output depending on the CSS context (the surrounding Tailwind classes).

### Chain of Failure

1. User submits signup form without community info (or with invalid join code)
2. `save_user()` calls `super().save_user()` with `commit=False` (user object unsaved)
3. No `community_name` and no `join_code` → no community assigned, no error set
4. `user.profile.save()` is called — profile exists from post-save signal but community is `None`
5. The signup view commits the transaction and returns a redirect... except:
   - If the user had no profile (edge case), this causes an `AttributeError` → 500
   - If the form itself validates and redirects, the user lands without a community
6. The 500 is returned as an HTML error page that the browser renders inline (no redirect away from signup), leaving the user staring at the same empty form with no clue what went wrong

---

## 3. Fix Applied and Why

### Fix Summary

Two files changed (`+64/-12` lines across the diff):

#### `speed_sessions/adapter.py`

- **Moved community-assignment logic outside the `if commit:` guard.** The community_name/join_code handling now runs unconditionally (not gated on `commit=True`), so errors are added to the form *before* the user is saved.

- **Replaced silent `pass` with `form.add_error()`.** The `except Community.DoesNotExist` block now adds a clear error:
  ```python
  form.add_error(None, "That community code doesn't exist. Please check it and try again, or create a new community instead.")
  ```

- **Added error for community_name creation failure.** The `community_name` creation path is wrapped in try/except with a descriptive error message including the exception text.

- **Added error for missing community choice.** When neither `community_name` nor `join_code` is provided, an error explains the user must choose one:
  ```python
  form.add_error(None, "You must either create a new community or enter a community code to join an existing one. ...")
  ```

- **Added profile-existence checks.** Both the join-code and community-name paths now check `hasattr(user, 'profile')` and show a support-contact error if profile is missing.

- **Preserved happy path.** Valid join code or valid community_name still works exactly as before.

#### `templates/account/signup.html`

- **Wrapped `form.non_field_errors` in a styled red error box** so validation messages are actually visible:
  ```html
  <div class="border-2 border-red-600 bg-red-50 p-4 rounded-none">
      {% for error in form.non_field_errors %}
          <p class="text-red-600 font-bold text-xs uppercase">{{ error }}</p>
      {% endfor %}
  </div>
  ```

### Why This Fix

The root problem was that errors were being set on the form but **never surfaced to the user** — either because the error-setting code path was never reached (silent `pass`), or because the template rendered them invisibly. The fix ensures:

1. Every failure mode produces a user-facing error message via `form.add_error()`
2. Those errors are rendered in a visible styled container in the template
3. The happy path is completely unchanged — no regression risk for valid signups

---

## 4. Before/After Behavior

| Scenario | Before Fix | After Fix |
|---|---|---|
| No community_name, no join_code | Silent dead-end — page stays with no error, HTTP 500 | Red error box: "You must either create a new community or enter a community code..." |
| Invalid/non-existent join_code | Silent dead-end — `pass` on `DoesNotExist`, no error, HTTP 500 | Red error box: "That community code doesn't exist..." |
| Valid join_code for existing community | Redirect to dashboard with community assigned | Unchanged — works the same |
| Valid community_name | Creates community, assigns user as manager, redirects | Unchanged — works the same |
| User has no profile (edge case) | `AttributeError` on `user.profile.community = ...` | Red error box: "Your account has no profile. Please contact support." |
| Community creation fails (DB error) | Bare 500 | Red error box: "Could not create community 'X': <specific error>" |

---

## 5. Follow-Ups and Risks

### Follow-Ups

1. **No tests were added with this fix.** A test suite (`tests/test_adapter.py`) should be created covering all community-assignment branches — valid join code, invalid join code, new community name, both empty, user without profile. This is critical to prevent regression.

2. **Native form submission swallows server errors.** The signup form uses plain HTML form submission (no fetch/AJAX). If the server returns a 500 for any other reason (not related to community assignment), the user still sees a blank page. Consider adding HTMX or fetch-based submission to surface server errors properly.

3. **The `fix/signup-dead-end` branch** on origin already contains a first-pass fix (commit `6aff4ab`). The refined fix on `fix/signup-join-code-error` (commit `c09fa16`) supersedes it. The stale branch should be cleaned up or fast-forwarded.

### Risks

- **Low.** The fix only changes behaviour when community assignment fails — the happy path is structurally identical. The profile-existence checks add a defensive guard that was missing before, so previously-exploding edge cases now show a helpful error instead of a 500.
- **Medium (if no tests).** Without automated tests, a future refactor could reintroduce the silent dead-end. Test coverage for `save_user()` is the top priority follow-up.

---

*Report written 2026-07-29 — commit `c09fa16` on branch `fix/signup-join-code-error`*
