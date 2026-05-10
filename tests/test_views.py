import pytest
from django.urls import reverse
from session_planner.models import TrainingBlock, BlockSessionTemplate, Session, SessionGroup
from datetime import date

@pytest.mark.django_db
def test_block_list_view(logged_in_client):
    """Verify that block_list_view returns a 200 status."""
    url = reverse('block-list')
    response = logged_in_client.get(url)
    assert response.status_code == 200
    assert "Training" in response.content.decode()
    assert "Blocks" in response.content.decode()

@pytest.mark.django_db
def test_get_schedule_form_view(logged_in_client, test_user):
    """Verify that get_schedule_form_view returns the correct HTML partial."""
    block = TrainingBlock.objects.create(
        title="Marathon Build",
        target_distance="Marathon",
        created_by=test_user
    )
    
    url = reverse('get-schedule-form', kwargs={'block_id': block.id})
    response = logged_in_client.get(url)
    
    assert response.status_code == 200
    content = response.content.decode()
    
    # Check for HTMX attributes and form elements
    assert 'hx-post=' in content
    assert reverse('apply-block-to-calendar') in content
    assert 'name="block_id"' in content
    assert f'value="{block.id}"' in content
    assert 'name="start_date"' in content
    assert 'type="date"' in content

@pytest.mark.django_db
def test_apply_block_to_calendar_view(logged_in_client, test_user, community, user_profile):
    """Verify that applying a block to the calendar creates the correct Session objects."""
    # 1. Create a block with two templates (Week 1 and Week 3)
    block = TrainingBlock.objects.create(
        title="5k Build",
        target_distance="5k",
        created_by=test_user
    )
    BlockSessionTemplate.objects.create(
        block=block,
        week_number=1,
        title="Week 1 Track",
        structure_json={"reps": 1}
    )
    BlockSessionTemplate.objects.create(
        block=block,
        week_number=3,
        title="Week 3 Track",
        structure_json={"reps": 3}
    )
    
    # 2. Post to the apply view
    start_date = "2025-01-01"
    url = reverse('apply-block-to-calendar')
    data = {
        'block_id': block.id,
        'start_date': start_date
    }
    
    response = logged_in_client.post(url, data)
    
    # 3. Assertions
    assert response.status_code == 200
    assert "Successfully added 2 sessions" in response.content.decode()
    
    # Check the created sessions
    sessions = Session.objects.filter(community=community).order_by('date')
    assert sessions.count() == 2
    
    # Week 1 should be Jan 1
    assert sessions[0].date == date(2025, 1, 1)
    assert sessions[0].title == "Week 1 Track"
    
    assert sessions[1].date == date(2025, 1, 15)
    assert sessions[1].title == "Week 3 Track"

@pytest.mark.django_db
def test_session_edit_view_loads_differentiated_plan(logged_in_client, test_user, community):
    """Verify that editing a session loads the differentiated plan results."""
    # 1. Create a session with structure and groups
    structure = [{"type": "single", "segment": {"reps": 10, "distance": 400, "intensity": "Interval", "rest": 60}}]
    session = Session.objects.create(
        title="Test Session",
        date=date.today(),
        community=community,
        creator=test_user,
        structure_json=structure
    )
    from session_planner.models import SessionGroup
    SessionGroup.objects.create(session=session, name="Group A", vdot=54.55)
    
    # Ensure the community manager is the test_user
    community.managers.add(test_user)
    community.save()
    
    # 2. Access edit view
    url = reverse('edit-session', kwargs={'pk': session.id})
    response = logged_in_client.get(url)
    
    # 3. Assertions
    assert response.status_code == 200
    content = response.content.decode()
    assert "Group A" in content
    # Check if the calculated pace for 54.55 VDOT (1:25.76) is present in the results
    assert "1:25.76" in content

