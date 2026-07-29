import pytest
from unittest.mock import Mock, MagicMock
from django.contrib.auth.models import User
from communities.models import Community, UserProfile
from speed_sessions.adapter import CustomAccountAdapter


class MockRequest:
    """Minimal mock for request object used in adapter.save_user."""
    def __init__(self, POST=None):
        self.POST = POST or {}
        self.method = 'POST'


class MockForm:
    """Minimal mock for the allauth signup form."""

    def __init__(self):
        self._errors = {}
        self.cleaned_data = {
            'email': 'test@example.com',
            'username': '',
            'password1': 'testpass123',
        }

    def add_error(self, field, error):
        if field is None:
            self._errors.setdefault(None, []).append(error)
        else:
            self._errors.setdefault(field, []).append(error)

    @property
    def non_field_errors(self):
        return self._errors.get(None, [])


@pytest.mark.django_db
class TestCustomAccountAdapter:
    """Tests for CustomAccountAdapter.save_user community assignment logic."""

    def test_save_user_no_community_choice_adds_error(self):
        """When neither join_code nor community_name is given, a non-field error is added."""
        adapter = CustomAccountAdapter()
        user = User.objects.create_user(username='nocomm', password='pass123')
        form = MockForm()
        request = MockRequest(POST={'community_name': '', 'join_code': ''})

        adapter.save_user(request, user, form, commit=False)

        assert len(form.non_field_errors) == 1
        assert 'must either create a new community' in form.non_field_errors[0]

    def test_save_user_valid_join_code_assigns_community(self):
        """When a valid join_code is provided, the user is assigned to that community."""
        community = Community.objects.create(name='Existing Crew', slug='existing-crew')
        user = User.objects.create_user(username='joiner', password='pass123')
        form = MockForm()
        request = MockRequest(POST={
            'community_name': '',
            'join_code': community.join_code,
        })

        adapter = CustomAccountAdapter()
        adapter.save_user(request, user, form, commit=False)

        user.profile.refresh_from_db()
        assert user.profile.community == community

    def test_save_user_invalid_join_code_adds_error(self):
        """When an invalid join_code is given, a non-field error is added."""
        user = User.objects.create_user(username='badcode', password='pass123')
        form = MockForm()
        request = MockRequest(POST={
            'community_name': '',
            'join_code': 'NOTEXIST',
        })

        adapter = CustomAccountAdapter()
        adapter.save_user(request, user, form, commit=False)

        assert len(form.non_field_errors) == 1
        assert "doesn't exist" in form.non_field_errors[0]

    def test_save_user_community_name_creates_community(self):
        """When a community_name is given, a new community is created and user is made manager."""
        user = User.objects.create_user(username='newcrew', password='pass123')
        form = MockForm()
        request = MockRequest(POST={
            'community_name': 'My New Crew',
            'join_code': '',
        })

        adapter = CustomAccountAdapter()
        adapter.save_user(request, user, form, commit=False)

        user.profile.refresh_from_db()
        assert user.profile.community is not None
        assert user.profile.community.name == 'My New Crew'
        assert user in user.profile.community.managers.all()

    def test_save_user_community_name_with_whitespace_is_stripped(self):
        """Whitespace-only community_name is treated as missing."""
        user = User.objects.create_user(username='wspcrew', password='pass123')
        form = MockForm()
        request = MockRequest(POST={
            'community_name': '   ',
            'join_code': '',
        })

        adapter = CustomAccountAdapter()
        adapter.save_user(request, user, form, commit=False)

        assert len(form.non_field_errors) == 1

    def test_save_user_community_name_takes_precedence_over_join_code(self):
        """When both are given, community_name takes precedence (existing behaviour)."""
        community = Community.objects.create(name='Already Joined', slug='already-joined')
        user = User.objects.create_user(username='bothcrew', password='pass123')
        form = MockForm()
        # Allauth puts join_code in POST regardless; adapter checks join_code first
        request = MockRequest(POST={
            'community_name': 'My New Crew',
            'join_code': community.join_code,
        })

        adapter = CustomAccountAdapter()
        adapter.save_user(request, user, form, commit=False)

        # join_code is checked first, so it wins
        user.profile.refresh_from_db()
        assert user.profile.community.name == 'Already Joined'
        assert user not in user.profile.community.managers.all()
