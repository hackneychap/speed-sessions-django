from django.test import TestCase
from workouts.utils import calculate_vdot, calculate_pace_from_vdot, calculate_tss, _solve_for_time

class WorkoutUtilsTest(TestCase):
    def test_calculate_vdot(self):
        # 5k in 18:30 is approx 54.55 VDOT
        vdot_data = calculate_vdot(5000, 18.5)
        self.assertIsNotNone(vdot_data)
        self.assertAlmostEqual(vdot_data['vdot_score'], 54.55, places=2)
        self.assertIn('5k', vdot_data['equivalent_times'])
        self.assertEqual(vdot_data['equivalent_times']['5k'], '18:30')

    def test_calculate_pace_from_vdot(self):
        # VDOT 54.55, Interval intensity (100% VO2Max), 400m
        pace_data = calculate_pace_from_vdot(54.55, 100.0, 400)
        self.assertIsNotNone(pace_data)
        self.assertEqual(pace_data['target_pace']['minutes'], 1)
        self.assertAlmostEqual(pace_data['target_pace']['seconds'], 25.76, places=2)

    def test_calculate_tss(self):
        # Define a workout: 10 x 400m at Interval pace
        workout_segments = [
            {'reps': 10, 'distance': 400, 'intensity': 'Interval'}
        ]
        tss = calculate_tss(54.55, workout_segments)
        self.assertGreater(tss, 0)
        self.assertLess(tss, 100)

    def test_calculate_tss_invalid_segment(self):
        # Pass malformed segments to test the except (ValueError, KeyError) block
        workout_segments = [
            {'reps': 10, 'distance': 400, 'intensity': 'Interval'},  # Valid segment
            {'distance': 400, 'intensity': 'Interval'},              # Missing 'reps'
            {'reps': 'invalid', 'distance': 400, 'intensity': 'Interval'}, # Invalid 'reps'
            {'reps': 10, 'intensity': 'Interval'},                   # Missing 'distance'
            {'reps': 10, 'distance': 'invalid', 'intensity': 'Interval'}, # Invalid 'distance'
            {'reps': 10, 'distance': 400},                           # Missing 'intensity'
            {'reps': 10, 'distance': 400, 'intensity': 'InvalidZone'}, # Invalid intensity zone
        ]
        # Calculate TSS ignoring the invalid segments, which should only count the valid one
        tss_all = calculate_tss(54.55, workout_segments)

        # Calculate TSS with just the valid segment
        tss_valid = calculate_tss(54.55, [workout_segments[0]])

        self.assertEqual(tss_all, tss_valid)
    def test_solve_for_time(self):
        # Happy paths
        # A VDOT of 54.55 and distance of 5000m should result in roughly 18.5 minutes (18:30)
        time_minutes = _solve_for_time(54.55, 5000)
        self.assertIsNotNone(time_minutes)
        self.assertAlmostEqual(time_minutes, 18.5, places=2)

        # Test low VDOT score
        time_minutes_low = _solve_for_time(30, 5000)
        self.assertIsNotNone(time_minutes_low)
        self.assertAlmostEqual(time_minutes_low, 30.68, places=2)

        # Test high VDOT score
        time_minutes_high = _solve_for_time(85, 5000)
        self.assertIsNotNone(time_minutes_high)
        self.assertAlmostEqual(time_minutes_high, 12.62, places=2)

    def test_calculate_vdot_includes_marathon_interval_rows(self):
        """The 1000m/1600m Marathon interval targets must be computed."""
        vdot_data = calculate_vdot(5000, 18.5)
        interval_times = vdot_data['target_interval_times']
        self.assertIn('1000m Marathon', interval_times)
        self.assertIn('1600m Marathon', interval_times)
        # Must be a real time range with a lap time, not an empty string
        self.assertIn(' - ', interval_times['1000m Marathon'])
        self.assertIn('(Lap:', interval_times['1000m Marathon'])

    def test_marathon_interval_rows_actually_render(self):
        """Computed is not the same as displayed.

        _vdot_results.html filters target_interval_times by name into sections,
        so without a Marathon section the new rows would be computed and then
        rendered nowhere at all.
        """
        from django.template.loader import render_to_string
        vdot_data = calculate_vdot(5000, 18.5)

        html = render_to_string('workouts/_vdot_results.html', vdot_data)
        self.assertIn('Marathon (Race Pace)', html)

        # Scope the check to the Marathon section itself
        section = html.split('Marathon (Race Pace)')[1]
        self.assertIn('1000m', section)
        self.assertIn('1600m', section)
