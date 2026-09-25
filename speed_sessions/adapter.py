from allauth.account.adapter import DefaultAccountAdapter


class CustomAccountAdapter(DefaultAccountAdapter):
    """Hook point for allauth customisation.

    Community assignment during signup now lives in
    ``speed_sessions.forms.CustomSignupForm`` so validation can abort signup
    properly (see that module for details).
    """
