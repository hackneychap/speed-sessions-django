"""Inline event handlers are JavaScript: anything interpolated into them must be JS-escaped.

Django's HTML autoescaping is *not* enough for an `on…="…"` attribute. The browser
HTML-decodes the attribute value and then hands the result to the JavaScript parser, so
`{{ session.title }}` in an onclick compiles as source code, not as data.

Regression (reported from production 2026-11-17): a session titled "Joy to you, we've won"
rendered

    onclick="copyAllWorkoutsToWhatsApp('Joy to you, we&#x27;ve won', '...')"

and the browser decoded `&#x27;` back to a raw apostrophe, closing the JS string literal
one character early. The whole handler died with

    Uncaught SyntaxError: missing ) after argument list

so the "📋 Copy WhatsApp" button did nothing at all (the error is attributed to the
button's own line in the console, which makes it look unrelated to the title).
"""
import html as html_module
import re
from datetime import date
from pathlib import Path

import pytest
from django.urls import reverse

from session_planner.models import Session, SessionGroup

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# on*="..." / on*='...'  — a handler attribute, in either quote style
HANDLER_RE = re.compile(r"""\bon[a-z]+\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
MUSTACHE_RE = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)

# `{% url %}` tags are deliberately not covered: their output is a path, not user text.
SAFE_FILTERS = ("escapejs", "slugify")


def _onclick_for(content, function_name):
    """Return the raw onclick attribute whose handler calls `function_name`."""
    match = re.search(r'onclick="([^"]*' + function_name + r'[^"]*)"', content)
    assert match, f"no onclick handler calling {function_name} in the rendered page"
    return match.group(1)


def _make_session(community, test_user, title, group_name="Group A"):
    session = Session.objects.create(
        title=title,
        date=date.today(),
        community=community,
        creator=test_user,
        structure_json=[
            {"type": "single", "segment": {"reps": 4, "distance": 400, "intensity": "Interval", "rest": 60}}
        ],
    )
    SessionGroup.objects.create(session=session, name=group_name, vdot=50)
    community.managers.add(test_user)
    return session


@pytest.mark.django_db
def test_session_detail_copy_handler_escapes_apostrophe_in_title(
    logged_in_client, test_user, community, user_profile
):
    """A session title containing an apostrophe must survive HTML *and* JS parsing."""
    title = "Joy to you, we've won"
    session = _make_session(community, test_user, title)

    response = logged_in_client.get(reverse('session-detail', kwargs={'pk': session.id}))
    assert response.status_code == 200

    handler = _onclick_for(response.content.decode(), 'copyAllWorkoutsToWhatsApp')
    # What the browser hands to the JS parser is the HTML-decoded attribute value.
    decoded = html_module.unescape(handler)
    assert "we\\u0027ve won" in decoded, (
        f"title must be JS-escaped, not just HTML-escaped; decoded handler was: {decoded}"
    )


@pytest.mark.django_db
def test_session_detail_copy_handler_escapes_apostrophe_in_group_name(
    logged_in_client, test_user, community, user_profile
):
    """Group names are manager-configurable ("Women's Group"), so the same rule applies."""
    session = _make_session(community, test_user, "Tuesday Track", group_name="Women's Group")

    response = logged_in_client.get(reverse('session-detail', kwargs={'pk': session.id}))
    assert response.status_code == 200

    handler = _onclick_for(response.content.decode(), 'copyWorkoutToWhatsApp')
    decoded = html_module.unescape(handler)
    assert "Women\\u0027s Group" in decoded, (
        f"group name must be JS-escaped, not just HTML-escaped; decoded handler was: {decoded}"
    )


def test_no_inline_handler_interpolates_unescaped_template_text():
    """Repo-wide guard: every `{{ … }}` inside an `on…=` handler must be JS-escaped.

    This is the class-level version of the bug above — it catches a *new* handler added
    later, not just the two that broke. `escapejs` (string data) and `slugify`
    (slug-shaped data) are the two filters that make interpolation into JS safe.
    """
    violations = []

    for path in sorted(TEMPLATES_DIR.rglob("*.html")):
        source = path.read_text(encoding="utf-8", errors="replace")
        for handler_match in HANDLER_RE.finditer(source):
            handler = handler_match.group(1) or handler_match.group(2) or ""
            for expr_match in MUSTACHE_RE.finditer(handler):
                expr = expr_match.group(1).strip()
                if any(f"|{safe}" in expr for safe in SAFE_FILTERS):
                    continue
                line_no = source[: handler_match.start()].count("\n") + 1
                violations.append(
                    f"{path.relative_to(TEMPLATES_DIR.parent)}:{line_no} "
                    f"-> {{{{ {expr} }}}} (add |escapejs)"
                )

    assert not violations, (
        "inline JS handler(s) interpolate unescaped template text — the browser parses "
        "these as source code, so an apostrophe or quote in the data kills the handler:\n  "
        + "\n  ".join(violations)
    )
