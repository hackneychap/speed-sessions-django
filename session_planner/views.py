from django.shortcuts import render

import json
import logging
from django.http import JsonResponse,QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Import your VDOT calculation function
from workouts.utils  import calculate_vdot, calculate_pace_from_vdot, TRAINING_ZONES, calculate_tss
logger = logging.getLogger(__name__)
# Create your views here.
# Add this new view to your existing views.py file

def _process_and_calculate_group_plan(post_data):
    """
    Helper function to process form data for a single group, calculate all paces,
    totals, and TSS, and return a dictionary of the results.
    This can be used by both the initial generation and recalculation views.
    """
    # 1. PARSE GROUP AND WORKOUT DATA FROM THE POST REQUEST
    group_name = post_data.get('group_name')
    group_vdot = float(post_data.get('group_vdot', 0))

    workout_segments = []
    reps_list = post_data.getlist('reps')
    distances_list = post_data.getlist('distance')
    intensities_list = post_data.getlist('intensity')
    rests_list = post_data.getlist('rest')

    for i in range(len(reps_list)):
        if reps_list[i] and distances_list[i]:
            workout_segments.append({
                "reps": reps_list[i],
                "distance": distances_list[i],
                "intensity": intensities_list[i],
                "rest": rests_list[i]
            })

    # 2. RECALCULATE PACES FOR EACH SEGMENT
    calculated_segments = []
    if group_vdot > 0:
        for segment in workout_segments:
            intensity_percent = TRAINING_ZONES[segment['intensity']]['max']
            distance_meters = float(segment['distance'])
            pace_data = calculate_pace_from_vdot(group_vdot, intensity_percent, distance_meters)
            if pace_data:
                # Calculate 400m lap time from pace_per_km
                pace_per_km_seconds = pace_data['pace_per_km']['minutes'] * 60 + pace_data['pace_per_km']['seconds']
                time_for_400m_seconds = pace_per_km_seconds * 0.4
                lap_minutes = int(time_for_400m_seconds // 60)
                lap_seconds = time_for_400m_seconds % 60
                lap_time_formatted = f"{lap_minutes}:{lap_seconds:05.2f}"

                calculated_segments.append({
                    "reps": segment['reps'],
                    "distance": segment['distance'],
                    "rest": segment['rest'],
                    "intensity": segment['intensity'],
                    "target_pace": f"{pace_data['target_pace']['minutes']}:{pace_data['target_pace']['seconds']:05.2f}",
                    "lap_time": lap_time_formatted,
                })

        # 3. RECALCULATE TOTALS AND TSS
        total_active_dist_m, total_active_time_s, total_rest_time_s = 0, 0, 0

        num_segments = len(calculated_segments)
        for i, segment in enumerate(calculated_segments):
            reps = int(segment['reps'])
            distance = int(segment['distance'])
            rest = int(segment['rest'])

            pace_min, pace_sec = map(float, segment['target_pace'].split(':'))
            time_per_rep_s = (pace_min * 60) + pace_sec

            total_active_dist_m += reps * distance
            total_active_time_s += reps * time_per_rep_s

            # Calculate rest WITHIN the segment (e.g., for 10x400, this adds 9 rests)
            if reps > 1:
                total_rest_time_s += (reps - 1) * rest

            # Add the rest AFTER the segment, but ONLY if it's not the last segment
            is_last_segment = (i == num_segments - 1)
            if not is_last_segment:
                total_rest_time_s += rest

    total_time_s = total_active_time_s + total_rest_time_s

    active_time_formatted = f"{int(total_active_time_s // 60)}:{int(total_active_time_s % 60):02d}"
    total_time_formatted = f"{int(total_time_s // 60)}:{int(total_time_s % 60):02d}"
    distance_formatted = f"{total_active_dist_m / 1000:.2f} km"

    tss_score = calculate_tss(group_vdot, workout_segments)

    # 4. RETURN THE COMPLETE DICTIONARY FOR THE GROUP
    return {
        'name': group_name,
        'vdot': group_vdot,
        'workout': calculated_segments,
        'summary': {
            'distance': distance_formatted,
            'active_time': active_time_formatted,
            'total_time': total_time_formatted,
            'tss': round(tss_score),
        }
    }

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
    Receives the initial planner form, calculates the plan for all groups,
    and returns the initial results HTML.
    """
    logger.info("Generating initial differentiated plan.")

    # 1. Parse the shared workout segments from the main form submission
    reps_list = request.POST.getlist('reps')
    distances_list = request.POST.getlist('distance')
    intensities_list = request.POST.getlist('intensity')
    rests_list = request.POST.getlist('rest')

    groups_data = []
    # 2. Loop through each potential group
    for group_char in ['a', 'b', 'c']:
        name = request.POST.get(f'group_{group_char}_name')
        metric = request.POST.get(f'group_{group_char}_metric')
        value = request.POST.get(f'group_{group_char}_value')

        # Only process groups that have a name and a value
        if name and value:
            group_vdot = 0
            if metric == 'vdot':
                try:
                    group_vdot = float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid VDOT value for group {name}: {value}")
                    continue
            elif metric == '5k_time':
                try:
                    time_parts = [int(p) for p in value.split(':')]
                    time_min = 0
                    if len(time_parts) == 3:
                        time_min = time_parts[0] * 60 + time_parts[1] + time_parts[2] / 60
                    elif len(time_parts) == 2:
                        time_min = time_parts[0] + time_parts[1] / 60
                    else:
                        raise ValueError("Invalid time format")

                    vdot_result = calculate_vdot(5000, time_min)
                    if vdot_result:
                        group_vdot = vdot_result.get('vdot_score', 0)
                except (ValueError, IndexError, TypeError):
                    logger.warning(f"Invalid 5k time format for group {name}: {value}")
                    continue

            # 3. Construct a QueryDict for the helper function
            group_post_data = QueryDict(mutable=True)
            group_post_data['group_name'] = name
            group_post_data['group_vdot'] = group_vdot
            group_post_data.setlist('reps', reps_list)
            group_post_data.setlist('distance', distances_list)
            group_post_data.setlist('intensity', intensities_list)
            group_post_data.setlist('rest', rests_list)

            # 4. Call the refactored helper function
            processed_group = _process_and_calculate_group_plan(group_post_data)
            if processed_group:
                groups_data.append(processed_group)

    context = {"groups": groups_data}
    return render(request, 'session_planner/partials/_differentiated_plan_results.html', context)


def add_workout_segment(request):
    """
    This view returns an HTML fragment for a new, empty workout segment row.
    It's called by HTMX when the user clicks the '+ Add Segment' button.
    """
    return render(request, 'session_planner/partials/_workout_segment.html')

#TODO add recalc group plan views and then url here.




@csrf_exempt
@require_http_methods(["POST"])
def recalculate_group_plan_view(request):
    """
    Receives the data for a single group's workout, recalculates all
    totals and paces, and returns a single updated group card HTML fragment.
    """
    # This view now calls the helper function to do all the heavy lifting.
    processed_group_data = _process_and_calculate_group_plan(request.POST)

    forloop_counter = int(request.POST.get('forloop_counter', 1))

    context = {
        'forloop': {'counter': forloop_counter},
        'group': processed_group_data
    }

    return render(request, 'session_planner/partials/_group_card.html', context)