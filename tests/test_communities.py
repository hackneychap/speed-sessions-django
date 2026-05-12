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

from django.urls import reverse
from datetime import date
from session_planner.models import Session

@pytest.mark.django_db
def test_community_detail_view_permissions(client):
    """
    Verify that standard users from one community cannot see the next workout
    on another community's page.
    """
    # Create two communities
    community_a = Community.objects.create(name="Community A")
    community_b = Community.objects.create(name="Community B")

    # Create a user for Community A
    user_a = User.objects.create_user(username="user_a", password="password")
    user_a.profile.community = community_a
    user_a.profile.save()

    # Create a session for Community B
    Session.objects.create(
        title="B's Secret Session",
        date=date.today(),
        community=community_b,
        creator=user_a, # Doesn't matter who created for this test
        structure_json={}
    )

    client.login(username="user_a", password="password")

    # Access Community B's detail page
    response = client.get(reverse('community-detail', args=[community_b.slug]))

    # Next session block should be hidden
    assert response.status_code == 200
    assert b"Next Scheduled Workout" not in response.content
    assert b"B&#x27;s Secret Session" not in response.content

    # Access Community A's page (with a session to ensure it's visible to members)
    Session.objects.create(
        title="A's Open Session",
        date=date.today(),
        community=community_a,
        creator=user_a,
        structure_json={}
    )

    response = client.get(reverse('community-detail', args=[community_a.slug]))

    # Next session block should be visible to members
    assert response.status_code == 200
    assert b"Next Scheduled Workout" in response.content
    assert b"A&#x27;s Open Session" in response.content
