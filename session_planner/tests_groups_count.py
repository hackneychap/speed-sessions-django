from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from communities.models import Community


class PlannerGroupsCountTest(TestCase):
    """Planner page renders one group card per community.num_groups (1..N indexing)."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.community = Community.objects.create(
            name='Test Community', slug='test-community', num_groups=5
        )

        # Profile is created by signal, so we just update it
        self.user.profile.community = self.community
        self.user.profile.save()

        self.client = Client()
        self.client.force_login(self.user)

    def test_planner_page_renders_num_groups_cards(self):
        response = self.client.get(reverse('planner-page'))

        self.assertEqual(response.status_code, 200)
        # 5th group card is rendered with index-based field names
        self.assertContains(response, 'name="group_5_value"')
        # No 6th card for a 5-group community
        self.assertNotContains(response, 'name="group_6_name"')
