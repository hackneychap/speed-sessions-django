# speed_session/utils.py

import math
import logging

logger = logging.getLogger(__name__)

# --- Constants ---
TRAINING_ZONES = {
    "Easy": {"min": 59.0, "max": 74.0},
    "Marathon": {"min": 75.0, "max": 84.0},
    "Threshold": {"min": 83.0, "max": 88.0},
    "Interval": {"min": 95.0, "max": 100.0},
    "Repetition": {"min": 105.0, "max": 110.0}
}

# A new dictionary for common interval training distances and their typical zones
COMMON_INTERVALS = {
    "200m Repetition": {"distance": 200, "zone": "Repetition"},
    "400m Repetition": {"distance": 400, "zone": "Repetition"},
    "400m Interval": {"distance": 400, "zone": "Interval"},
    "800m Interval": {"distance": 800, "zone": "Interval"},
    "1000m Interval": {"distance": 1000, "zone": "Interval"},
    "1000m Threshold": {"distance": 1000, "zone": "Threshold"},
    "1600m Interval": {"distance": 1600, "zone": "Interval"},
    "1600m Threshold": {"distance": 1600, "zone": "Threshold"}
}


# --- Helper Functions ---

def _calculate_vdot_score(distance_meters: float, time_minutes: float) -> float:
    """Internal helper to calculate the raw VDOT score."""
    if time_minutes <= 0:
        return None
    velocity = distance_meters / time_minutes
    vo2 = -4.60 + 0.182258 * velocity + 0.000104 * (velocity ** 2)
    percent_max = 0.8 + 0.1894393 * math.exp(-0.012778 * time_minutes) + 0.2989558 * math.exp(-0.1932605 * time_minutes)
    return vo2 / percent_max


def _format_time(time_minutes: float) -> str:
    """Formats decimal minutes into a MM:SS or HH:MM:SS string."""
    if time_minutes is None:
        return "N/A"
    total_seconds = int(time_minutes * 60)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def _solve_for_time(vdot_score: float, distance_meters: float) -> float:
    """
    Finds the race time for a given distance that equates to a VDOT score.
    """
    low_t = 0.5
    high_t = 600.0

    for _ in range(100):
        mid_t = (low_t + high_t) / 2
        if mid_t <= 0: return None

        mid_vdot = _calculate_vdot_score(distance_meters, mid_t)
        if mid_vdot is None: return None

        if mid_vdot > vdot_score:
            low_t = mid_t
        else:
            high_t = mid_t

    return (low_t + high_t) / 2


# --- Main Calculation Functions ---

def _calculate_vdot_score(distance_meters: float, time_minutes: float) -> float:
    """Internal helper to calculate the raw VDOT score."""
    if time_minutes <= 0:
        return None
    velocity = distance_meters / time_minutes
    vo2 = -4.60 + 0.182258 * velocity + 0.000104 * (velocity ** 2)
    percent_max = 0.8 + 0.1894393 * math.exp(-0.012778 * time_minutes) + 0.2989558 * math.exp(-0.1932605 * time_minutes)
    return vo2 / percent_max


def _format_time(time_minutes: float) -> str:
    """Formats decimal minutes into a MM:SS or HH:MM:SS string."""
    if time_minutes is None:
        return "N/A"
    total_seconds = int(time_minutes * 60)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


def _solve_for_time(vdot_score: float, distance_meters: float) -> float:
    """
    Finds the race time for a given distance that equates to a VDOT score.
    """
    low_t = 0.5
    high_t = 600.0

    for _ in range(100):
        mid_t = (low_t + high_t) / 2
        if mid_t <= 0: return None

        mid_vdot = _calculate_vdot_score(distance_meters, mid_t)
        if mid_vdot is None: return None

        if mid_vdot > vdot_score:
            low_t = mid_t
        else:
            high_t = mid_t

    return (low_t + high_t) / 2

def _get_velocity_from_vdot(vdot_score: float, intensity_percent: float) -> float:
    """Calculates the velocity in m/min for a given VDOT and intensity."""
    target_vo2 = vdot_score * (intensity_percent / 100.0)
    a = 0.000104
    b = 0.182258
    c = -(4.60 + target_vo2)
    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        return 0
    return (-b + math.sqrt(discriminant)) / (2 * a)


# --- Main Calculation Functions ---

