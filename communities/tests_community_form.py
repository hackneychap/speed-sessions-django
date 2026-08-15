import pytest
from communities.forms import CommunityForm
from communities.models import Community, CommunityGroupVDOT

pytestmark = pytest.mark.django_db


def test_community_form_exposes_num_groups_and_group_vdots():
    form = CommunityForm()
    assert "num_groups" in form.fields
    for i in range(1, 10):
        assert f"display_name_{i}" in form.fields
        assert f"default_vdot_{i}" in form.fields


def test_community_form_save_persists_group_vdots():
    community = Community(name="OTWRT", num_groups=5)
    community.save()
    data = {
        "name": "OTWRT",
        "num_groups": 5,
        "display_name_1": "Pacers",
        "default_vdot_1": 50.0,
        "display_name_2": "Group 2",
        "default_vdot_2": 45.0,
        "display_name_3": "Group 3",
        "default_vdot_3": 40.0,
        "display_name_4": "Group 4",
        "default_vdot_4": 38.0,
        "display_name_5": "Group 5",
        "default_vdot_5": 34.0,
    }
    form = CommunityForm(data, instance=community)
    assert form.is_valid(), form.errors
    form.save()
    community.refresh_from_db()
    assert community.num_groups == 5
    g1 = CommunityGroupVDOT.objects.get(community=community, position=1)
    assert g1.display_name == "Pacers"
    g5 = CommunityGroupVDOT.objects.get(community=community, position=5)
    assert g5.default_vdot == 34.0


def test_community_form_save_cleans_up_rows_beyond_num_groups():
    community = Community(name="OTWRT", num_groups=5)
    community.save()
    for i in range(1, 6):
        CommunityGroupVDOT.objects.create(
            community=community, position=i, display_name=f"Group {i}", default_vdot=float(i * 10)
        )
    data = {
        "name": "OTWRT",
        "num_groups": 3,
        "display_name_1": "Group 1",
        "default_vdot_1": 10.0,
        "display_name_2": "Group 2",
        "default_vdot_2": 20.0,
        "display_name_3": "Group 3",
        "default_vdot_3": 30.0,
    }
    form = CommunityForm(data, instance=community)
    assert form.is_valid(), form.errors
    form.save()
    assert CommunityGroupVDOT.objects.filter(community=community).count() == 3
    assert not CommunityGroupVDOT.objects.filter(community=community, position__gt=3).exists()
