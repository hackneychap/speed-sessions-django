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