def calculate_vdot(distance_meters: float, time_minutes: float) -> dict:
    """
    Calculates a VDOT score and tables for equivalent times, paces, and interval targets.
    """
    vdot_score = _calculate_vdot_score(distance_meters, time_minutes)
    if vdot_score is None:
        return None

    # --- 1. Calculate Equivalent Race Times ---
    standard_distances = {
        "400m": 400, "1600m": 1600, "5k": 5000, "10k": 10000,
        "Half Marathon": 21097.5, "Marathon": 42195
    }
    equivalent_times = {}
    for name, dist_m in standard_distances.items():
        equiv_time_min = _solve_for_time(vdot_score, dist_m)
        equivalent_times[name] = _format_time(equiv_time_min)

    # --- 2. Calculate Target Training Paces (per km) ---
    pace_targets = {}
    for zone_name, intensities in TRAINING_ZONES.items():
        # Calculate pace for both min and max of the range
        pace_data_max = calculate_pace_from_vdot(vdot_score, intensities["max"], 1000)
        pace_data_min = calculate_pace_from_vdot(vdot_score, intensities["min"], 1000)
        if pace_data_max and pace_data_min:
            km_pace_max_intensity = pace_data_max['pace_per_km']
            km_pace_min_intensity = pace_data_min['pace_per_km']
            pace_targets[
                zone_name] = f"{km_pace_max_intensity['minutes']}:{km_pace_max_intensity['seconds']:05.2f} - {km_pace_min_intensity['minutes']}:{km_pace_min_intensity['seconds']:05.2f} min/km"

    # --- 3. Calculate Target Interval Times ---
    target_interval_times = {}
    for name, details in COMMON_INTERVALS.items():
        zone = details["zone"]
        distance = details["distance"]
        min_intensity = TRAINING_ZONES[zone]["min"]
        max_intensity = TRAINING_ZONES[zone]["max"]

        # Calculate times for both min and max intensities
        pace_data_interval_max = calculate_pace_from_vdot(vdot_score, max_intensity, distance)
        pace_data_400m_max = calculate_pace_from_vdot(vdot_score, max_intensity, 400)
        pace_data_interval_min = calculate_pace_from_vdot(vdot_score, min_intensity, distance)
        pace_data_400m_min = calculate_pace_from_vdot(vdot_score, min_intensity, 400)

        if all([pace_data_interval_max, pace_data_400m_max, pace_data_interval_min, pace_data_400m_min]):
            # Max intensity gives the faster time (lower number)
            target_pace_max_intensity = pace_data_interval_max['target_pace']
            lap_pace_max_intensity = pace_data_400m_max['target_pace']
            interval_time_max_str = f"{target_pace_max_intensity['minutes']}:{target_pace_max_intensity['seconds']:05.2f}"
            lap_time_max_str = f"{lap_pace_max_intensity['minutes']}:{lap_pace_max_intensity['seconds']:05.2f}"

            # Min intensity gives the slower time (higher number)
            target_pace_min_intensity = pace_data_interval_min['target_pace']
            lap_pace_min_intensity = pace_data_400m_min['target_pace']
            interval_time_min_str = f"{target_pace_min_intensity['minutes']}:{target_pace_min_intensity['seconds']:05.2f}"
            lap_time_min_str = f"{lap_pace_min_intensity['minutes']}:{lap_pace_min_intensity['seconds']:05.2f}"

            target_interval_times[
                name] = f"{interval_time_max_str} - {interval_time_min_str} (Lap: {lap_time_max_str} - {lap_time_min_str})"

    # --- 4. Combine into a single response ---
    return {
        "vdot_score": round(vdot_score, 2),
        "equivalent_times": equivalent_times,
        "pace_targets": pace_targets,
        "target_interval_times": target_interval_times
    }


def calculate_pace_from_vdot(vdot_score: float, target_intensity_percent: float, target_distance_meters: float) -> dict:
    """
    Calculates a target running pace for a given distance and intensity.
    """
    if not (0 < target_intensity_percent <= 200):
        return None

    target_vo2 = vdot_score * (target_intensity_percent / 100.0)

    a = 0.000104
    b = 0.182258
    c = -(4.60 + target_vo2)

    discriminant = b ** 2 - 4 * a * c
    if discriminant < 0:
        return None

    velocity_mps = (-b + math.sqrt(discriminant)) / (2 * a)
    if velocity_mps <= 0:
        return None

    time_for_target = target_distance_meters / velocity_mps
    target_minutes = int(time_for_target)
    target_seconds = (time_for_target - target_minutes) * 60

    time_for_km = 1000 / velocity_mps
    km_minutes = int(time_for_km)
    km_seconds = (time_for_km - km_minutes) * 60

    return {
        "target_pace": {
            "minutes": target_minutes,
            "seconds": round(target_seconds, 2)
        },
        "pace_per_km": {
            "minutes": km_minutes,
            "seconds": round(km_seconds, 2)
        }
    }


def calculate_tss(vdot_score: float, workout_segments: list) -> int:
    """
    Calculates the Training Stress Score (TSS) for a workout.
    """
    if vdot_score <= 0:
        return 0

    # 1. Determine the runner's Threshold Pace (velocity in m/s)
    # T-Pace is the benchmark for TSS (Intensity Factor of 1.0)
    threshold_intensity = TRAINING_ZONES["Threshold"]["max"]
    threshold_velocity_mpm = _get_velocity_from_vdot(vdot_score, threshold_intensity)
    if threshold_velocity_mpm <= 0:
        return 0
    threshold_velocity_mps = threshold_velocity_mpm / 60

    total_tss = 0

    # 2. Loop through each segment of the workout
    for segment in workout_segments:
        try:
            reps = int(segment['reps'])
            distance_m = float(segment['distance'])
            intensity_zone = segment['intensity']

            # 3. Calculate the velocity and duration for this segment
            segment_intensity = TRAINING_ZONES[intensity_zone]['max']
            segment_velocity_mpm = _get_velocity_from_vdot(vdot_score, segment_intensity)
            if segment_velocity_mpm <= 0:
                continue

            segment_velocity_mps = segment_velocity_mpm / 60
            time_per_rep_s = distance_m / segment_velocity_mps
            total_duration_s = time_per_rep_s * reps

            # 4. Calculate Intensity Factor (IF) and TSS for this segment
            intensity_factor = segment_velocity_mps / threshold_velocity_mps
            segment_tss = (total_duration_s * segment_velocity_mps * intensity_factor) / (
                        threshold_velocity_mps * 3600) * 100

            total_tss += segment_tss
        except (ValueError, KeyError) as e:
            logger.warning(f"Skipping segment in TSS calculation due to invalid data: {e}")
            continue

    return round(total_tss)

