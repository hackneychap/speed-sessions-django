import pytest
from django.contrib.auth.models import User
from session_planner.models import TrainingBlock, BlockSessionTemplate

@pytest.mark.django_db
def test_training_block_creation():
    user = User.objects.create_user(username="coach", password="password")
    block = TrainingBlock.objects.create(
        title="Marathon Build",
        description="A 12-week build for the London Marathon",
        target_distance="Marathon",
        created_by=user
    )
    assert TrainingBlock.objects.count() == 1
    assert block.title == "Marathon Build"
    assert str(block) == "Marathon Build"

@pytest.mark.django_db
def test_block_session_template_creation():
    user = User.objects.create_user(username="coach", password="password")
    block = TrainingBlock.objects.create(
        title="Marathon Build",
        target_distance="Marathon",
        created_by=user
    )
    template = BlockSessionTemplate.objects.create(
        block=block,
        week_number=1,
        title="Long Run",
        structure_json={"item_type": "segment", "reps": 1, "distance": 10000}
    )
    assert BlockSessionTemplate.objects.count() == 1
    assert template.week_number == 1
    assert str(template) == "Long Run (Week 1)"

@pytest.mark.django_db
def test_training_block_cascade_delete():
    user = User.objects.create_user(username="coach", password="password")
    block = TrainingBlock.objects.create(
        title="Marathon Build",
        target_distance="Marathon",
        created_by=user
    )
    BlockSessionTemplate.objects.create(
        block=block,
        week_number=1,
        title="Template 1",
        structure_json={}
    )
    BlockSessionTemplate.objects.create(
        block=block,
        week_number=2,
        title="Template 2",
        structure_json={}
    )
    
    assert BlockSessionTemplate.objects.count() == 2
    
    # Delete the block
    block.delete()
    
    # Check if templates are gone
    assert TrainingBlock.objects.count() == 0
    assert BlockSessionTemplate.objects.count() == 0
