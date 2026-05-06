from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from communities.models import Community
from session_planner.models import Session, SessionGroup

class SessionPlannerViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.community = Community.objects.create(name='Test Community', slug='test-community')
        
        # Profile is created by signal, so we just update it
        self.user.profile.community = self.community
        self.user.profile.save()
        
        self.client = Client()
        self.client.force_login(self.user)

    def test_recalculate_group_plan_view(self):
        # Prepare POST data for a single group
        data = {
            'group_name': 'Group A',
            'group_vdot': '54.55',
            'forloop_counter': '1',
            'item_type': ['segment'],
            'reps': ['10'],
            'distance': ['400'],
            'intensity': ['Interval'],
            'rest': ['60'],
            'block_multiplier': ['1']
        }
        
        url = reverse('recalculate-plan')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        # Check if the response contains the expected group name
        self.assertContains(response, 'Group A')
        # Check if it contains the calculated pace for 54.55 VDOT (1:25.76)
        self.assertContains(response, '1:25.76')

    def test_generate_plan_view(self):
        # Prepare POST data for all groups
        data = {
            'group_a_name': 'A',
            'group_a_metric': 'vdot',
            'group_a_value': '54.55',
            'item_type': ['segment'],
            'reps': ['10'],
            'distance': ['400'],
            'intensity': ['Interval'],
            'rest': ['60'],
            'block_multiplier': ['1']
        }
        
        url = reverse('generate-plan')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A')
        self.assertContains(response, '1:25.76')

class TrainingBlockViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_block', password='password123')
        self.community = Community.objects.create(name='Test Community 2', slug='test-community-2', manager=self.user)
        self.user.profile.community = self.community
        self.user.profile.save()
        self.client = Client()
        self.client.force_login(self.user)

    def test_edit_training_block_page_loads(self):
        from session_planner.models import TrainingBlock
        block = TrainingBlock.objects.create(title="My Block", target_distance="5k", created_by=self.user)
        url = reverse('edit-block', args=[block.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Block")

    def test_reorder_training_block_templates(self):
        from session_planner.models import TrainingBlock, BlockSessionTemplate
        block = TrainingBlock.objects.create(title="My Block", target_distance="5k", created_by=self.user)
        t1 = BlockSessionTemplate.objects.create(block=block, week_number=1, title="T1", structure_json={})
        t2 = BlockSessionTemplate.objects.create(block=block, week_number=2, title="T2", structure_json={})
        
        url = reverse('edit-block', args=[block.id])
        response = self.client.post(url, {
            'template_order': f"{t2.id},{t1.id}"
        })
        
        self.assertRedirects(response, reverse('block-list'))
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t2.week_number, 1)
        self.assertEqual(t1.week_number, 2)

    def test_update_workout_and_save_as_template(self):
        from session_planner.models import Session, TrainingBlock, BlockSessionTemplate
        
        # 1. Create a session and a training block
        session = Session.objects.create(
            title="Old Title",
            date="2026-04-11",
            structure_json=[{"type": "single", "segment": {"reps": 1, "distance": 400, "intensity": "Threshold", "rest": 60}}],
            community=self.community,
            creator=self.user
        )
        block = TrainingBlock.objects.create(title="My Block", target_distance="5k", created_by=self.user)
        
        # 2. Update the session via save-workout view
        url = reverse('save-workout')
        data = {
            'session_id': session.id,
            'title': "New Title",
            'date': "2026-04-12",
            'item_type': ['segment'],
            'reps': ['8'],
            'distance': ['400'],
            'intensity': ['Interval'],
            'rest': ['90'],
            'block_multiplier': ['1'],
            'group_a_name': 'Group A',
            'group_a_metric': 'vdot',
            'group_a_value': '50',
            'save_as_template': 'on',
            'block_id': block.id,
            'template_week_number': '2'
        }
        
        response = self.client.post(url, data)
        
        # 3. Check redirects and database
        self.assertEqual(response.status_code, 200)
        self.assertIn('HX-Redirect', response.headers)
        
        session.refresh_from_db()
        self.assertEqual(session.title, "New Title")
        self.assertEqual(session.date.strftime('%Y-%m-%d'), "2026-04-12")
        self.assertEqual(session.structure_json[0]['segment']['reps'], 8)
        
        # Check template creation
        template = BlockSessionTemplate.objects.filter(block=block, week_number=2).first()
        self.assertIsNotNone(template)
        self.assertEqual(template.title, "New Title")
