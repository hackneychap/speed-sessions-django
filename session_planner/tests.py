import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase, Client, SimpleTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from communities.models import Community
from session_planner.models import Session, SessionGroup
from workouts.utils import TRAINING_ZONES

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
        # Check if it contains the 100m split label
        self.assertContains(response, '100m:')

    def test_recalculate_group_plan_with_marathon_intensity(self):
        """A Marathon segment must produce a pace, not be silently dropped.

        process_segment() returns None for an intensity missing from
        TRAINING_ZONES, which would make the segment vanish from the card.
        """
        data = {
            'group_name': 'Group A',
            'group_vdot': '40',
            'forloop_counter': '1',
            'item_type': ['segment'],
            'reps': ['6'],
            'distance': ['1000'],
            'intensity': ['Marathon'],
            'rest': ['60'],
            'block_multiplier': ['1'],
        }

        url = reverse('recalculate-plan')
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Group A')
        self.assertContains(response, '5:17.17')   # target pace @ VDOT 40 / 84%
        self.assertContains(response, '2:06.87')   # 400m lap
        self.assertContains(response, '0:31.72')   # 100m split

    def test_planner_surfaces_marathon_in_served_html(self):
        """Both dropdowns must actually reach the browser with Marathon in them.

        The template-source guard proves the option was written; this proves it
        is rendered by the real views.
        """
        # 1. Base structure builder on the planner page
        page = self.client.get(reverse('planner-page'))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, '>Marathon</option>')

        # 2. Per-group override dropdown, rendered into a group card
        plan = self.client.post(reverse('generate-plan'), {
            'groups_count': '1',
            'group_1_name': 'A',
            'group_1_metric': 'vdot',
            'group_1_value': '40',
            'item_type': ['segment'],
            'reps': ['6'],
            'distance': ['1000'],
            'intensity': ['Marathon'],
            'rest': ['60'],
            'block_multiplier': ['1'],
        })
        self.assertEqual(plan.status_code, 200)
        self.assertContains(plan, '>Marathon</option>')
        self.assertContains(plan, '5:17.17')       # Marathon pace rendered into the card

    def test_generate_plan_view(self):
        # Prepare POST data for all groups
        data = {
            'groups_count': '1',
            'group_1_name': 'A',
            'group_1_metric': 'vdot',
            'group_1_value': '54.55',
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
        self.assertContains(response, '100m:')

class TrainingBlockViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_block', password='password123')
        self.community = Community.objects.create(name='Test Community 2', slug='test-community-2')
        self.community.managers.add(self.user)
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
            'groups_count': '1',
            'group_1_name': 'Group A',
            'group_1_metric': 'vdot',
            'group_1_value': '50',
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

    def test_copy_training_block(self):
        from session_planner.models import TrainingBlock, BlockSessionTemplate

        # 1. Create original block (tradeable) by another user
        other_user = User.objects.create_user(username='otheruser', password='password123')
        original_block = TrainingBlock.objects.create(
            title="Original Tradeable Block",
            target_distance="10k",
            created_by=other_user,
            is_tradeable=True
        )
        BlockSessionTemplate.objects.create(
            block=original_block, week_number=1, title="T1", structure_json={}
        )

        # 2. Copy the block via copy-block view
        url = reverse('copy-block', args=[original_block.id])
        response = self.client.post(url)

        # 3. Check redirects and database
        copied_block = TrainingBlock.objects.filter(created_by=self.user).first()
        self.assertRedirects(response, reverse('edit-block', args=[copied_block.id]))

        self.assertIsNotNone(copied_block)
        self.assertEqual(copied_block.title, original_block.title)
        self.assertEqual(copied_block.created_by, self.user)
        self.assertEqual(copied_block.community, self.community)
        self.assertFalse(copied_block.is_tradeable)
        self.assertEqual(copied_block.templates.count(), 1)


class IntensityZoneConsistencyTest(SimpleTestCase):
    """Guard: every intensity the planner offers must exist in TRAINING_ZONES.

    process_segment() (session_planner/views.py) returns None for an intensity
    that is not a TRAINING_ZONES key, so a dropdown option with no matching zone
    makes the segment vanish from every group card AND every WhatsApp copy with
    no error at all. This test fails loudly at that boundary instead.
    """

    INTENSITY_TEMPLATES = [
        'session_planner/partials/_workout_segment.html',
        'session_planner/partials/_card_segment_row.html',
    ]

    def _options(self, rel_path):
        html = (Path(settings.BASE_DIR) / 'templates' / rel_path).read_text(encoding='utf-8')
        select = re.search(r'name="[^"]*intensity".*?</select>', html, re.S)
        self.assertIsNotNone(select, f'no intensity <select> found in {rel_path}')
        return [o.strip() for o in re.findall(r'<option[^>]*>([^<]+)</option>', select.group(0))]

    def test_dropdown_options_are_real_training_zones(self):
        for rel_path in self.INTENSITY_TEMPLATES:
            with self.subTest(template=rel_path):
                options = self._options(rel_path)
                self.assertTrue(options, f'no <option> tags found in {rel_path}')
                for opt in options:
                    self.assertIn(
                        opt, TRAINING_ZONES,
                        f'{rel_path} offers intensity "{opt}", which is not a '
                        f'TRAINING_ZONES key — segments using it would be silently dropped',
                    )

    def test_option_order_matches_locked_decision(self):
        """Marathon is selectable in both dropdowns, in the agreed order."""
        for rel_path in self.INTENSITY_TEMPLATES:
            with self.subTest(template=rel_path):
                options = self._options(rel_path)
                self.assertIn('Marathon', options)
                self.assertEqual(
                    options,
                    ['Marathon', 'Threshold', 'Interval', 'Repetition'],
                    f'{rel_path} option order changed',
                )

    def test_threshold_remains_the_default_option(self):
        """Threshold keeps the `or not segment.intensity` guard; Marathon must not.

        That guard is what makes a brand-new segment default to Threshold rather
        than Marathon. The `selected` keyword alone is not the signal — every
        option carries an `{% if ... %}selected{% endif %}` conditional.
        """
        for rel_path in self.INTENSITY_TEMPLATES:
            with self.subTest(template=rel_path):
                html = (Path(settings.BASE_DIR) / 'templates' / rel_path).read_text(encoding='utf-8')
                select = re.search(r'name="[^"]*intensity".*?</select>', html, re.S).group(0)

                marathon_line = next(l for l in select.splitlines() if '>Marathon</option>' in l)
                threshold_line = next(l for l in select.splitlines() if '>Threshold</option>' in l)

                # Marathon is opt-in only — it has no "blank means me" guard
                self.assertNotIn('or not segment.intensity', marathon_line)
                # Threshold is the fallback default
                self.assertIn('or not segment.intensity', threshold_line)
