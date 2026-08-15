import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from communities.models import Community, CommunityGroupVDOT

pytestmark = pytest.mark.django_db


def test_community_num_groups_defaults_to_three():
    c = Community(name="OTWRT")
    c.save()
    assert c.num_groups == 3


def test_community_num_groups_validates_range():
    c = Community(name="OTWRT", num_groups=0)
    with pytest.raises(ValidationError):
        c.full_clean()
    c.num_groups = 10
    with pytest.raises(ValidationError):
        c.full_clean()


def test_community_group_vdot_unique_position_per_community():
    c = Community(name="OTWRT")
    c.save()
    CommunityGroupVDOT.objects.create(community=c, position=1, display_name="Pacers", default_vdot=50.0)
    with pytest.raises(IntegrityError):
        CommunityGroupVDOT.objects.create(community=c, position=1, display_name="Pacers 2", default_vdot=51.0)


def test_community_group_vdot_str_uses_display_name():
    c = Community(name="OTWRT")
    c.save()
    g = CommunityGroupVDOT.objects.create(community=c, position=1, display_name="Pacers", default_vdot=50.0)
    assert str(g) == "Pacers (OTWRT)"
