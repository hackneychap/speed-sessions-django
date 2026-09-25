import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from session_planner.models import TrainingBlock
from workouts.forms import ProfileForm


@pytest.mark.django_db
def test_profile_form_only_exposes_safe_fields():
    assert set(ProfileForm().fields) == {"first_name", "last_name", "email"}


@pytest.mark.django_db
def test_profile_view_cannot_escalate_privileges(logged_in_client, test_user):
    """A normal user must not be able to grant themselves staff/superuser."""
    response = logged_in_client.post(
        reverse("profile"),
        {
            "first_name": "Normal",
            "last_name": "User",
            "email": "normal@example.com",
            "is_superuser": "on",
            "is_staff": "on",
            "is_active": "on",
        },
    )
    assert response.status_code in (200, 302)

    test_user.refresh_from_db()
    assert test_user.is_superuser is False
    assert test_user.is_staff is False
    assert test_user.first_name == "Normal"


@pytest.mark.django_db
def test_apply_other_users_block_is_forbidden(logged_in_client, user_profile):
    other = User.objects.create_user(username="other", password="irrelevant123")
    block = TrainingBlock.objects.create(
        title="Someone Else's Block",
        target_distance="5k",
        created_by=other,
    )

    response = logged_in_client.post(
        reverse("apply-block-to-calendar"),
        {"block_id": block.id, "start_date": "2025-01-01"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_apply_tradeable_block_is_allowed(logged_in_client, community, user_profile):
    other = User.objects.create_user(username="other2", password="irrelevant123")
    block = TrainingBlock.objects.create(
        title="Community Block",
        target_distance="5k",
        created_by=other,
        is_tradeable=True,
    )

    response = logged_in_client.post(
        reverse("apply-block-to-calendar"),
        {"block_id": block.id, "start_date": "2025-01-01"},
    )
    assert response.status_code == 200
