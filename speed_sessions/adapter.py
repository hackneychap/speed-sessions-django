from allauth.account.adapter import DefaultAccountAdapter
from communities.models import Community


class CustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        # Don't call super().save_user() here — we replicate the parts we need
        # and handle community assignment ourselves so we can add proper errors.
        # allauth's default save_user() saves the user immediately via commit=True,
        # which makes error recovery impossible. We use commit=False instead.
        user = super().save_user(request, user, form, commit=False)

        community_name = request.POST.get('community_name', '').strip()
        join_code = request.POST.get('join_code', '').strip()

        if join_code:
            # Validate join code exists
            try:
                community = Community.objects.get(join_code__iexact=join_code)
                if not hasattr(user, 'profile') or user.profile is None:
                    form.add_error(
                        None,
                        "Your account has no profile. Please contact support."
                    )
                else:
                    user.profile.community = community
            except Community.DoesNotExist:
                form.add_error(
                    None,
                    "That community code doesn't exist. Please check it and try again, "
                    "or create a new community instead."
                )
        elif community_name:
            # Create new community and make user its manager
            try:
                community = Community.objects.create(name=community_name)
                community.managers.add(user)
                if not hasattr(user, 'profile') or user.profile is None:
                    form.add_error(
                        None,
                        "Your account has no profile. Please contact support."
                    )
                else:
                    user.profile.community = community
            except Exception as e:
                form.add_error(
                    None,
                    f"Could not create community '{community_name}': {e}"
                )
        else:
            # Neither join_code nor community_name — user must choose one
            form.add_error(
                None,
                "You must either create a new community or enter a community code "
                "to join an existing one. "
                "Use the form above to name your new community, or enter a code "
                "to join an existing community."
            )

        # Only save profile if user has one (created by post_save signal on User)
        if hasattr(user, 'profile') and user.profile is not None:
            user.profile.save()

        if commit:
            user.save()
        return user

    def error_messages(self):
        errors = super().error_messages()
        return errors
