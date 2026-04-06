import pytest
from django.contrib.auth.models import User
from communities.models import Community, UserProfile

@pytest.mark.django_db
def test_community_slug_generation():
    """Verify that a Community generates a valid slug from its name on save."""
    community = Community.objects.create(name="Running Club London")
    assert community.slug == "running-club-london"

@pytest.mark.django_db
def test_user_profile_created_on_user_save():
    """Verify that creating a User correctly triggers the post-save signal to create a UserProfile."""
    # Ensure the user doesn't exist yet
    username = "new_signal_user"
    assert not User.objects.filter(username=username).exists()
    
    # Create the user
    user = User.objects.create_user(username=username, password="password123")
    
    # Check if profile was created
    assert hasattr(user, 'profile')
    assert isinstance(user.profile, UserProfile)
    assert UserProfile.objects.filter(user=user).exists()
