from django.shortcuts import render

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Import your VDOT calculation function
from workouts.utils  import calculate_vdot, calculate_pace_from_vdot, TRAINING_ZONES, calculate_tss
logger = logging.getLogger(__name__)
# Create your views here.
# Add this new view to your existing views.py file

def planner_page_view(request):
    """
    This view renders the main session planner page.
    """
    # This view doesn't need any context, it just displays the form.
    return render(request, 'session_planner/planner_form.html')


@csrf_exempt
@require_http_methods(["POST"])
def differentiated_plan_view(request):
    """
    Receives workout and group data from the planner form, calculates
    all paces, and returns a rendered HTML fragment with the full plan.
    """
    logger.info("Received request for differentiated plan.")

    # 1. PARSE THE WORKOUT SEGMENTS
    workout_segments = []
    reps_list = request.POST.getlist('reps')
    distances_list = request.POST.getlist('distance')
    intensities_list = request.POST.getlist('intensity')
    rests_list = request.POST.getlist('rest')

    for i in range(len(reps_list)):
        if reps_list[i] and distances_list[i]:
            segment = {
                "reps": reps_list[i],
                "distance": distances_list[i],
                "intensity": intensities_list[i],
                "rest": rests_list[i]
            }
            workout_segments.append(segment)

    # 2. PARSE THE TRAINING GROUPS
    groups = []
    for group_char in ['a', 'b', 'c']:
        name = request.POST.get(f'group_{group_char}_name')
        metric = request.POST.get(f'group_{group_char}_metric')
        value = request.POST.get(f'group_{group_char}_value')

        if name and value:
            group_vdot = 0
            if metric == 'vdot':
                group_vdot = float(value)
            elif metric == '5k_time':
                try:
                    time_parts = [int(p) for p in value.split(':')]
                    time_min = 0
                    if len(time_parts) == 2:  # MM:SS
                        time_min = time_parts[0] + time_parts[1] / 60

                    vdot_result = calculate_vdot(5000, time_min)
                    if vdot_result:
                        group_vdot = vdot_result['vdot_score']
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse 5k time: {value}")
                    group_vdot = 0

            # 3. CALCULATE PACES FOR EACH SEGMENT FOR THIS GROUP
            calculated_segments = []
            if group_vdot > 0:
                for segment in workout_segments:
                    intensity_percent = TRAINING_ZONES[segment['intensity']]['max']
                    distance_meters = float(segment['distance'])

                    pace_data = calculate_pace_from_vdot(group_vdot, intensity_percent, distance_meters)

                    if pace_data:
                        calculated_segments.append({
                            "reps": segment['reps'],
                            "distance": segment['distance'],
                            "rest": segment['rest'],
                            "target_pace": f"{pace_data['target_pace']['minutes']}:{pace_data['target_pace']['seconds']:05.2f}"
                        })

            # 4. CALCULATE WORKOUT TOTALS FOR THE GROUP
            total_active_dist_m = 0
            total_active_time_s = 0
            total_rest_time_s = 0

            for seg in calculated_segments:
                reps = int(seg['reps'])
                dist_m = int(seg['distance'])
                rest_s = int(seg['rest'])

                total_active_dist_m += reps * dist_m

                pace_parts = seg['target_pace'].split(':')
                time_per_rep_s = (int(pace_parts[0]) * 60) + float(pace_parts[1])
                total_active_time_s += reps * time_per_rep_s

                if reps > 1:
                    total_rest_time_s += (reps - 1) * rest_s

            total_time_inc_rest_s = total_active_time_s + total_rest_time_s

            # Calculate the TSS for the workout
            tss_score = calculate_tss(group_vdot, workout_segments)
            logger.info(f"Calculated TSS for group {name}: {tss_score}")

            def format_seconds(seconds):
                mins, secs = divmod(int(seconds), 60)
                return f"{mins:02d}:{secs:02d}"

            groups.append({
                "name": name,
                "vdot": round(group_vdot, 2),
                "workout": calculated_segments,
                "summary": {
                    "distance": f"{total_active_dist_m / 1000:.2f} km",
                    "active_time": format_seconds(total_active_time_s),
                    "total_time": format_seconds(total_time_inc_rest_s),
                    "tss": tss_score  # Add the TSS score to the summary
                }
            })

    # 5. RENDER THE RESULTS TEMPLATE
    context = {"groups": groups}
    return render(request, 'session_planner/partials/_differentiated_plan_results.html', context)

def add_workout_segment(request):
    """
    This view returns an HTML fragment for a new, empty workout segment row.
    It's called by HTMX when the user clicks the '+ Add Segment' button.
    """
    return render(request, 'session_planner/partials/_workout_segment.html')