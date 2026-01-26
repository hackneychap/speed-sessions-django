from django.shortcuts import render
from django.http import QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from workouts.utils import calculate_vdot, calculate_pace_from_vdot, calculate_tss, TRAINING_ZONES
import logging

logger = logging.getLogger(__name__)


def _process_and_calculate_group_plan(post_data):
    """
    Helper function to process form data for a single group.
    Supports nested Repeat Blocks by reconstructing the hierarchy using 'item_type' markers.
    """
    group_name = post_data.get('group_name')
    group_vdot = float(post_data.get('group_vdot', 0))

    # 1. RECONSTRUCT THE WORKOUT HIERARCHY
    # We use 'item_type' as a breadcrumb trail to know when blocks start/end
    item_types = post_data.getlist('item_type')
    reps_list = post_data.getlist('reps')
    distances_list = post_data.getlist('distance')
    intensities_list = post_data.getlist('intensity')
    rests_list = post_data.getlist('rest')
    block_multipliers = post_data.getlist('block_multiplier')

    structured_workout = []
    seg_idx = 0
    block_idx = 0
    current_block = None

    for item in item_types:
        if item == 'block_start':
            current_block = {
                'type': 'block',
                'multiplier': int(block_multipliers[block_idx] if block_multipliers[block_idx] else 1),
                'segments': []
            }
            block_idx += 1
        elif item == 'block_end':
            structured_workout.append(current_block)
            current_block = None
        elif item == 'segment':
            segment = {
                'reps': int(reps_list[seg_idx] if reps_list[seg_idx] else 1),
                'distance': int(float(distances_list[seg_idx] if distances_list[seg_idx] else 400)),  # Cast to int here
                'intensity': intensities_list[seg_idx],
                'rest': int(rests_list[seg_idx] if rests_list[seg_idx] else 0)
            }
            if current_block:
                current_block['segments'].append(segment)
            else:
                structured_workout.append({'type': 'single', 'segment': segment})
            seg_idx += 1

    # 2. CALCULATION LOGIC
    final_flat_segments = []  # Used for TSS and Totals
    display_structure = []  # Used for rendering the Canvas card

    total_active_dist_m = 0
    total_active_time_s = 0
    total_rest_time_s = 0

    def process_segment(seg, block_multiplier=1):
        nonlocal total_active_dist_m, total_active_time_s

        pace_data = calculate_pace_from_vdot(group_vdot, TRAINING_ZONES[seg['intensity']]['max'], seg['distance'])
        if not pace_data:
            return None

        # Calculate 400m lap time
        pace_per_km_s = pace_data['pace_per_km']['minutes'] * 60 + pace_data['pace_per_km']['seconds']
        lap_time_s = pace_per_km_s * 0.4
        lap_fmt = f"{int(lap_time_s // 60)}:{lap_time_s % 60:05.2f}"

        target_pace_fmt = f"{pace_data['target_pace']['minutes']}:{pace_data['target_pace']['seconds']:05.2f}"

        # Totals calculation
        pace_s = pace_data['target_pace']['minutes'] * 60 + pace_data['target_pace']['seconds']
        effective_reps = seg['reps'] * block_multiplier
        total_active_dist_m += seg['distance'] * effective_reps
        total_active_time_s += pace_s * effective_reps

        segment_data = {
            **seg,
            'target_pace': target_pace_fmt,
            'lap_time': lap_fmt,
        }

        # Flatten for TSS (TSS needs total reps across all sets)
        final_flat_segments.append({**segment_data, 'reps': effective_reps})
        return segment_data

    # Process structured workout into calc data
    for item in structured_workout:
        if item['type'] == 'single':
            calc_seg = process_segment(item['segment'])
            if calc_seg:
                display_structure.append({'type': 'single', 'segment': calc_seg})
        elif item['type'] == 'block':
            calc_block_segs = []
            for s in item['segments']:
                calc_seg = process_segment(s, block_multiplier=item['multiplier'])
                if calc_seg:
                    calc_block_segs.append(calc_seg)
            display_structure.append({
                'type': 'block',
                'multiplier': item['multiplier'],
                'segments': calc_block_segs
            })

    # 3. RE-CALCULATE REST TIME
    num_segs = len(final_flat_segments)
    for i, seg in enumerate(final_flat_segments):
        reps = int(seg['reps'])
        rest = int(seg['rest'])
        if reps > 1:
            total_rest_time_s += (reps - 1) * rest
        if i < num_segs - 1:
            total_rest_time_s += rest

    total_time_s = total_active_time_s + total_rest_time_s

    # 4. PREPARE RESULTS
    return {
        'name': group_name,
        'vdot': round(group_vdot, 2),
        'workout_structure': display_structure,
        'summary': {
            'distance': f"{total_active_dist_m / 1000:.2f} km",
            'active_time': f"{int(total_active_time_s // 60)}:{int(total_active_time_s % 60):02d}",
            'total_time': f"{int(total_time_s // 60)}:{int(total_time_s % 60):02d}",
            'tss': round(calculate_tss(group_vdot, final_flat_segments)) if group_vdot > 0 else 0,
            "raw_distance_km": float(total_active_dist_m / 1000),
            "raw_total_time_min": float(total_time_s / 60),
        }
    }


def planner_page_view(request):
    return render(request, 'session_planner/planner_form.html')


def add_workout_segment(request):
    return render(request, 'session_planner/partials/_workout_segment.html')


def add_repeat_block(request):
    return render(request, 'session_planner/partials/_repeat_block.html')


@csrf_exempt
@require_http_methods(["POST"])
def generate_plan_view(request):
    """Initial generation for all groups"""
    item_types = request.POST.getlist('item_type')
    reps_list = request.POST.getlist('reps')
    distances_list = request.POST.getlist('distance')
    intensities_list = request.POST.getlist('intensity')
    rests_list = request.POST.getlist('rest')
    block_multipliers = request.POST.getlist('block_multiplier')

    groups_data = []
    for char in ['a', 'b', 'c']:
        name = request.POST.get(f'group_{char}_name')
        metric = request.POST.get(f'group_{char}_metric')
        val = request.POST.get(f'group_{char}_value')

        if name and val:
            vdot = 0
            if metric == 'vdot':
                try:
                    vdot = float(val)
                except:
                    continue
            else:
                try:
                    p = [int(x) for x in val.split(':')]
                    m = p[0] + p[1] / 60 if len(p) == 2 else p[0] * 60 + p[1] + p[2] / 60
                    vdot_res = calculate_vdot(5000, m)
                    vdot = vdot_res['vdot_score'] if isinstance(vdot_res, dict) else vdot_res
                except:
                    continue

            # Construct QueryDict for helper
            gd = QueryDict(mutable=True)
            gd['group_name'] = name
            gd['group_vdot'] = vdot
            gd.setlist('item_type', item_types)
            gd.setlist('reps', reps_list)
            gd.setlist('distance', distances_list)
            gd.setlist('intensity', intensities_list)
            gd.setlist('rest', rests_list)
            gd.setlist('block_multiplier', block_multipliers)

            groups_data.append(_process_and_calculate_group_plan(gd))

    return render(request, 'session_planner/partials/_differentiated_plan_results.html', {'groups': groups_data})


@csrf_exempt
@require_http_methods(["POST"])
def recalculate_group_plan_view(request):
    """HTMX update for a single card"""
    processed_group_data = _process_and_calculate_group_plan(request.POST)
    counter = int(request.POST.get('forloop_counter', 1))
    return render(request, 'session_planner/partials/_group_card.html', {
        'group': processed_group_data,
        'forloop': {'counter': counter}
    })