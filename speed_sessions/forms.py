from allauth.account.forms import SignupForm
from django.utils.text import slugify

from communities.models import Community, UserProfile


class CustomSignupForm(SignupForm):
    """Signup form that requires the user to create or join a community.

    Validation happens in ``clean()`` so a missing/invalid community aborts
    signup *before* the user account is created (unlike ``add_error`` calls
    made during ``save()``, which are too late to stop allauth).

    ``join_code`` takes precedence over ``community_name``: a code is an
    explicit invitation and the ``?join_code=`` link flow posts only the code.
    """

    def clean(self):
        cleaned_data = super().clean()

        join_code = (self.data.get("join_code") or "").strip()
        community_name = (self.data.get("community_name") or "").strip()

        if join_code:
            if not Community.objects.filter(join_code__iexact=join_code).exists():
                self.add_error(
                    None,
                    "That community code doesn't exist. Please check it and try "
                    "again, or create a new community instead.",
                )
        elif community_name:
            if len(community_name) > 100:
                self.add_error(
                    None, "Community name must be 100 characters or fewer."
                )
            slug = slugify(community_name)
            if slug and Community.objects.filter(slug=slug).exists():
                self.add_error(
                    None,
                    "A community with that name already exists. Choose a "
                    "different name, or join the existing one with its code.",
                )
        else:
            self.add_error(
                None,
                "You must either create a new community or enter a community "
                "code to join an existing one.",
            )

        return cleaned_data

    def save(self, request):
        user = super().save(request)

        join_code = (self.data.get("join_code") or "").strip()
        community_name = (self.data.get("community_name") or "").strip()

        community = None
        if join_code:
            community = Community.objects.filter(join_code__iexact=join_code).first()
        elif community_name:
            community = Community.objects.create(name=community_name)
            community.managers.add(user)

        if community is not None:
            profile = getattr(user, "profile", None)
            if profile is None:
                profile = UserProfile.objects.create(user=user)
            profile.community = community
            profile.save()

        return user
