"""Temporary settings used to repair a migration-history inconsistency.

Some existing databases (Vercel/Postgres) applied allauth's ``socialaccount``
migrations while ``django.contrib.sites`` was absent from ``INSTALLED_APPS``.
Now that ``sites`` is installed, Django's ``check_consistent_history`` refuses
to run any ``migrate`` because ``socialaccount.0001_initial`` is recorded as
applied before its dependency ``sites.0001_initial``.

Running ``migrate sites`` with this module drops the socialaccount apps so their
already-applied migration rows are treated as unknown and skipped by the check.
That applies the ``sites`` migrations; afterwards the normal ``migrate`` works.
"""
from .settings import *  # noqa: F401,F403

INSTALLED_APPS = [
    app for app in INSTALLED_APPS
    if not app.startswith("allauth.socialaccount")
]
