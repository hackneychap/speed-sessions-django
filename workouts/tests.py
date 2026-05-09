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
