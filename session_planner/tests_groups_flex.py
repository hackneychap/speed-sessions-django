import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from communities.models import Community, CommunityGroupVDOT
from session_planner.models import Session, SessionGroup

pytestmark = pytest.mark.django_db


def _base_segment():
    """POST fields for one 400m Threshold segment."""
    return {
        'item_type': ['segment'],
        'reps': ['1'],
        'distance': ['400'],
        'intensity': ['Threshold'],
        'rest': ['60'],
        'block_multiplier': ['1'],
    }


def _make_user_community(num_groups=3, manager=False):
    user = User.objects.create_user(username='planner_user', password='password123')
    community = Community.objects.create(
        name='Flex Community', slug='flex-community', num_groups=num_groups
    )
    user.profile.community = community
    user.profile.save()
    if manager:
        community.managers.add(user)
    client = Client()
    client.force_login(user)
    return user, community, client


def test_planner_with_one_group_saves_and_renders():
    _, community, client = _make_user_community(num_groups=1)

    data = {
        'title': 'One Group Session',
        'date': '2026-04-12',
        'groups_count': '1',
        'group_1_name': 'Solo',
        'group_1_metric': 'vdot',
        'group_1_value': '50',
        **_base_segment(),
    }
    response = client.post(reverse('save-workout'), data)
    assert response.status_code == 200

    session = Session.objects.get(title='One Group Session')
    assert session.groups.count() == 1
    assert client.get(reverse('session-detail', args=[session.id])).status_code == 200


def test_planner_with_nine_groups_saves_and_renders():
    _, community, client = _make_user_community(num_groups=9)

    data = {
        'title': 'Nine Group Session',
        'date': '2026-04-12',
        'groups_count': '9',
        **_base_segment(),
    }
    for i in range(1, 10):
        data[f'group_{i}_name'] = f'G{i}'
        data[f'group_{i}_metric'] = 'vdot'
        data[f'group_{i}_value'] = str(40 + i)

    response = client.post(reverse('save-workout'), data)
    assert response.status_code == 200

    session = Session.objects.get(title='Nine Group Session')
    assert session.groups.count() == 9
    assert [g.name for g in session.groups.all()] == [f'G{i}' for i in range(1, 10)]


def test_planner_prefills_community_display_names():
    _, community, client = _make_user_community(num_groups=3)
    for position, display_name, vdot in [(1, 'Pacers', 52), (2, 'Chasers', 47), (3, 'Cruisers', 42)]:
        CommunityGroupVDOT.objects.create(
            community=community, position=position,
            display_name=display_name, default_vdot=vdot,
        )

    response = client.get(reverse('planner-page'))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'Pacers' in body
    assert 'Cruisers' in body
    assert 'value="52.0"' in body


def test_edit_session_uses_saved_group_count_not_community_default():
    user, community, client = _make_user_community(num_groups=3, manager=True)

    session = Session.objects.create(
        title='Five Group Session',
        date='2026-04-12',
        structure_json=[{'type': 'single', 'segment': {'reps': 1, 'distance': 400, 'intensity': 'Threshold', 'rest': 60}}],
        community=community,
        creator=user,
    )
    for i in range(1, 6):
        SessionGroup.objects.create(session=session, name=f'G{i}', vdot=40 + i)

    response = client.get(reverse('edit-session', args=[session.id]))
    body = response.content.decode()
    assert response.status_code == 200
    assert 'name="group_5_value"' in body
    assert 'name="group_6_name"' not in body
