from django import forms
from django.contrib.auth.models import User


class ProfileForm(forms.ModelForm):
    """Editable subset of the user account.

    Deliberately excludes privileged fields (is_staff, is_superuser, groups,
    user_permissions) so users cannot escalate their own permissions.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
