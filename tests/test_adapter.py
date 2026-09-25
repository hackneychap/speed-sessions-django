import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from communities.models import Community
from speed_sessions.forms import CustomSignupForm

STRONG_PASSWORD = "V3ry-Str0ng-Passphrase!"


def make_form(**overrides):
    data = {
        "email": "runner@example.com",
        "password1": STRONG_PASSWORD,
        "password2": STRONG_PASSWORD,
        "community_name": "",
        "join_code": "",
    }
    data.update(overrides)
    return CustomSignupForm(data=data)


def make_request():
    request = RequestFactory().post("/accounts/signup/")
    # allauth's account setup reads request.session, which RequestFactory omits.
    SessionMiddleware(lambda r: None).process_request(request)
    return request


@pytest.mark.django_db
class TestCustomSignupForm:
    """Tests for community create/join validation during signup.

    Validation must happen at form-validation time (``clean``), not during
    ``save``, otherwise the user is created before the error is surfaced.
    """

    def _save(self, form, email):
        form.data["email"] = email
        return form.save(make_request())

    def test_no_community_choice_is_rejected(self):
        form = make_form(email="noc@example.com")
        assert not form.is_valid()
        assert "must either create a new community" in " ".join(form.non_field_errors())

    def test_whitespace_community_name_is_treated_as_missing(self):
        form = make_form(email="wsp@example.com", community_name="   ")
        assert not form.is_valid()
        assert "must either create a new community" in " ".join(form.non_field_errors())

    def test_invalid_join_code_is_rejected(self):
        form = make_form(email="bad@example.com", join_code="NOPE99")
        assert not form.is_valid()
        assert "doesn't exist" in " ".join(form.non_field_errors())

    def test_valid_join_code_assigns_community(self):
        community = Community.objects.create(name="Existing Crew")
        form = make_form(email="joiner@example.com", join_code=community.join_code)
        assert form.is_valid(), form.errors

        user = self._save(form, "joiner@example.com")
        user.refresh_from_db()
        assert user.profile.community == community
        assert user not in community.managers.all()

    def test_community_name_creates_community_and_manager(self):
        form = make_form(email="new@example.com", community_name="My New Crew")
        assert form.is_valid(), form.errors

        user = self._save(form, "new@example.com")
        user.refresh_from_db()
        assert user.profile.community is not None
        assert user.profile.community.name == "My New Crew"
        assert user in user.profile.community.managers.all()

    def test_join_code_takes_precedence_over_community_name(self):
        community = Community.objects.create(name="Already Joined")
        form = make_form(
            email="both@example.com",
            community_name="My New Crew",
            join_code=community.join_code,
        )
        assert form.is_valid(), form.errors

        user = self._save(form, "both@example.com")
        user.refresh_from_db()
        assert user.profile.community == community
        assert not Community.objects.filter(name="My New Crew").exists()


@pytest.mark.django_db
def test_duplicate_community_name_gets_unique_slug():
    first = Community.objects.create(name="Run Club")
    second = Community.objects.create(name="Run Club")
    assert first.slug == "run-club"
    assert second.slug == "run-club-2"
