from allauth.account.adapter import DefaultAccountAdapter
from communities.models import Community

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()

            community_name = request.POST.get('community_name')
            join_code = request.POST.get('join_code')

            if join_code:
                try:
                    community = Community.objects.get(join_code__iexact=join_code)
                    user.profile.community = community
                except Community.DoesNotExist:
                    pass
            elif community_name:
                community = Community.objects.create(name=community_name)
                community.managers.add(user)
                user.profile.community = community

            user.profile.save()
        return user
