from django.shortcuts import render
# speed_session/views.py

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Import your VDOT calculation function
from .utils import calculate_vdot, calculate_pace_from_vdot, TRAINING_ZONES


# Get an instance of a logger
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def calculate_vdot_view(request):
    """
    API view to calculate a VDOT score from a race performance.
    This view now handles form data from HTMX and returns an HTML fragment.
    """
    logger.info("Received request for VDOT calculation.")

    try:
        # --- THE FIX: Read from request.POST instead of request.body ---
        distance_val = request.POST.get("distance_meters")
        time_val = request.POST.get("time_minutes")

        logger.debug(f"Request POST data: distance={distance_val}, time={time_val}")

        # Check for missing keys
        if distance_val is None or time_val is None:
            logger.warning("Request was missing 'distance_meters' or 'time_minutes'.")
            # You could render an error template here if you wanted
            return JsonResponse({"error": "Request must contain 'distance_meters' and 'time_minutes'."}, status=400)

        distance = float(distance_val)
        time = float(time_val)

    except (ValueError, TypeError):
        logger.warning("Invalid non-numeric values in request.")
        return JsonResponse({"error": "Invalid non-numeric values for distance/time."}, status=400)

    # Call your utility function which returns a full dictionary
    vdot_data = calculate_vdot(distance, time)

    if vdot_data is None:
        logger.warning("VDOT calculation failed, likely due to invalid time.")
        return JsonResponse({"error": "Calculation failed. Ensure time is greater than zero."}, status=400)

    logger.info(f"Successfully calculated VDOT: {vdot_data['vdot_score']}")

    # --- THE SECOND FIX: Render the HTML fragment instead of JSON ---
    return render(request, 'workouts/_vdot_results.html', vdot_data)

@csrf_exempt
@require_http_methods(["POST"])
def calculate_pace_view(request):
    """
    API view to calculate a target pace from a VDOT score.
    Expects JSON with 'vdot_score', 'intensity_zone', and 'target_distance_meters'.
    """
    logger.info("Received request for pace calculation.")

    try:
        data = json.loads(request.body)
        vdot_val = data.get("vdot_score")
        intensity_zone = data.get("intensity_zone")
        distance_val = data.get("target_distance_meters")

        # Check for missing keys
        if vdot_val is None or intensity_zone is None or distance_val is None:
            logger.warning("Request was missing a required key for pace calculation.")
            return JsonResponse(
                {"error": "Request must contain 'vdot_score', 'intensity_zone', and 'target_distance_meters'."},
                status=400)

        vdot = float(vdot_val)
        distance = float(distance_val)
        logger.debug(f"Request data: vdot={vdot}, zone={intensity_zone}, distance={distance}")

    except (json.JSONDecodeError, ValueError):
        logger.warning("Invalid JSON or non-numeric values in request.")
        return JsonResponse({"error": "Invalid JSON or non-numeric values for vdot/distance."}, status=400)

    if intensity_zone not in TRAINING_ZONES:
        logger.warning(f"Invalid intensity zone requested: {intensity_zone}")
        return JsonResponse({"error": f"Invalid intensity_zone. Must be one of: {list(TRAINING_ZONES.keys())}"},
                            status=400)

    intensity_percent = TRAINING_ZONES[intensity_zone]["max"]
    pace_data = calculate_pace_from_vdot(vdot, intensity_percent, distance)

    if pace_data is None:
        logger.error("Pace calculation failed in the utility function.")
        return JsonResponse({"error": "Pace calculation failed. Check your inputs."}, status=500)

    response_data = {
        "vdot_score": vdot,
        "intensity_zone": intensity_zone,
        "target_distance_meters": distance,
        "calculated_pace": pace_data
    }
    logger.info(f"Successfully calculated pace for VDOT {vdot}.")
    return JsonResponse(response_data, status=200)

def vdot_calculator_page(request):
    """
    This view renders the main VDOT calculator page.
    """
    return render(request, 'workouts/vdot_form.html')

