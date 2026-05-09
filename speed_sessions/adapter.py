from allauth.account.adapter import DefaultAccountAdapter
from communities.models import Community

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if commit:
            user.save()

            community_name = request.POST.get('community_name')
            community_id = request.POST.get('community_id')

            if community_id:
                try:
                    community = Community.objects.get(id=community_id)
                    user.profile.community = community
                except Community.DoesNotExist:
                    pass
            elif community_name:
                community = Community.objects.create(name=community_name, manager=user)
                user.profile.community = community

            user.profile.save()
        return user
