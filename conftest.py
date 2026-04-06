import pytest
from django.contrib.auth.models import User
from communities.models import Community, UserProfile

@pytest.fixture
def test_password():
    return "strong-test-pass"

@pytest.fixture
def create_user(db, test_password):
    def make_user(**kwargs):
        kwargs.setdefault("username", "testuser")
        if "password" not in kwargs:
            kwargs["password"] = test_password
        return User.objects.create_user(**kwargs)
    return make_user

@pytest.fixture
def test_user(db, create_user):
    return create_user()

@pytest.fixture
def logged_in_client(db, client, test_user, test_password):
    client.login(username=test_user.username, password=test_password)
    return client

@pytest.fixture
def community(db, test_user):
    return Community.objects.create(
        name="Test Community",
        slug="test-community",
        manager=test_user
    )

@pytest.fixture
def user_profile(db, test_user, community):
    # UserProfile is created automatically by signal, so we just update it
    profile = test_user.profile
    profile.community = community
    profile.save()
    return profile