@pytest.mark.django_db
def test_save_workout_with_differentiated_structure(logged_in_client, test_user, community, user_profile):
    """Verify that saving a workout includes group-specific structure overrides."""
    url = reverse('save-workout')
    
    # Define a base structure (10 reps)
    data = {
        'title': 'Test Workout',
        'date': '2025-01-01',
        # Base workout inputs
        'item_type': ['segment'],
        'reps': ['10'],
        'distance': ['400'],
        'intensity': ['Interval'],
        'rest': ['60'],
        'block_multiplier': ['1'],
        
        # Group A specific inputs (15 reps instead of 10)
        'group_a_name': 'Group A',
        'group_a_metric': 'vdot',
        'group_a_value': '50',
        'group_a_item_type': ['segment'],
        'group_a_reps': ['15'],
        'group_a_distance': ['400'],
        'group_a_intensity': ['Interval'],
        'group_a_rest': ['60'],
        'group_a_block_multiplier': ['1'],
    }
    
    response = logged_in_client.post(url, data)
    assert 'HX-Redirect' in response
    assert reverse('session-detail', kwargs={'pk': Session.objects.get(title=data['title']).id}) in response['HX-Redirect']
    
    # Check that Session was created with base structure (10 reps)
    session = Session.objects.get(title='Test Workout')
    assert session.structure_json[0]['segment']['reps'] == 10
    
    # Check that SessionGroup was created with differentiated structure (15 reps)
    group_a = SessionGroup.objects.get(session=session, name='Group A')
    assert group_a.structure_json[0]['segment']['reps'] == 15

@pytest.mark.django_db
def test_save_workout_multiple_group_overrides(logged_in_client, test_user, community, user_profile):
    """Verify that multiple group overrides are saved correctly and don't leak."""
    url = reverse('save-workout')
    
    data = {
        'title': 'Multi Group Workout',
        'date': '2025-01-01',
        'item_type': ['segment'],
        'reps': ['10'],
        'distance': ['400'],
        'intensity': ['Interval'],
        'rest': ['60'],
        'block_multiplier': ['1'],
        
        # Group A: 12 reps
        'group_a_name': 'Group A',
        'group_a_metric': 'vdot',
        'group_a_value': '50',
        'group_a_item_type': ['segment'],
        'group_a_reps': ['12'],
        'group_a_distance': ['400'],
        'group_a_intensity': ['Interval'],
        'group_a_rest': ['60'],
        'group_a_block_multiplier': ['1'],
        
        # Group C: 8 reps
        'group_c_name': 'Group C',
        'group_c_metric': 'vdot',
        'group_c_value': '40',
        'group_c_item_type': ['segment'],
        'group_c_reps': ['8'],
        'group_c_distance': ['400'],
        'group_c_intensity': ['Interval'],
        'group_c_rest': ['60'],
        'group_c_block_multiplier': ['1'],
    }
    
    response = logged_in_client.post(url, data)
    assert 'HX-Redirect' in response
    assert reverse('session-detail', kwargs={'pk': Session.objects.get(title=data['title']).id}) in response['HX-Redirect']
    
    session = Session.objects.get(title='Multi Group Workout')
    
    # Group A should have 12
    group_a = SessionGroup.objects.get(session=session, name='Group A')
    assert group_a.structure_json[0]['segment']['reps'] == 12
    
    # Group C should have 8
    group_c = SessionGroup.objects.get(session=session, name='Group C')
    assert group_c.structure_json[0]['segment']['reps'] == 8
    
    # Group B (no inputs in POST for B's structure) should fallback to base (10)
    # Note: If group_b_name/value were not in data, it wouldn't even be created. 
    # But let's assume it was created with base.

@pytest.mark.django_db
def test_save_workout_as_block_template(logged_in_client, test_user, community, user_profile):
    """Verify that saving a workout can also create a Training Block template."""
    block = TrainingBlock.objects.create(title="Test Block", target_distance="5k", created_by=test_user)
    
    url = reverse('save-workout')
    data = {
        'title': 'Template Workout',
        'date': '2025-01-01',
        'item_type': ['segment'],
        'reps': ['8'],
        'distance': ['400'],
        'intensity': ['Interval'],
        'rest': ['90'],
        'block_multiplier': ['1'],
        
        # Template inputs
        'save_as_template': 'on',
        'block_id': block.id,
        'template_week_number': '5'
    }
    
    response = logged_in_client.post(url, data)
    assert 'HX-Redirect' in response
    
    # Check if template was created
    template = BlockSessionTemplate.objects.get(block=block, week_number=5)
    assert template.title == 'Template Workout'
    assert template.structure_json[0]['segment']['reps'] == 8
