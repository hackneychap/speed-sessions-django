from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import QueryDict, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from workouts.utils import calculate_vdot, calculate_pace_from_vdot, calculate_tss, TRAINING_ZONES
import logging
import json
import calendar
from datetime import datetime, timedelta
from .models import Session, SessionGroup, TrainingBlock

logger = logging.getLogger(__name__)


@login_required
def block_list_view(request):
    """View to list all training blocks."""
    blocks = TrainingBlock.objects.all()
    return render(request, 'session_planner/block_list.html', {'blocks': blocks})

@login_required
def get_schedule_form_view(request, block_id):
    """HTMX view to return the scheduling form for a specific block."""
    block = get_object_or_404(TrainingBlock, id=block_id)
    return render(request, 'session_planner/partials/_schedule_form.html', {'block': block})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def apply_block_to_calendar_view(request):
    """View to apply a training block to the calendar by creating Session objects."""
    block_id = request.POST.get('block_id')
    start_date_str = request.POST.get('start_date')
    
    if not block_id or not start_date_str:
        return HttpResponse("Missing data", status=400)
    
    block = get_object_or_404(TrainingBlock, id=block_id)
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse("Invalid date format", status=400)
    
    community = request.user.profile.community
    if not community:
        return HttpResponse("User must belong to a community", status=400)
    
    templates = block.templates.all()
    sessions_created = 0
    
    for template in templates:
        # Calculate the date for this session
        # Week 1 is the start date, Week 2 is +7 days, etc.
        session_date = start_date + timedelta(days=(template.week_number - 1) * 7)
        
        Session.objects.create(
            title=template.title,
            date=session_date,
            community=community,
            creator=request.user,
            structure_json=template.structure_json
        )
        sessions_created += 1
    
    return HttpResponse(f'<div class="bg-green-900/40 border border-green-500 text-green-400 p-4 rounded-lg font-bold text-center uppercase tracking-widest text-xs">Successfully added {sessions_created} sessions to the calendar!</div>')

def _extract_workout_structure(post_data, prefix=''):
    """
    Helper to extract the raw structure from POST data for saving.
    Supports a prefix to distinguish between base and group-specific structures.
    """
    item_types = post_data.getlist(f'{prefix}item_type')
    reps_list = post_data.getlist(f'{prefix}reps')
    distances_list = post_data.getlist(f'{prefix}distance')
    intensities_list = post_data.getlist(f'{prefix}intensity')
    rests_list = post_data.getlist(f'{prefix}rest')
    block_multipliers = post_data.getlist(f'{prefix}block_multiplier')

    structure = []
    seg_idx = 0
    block_idx = 0
    current_block = None

    for item in item_types:
        if item == 'block_start':
            current_block = {
                'type': 'block',
                'multiplier': int(block_multipliers[block_idx] if block_idx < len(block_multipliers) and block_multipliers[block_idx] and block_multipliers[block_idx] != '' else 1),
                'segments': []
            }
            block_idx += 1
        elif item == 'block_end':
            if current_block:
                structure.append(current_block)
            current_block = None
        elif item == 'segment':
            try:
                reps = int(reps_list[seg_idx]) if seg_idx < len(reps_list) and reps_list[seg_idx] else 1
                dist = int(float(distances_list[seg_idx])) if seg_idx < len(distances_list) and distances_list[seg_idx] else 400
                intensity = intensities_list[seg_idx] if seg_idx < len(intensities_list) else 'Threshold'
                rest = int(rests_list[seg_idx]) if seg_idx < len(rests_list) and rests_list[seg_idx] else 0
            except (ValueError, IndexError):
                reps = 1
                dist = 400
                intensity = 'Threshold'
                rest = 0

            segment = {
                'reps': reps,
                'distance': dist,
                'intensity': intensity,
                'rest': rest
            }
            if current_block:
                current_block['segments'].append(segment)
            else:
                structure.append({'type': 'single', 'segment': segment})
            seg_idx += 1
    return structure


def _process_and_calculate_group_plan(group_name, group_vdot, structure, prefix=None):
    """
    Helper function to process a workout structure for a single group.
    """
    final_flat_segments = []  # Used for TSS and Totals
    display_structure = []  # Used for rendering the Canvas card

    total_active_dist_m = 0
    total_active_time_s = 0
    total_rest_time_s = 0

    def process_segment(seg, block_multiplier=1):
        nonlocal total_active_dist_m, total_active_time_s

        if seg['intensity'] not in TRAINING_ZONES:
             return None
             
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
    for item in structure:
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
    for seg in final_flat_segments:
        reps = int(seg['reps'])
        rest = int(seg['rest'])
        if reps > 1:
            total_rest_time_s += (reps - 1) * rest
            
    if len(final_flat_segments) > 1:
        for i in range(len(final_flat_segments) - 1):
            total_rest_time_s += int(final_flat_segments[i]['rest'])

    total_time_s = total_active_time_s + total_rest_time_s

    # 4. PREPARE RESULTS
    return {
        'name': group_name,
        'vdot': round(group_vdot, 2),
        'prefix': prefix,
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

@login_required
def planner_page_view(request):
    try:
        profile = request.user.profile
        if not profile.community:
            return redirect('home')
    except:
        return redirect('home')
    
    # Default data for a new workout
    groups_form_data = [
        {'char': 'a', 'name': 'Group A', 'vdot': ''},
        {'char': 'b', 'name': 'Group B', 'vdot': ''},
        {'char': 'c', 'name': 'Group C', 'vdot': ''},
    ]
    
    training_blocks = TrainingBlock.objects.filter(created_by=request.user)
    
    return render(request, 'session_planner/planner_form.html', {
        'groups_form_data': groups_form_data,
        'training_blocks': training_blocks
    })

@login_required
def session_edit_view(request, pk):
    """View to edit an existing session."""
    session = get_object_or_404(Session, pk=pk)
    
    # Verify user is community manager
    if not session.community or session.community.manager != request.user:
        return redirect('session-detail', pk=pk)
    
    # Prepare groups data for the form
    groups = session.groups.all().order_by('id')
    groups_form_data = []
    groups_results = []
    chars = ['a', 'b', 'c']
    
    structure = session.structure_json
    
    for i, group in enumerate(groups):
        if i < len(chars):
            groups_form_data.append({
                'char': chars[i],
                'name': group.name,
                'vdot': group.vdot
            })
            
            # Check if group has a specific structure, otherwise use session structure
            group_structure = group.structure_json if group.structure_json else structure
            
            # Calculate the differentiated plan for this group with prefix
            groups_results.append(_process_and_calculate_group_plan(
                group.name, group.vdot, group_structure, prefix=f'group_{chars[i]}_'
            ))
    
    # If session has fewer than 3 groups, fill the rest
    while len(groups_form_data) < 3:
        char = chars[len(groups_form_data)]
        groups_form_data.append({
            'char': char,
            'name': f'Group {char.upper()}',
            'vdot': ''
        })

    return render(request, 'session_planner/planner_form.html', {
        'session': session,
        'groups_form_data': groups_form_data,
        'groups_results': groups_results,
        'training_blocks': TrainingBlock.objects.filter(created_by=request.user)
    })

@login_required
def add_workout_segment(request):
    return render(request, 'session_planner/partials/_workout_segment.html')

@login_required
def add_repeat_block(request):
    return render(request, 'session_planner/partials/_repeat_block.html')

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def generate_plan_view(request):
    """Initial generation for all groups"""
    structure = _extract_workout_structure(request.POST)

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

            groups_data.append(_process_and_calculate_group_plan(name, vdot, structure, prefix=f'group_{char}_'))

    return render(request, 'session_planner/partials/_differentiated_plan_results.html', {'groups': groups_data})

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def recalculate_group_plan_view(request):
    """
    Recalculate a single group's plan based on changed inputs within the group card.
    """
    name = request.POST.get('group_name')
    vdot = float(request.POST.get('group_vdot', 0))
    forloop_counter = request.POST.get('forloop_counter')
    prefix = request.POST.get('group_prefix')
    
    # Extract structure using prefix if available
    structure = _extract_workout_structure(request.POST, prefix=prefix if prefix else '')
    group_data = _process_and_calculate_group_plan(name, vdot, structure, prefix=prefix)

    return render(request, 'session_planner/partials/_group_card.html', {
        'group': group_data,
        'forloop': {'counter': forloop_counter}
    })

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def save_workout_view(request):
    """Save or update the session and its groups"""
    try:
        community = request.user.profile.community
        if not community:
            return redirect('home')
    except:
        return redirect('home')

    session_id = request.POST.get('session_id')
    title = request.POST.get('title')
    date = request.POST.get('date')
    base_structure = _extract_workout_structure(request.POST)
    
    if session_id:
        # Update existing session
        session = get_object_or_404(Session, id=session_id)
        # Security check
        if session.community != community or session.community.manager != request.user:
            return HttpResponse("Unauthorized", status=403)
        
        session.title = title
        session.date = date
        session.structure_json = base_structure
        session.save()
        
        # Clear existing groups and recreate
        session.groups.all().delete()
    else:
        # Create new session
        session = Session.objects.create(
            title=title,
            date=date,
            structure_json=base_structure,
            community=community,
            creator=request.user
        )
    
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
            
            # Extract group-specific structure if it exists
            group_prefix = f'group_{char}_'
            group_structure = _extract_workout_structure(request.POST, prefix=group_prefix)
            
            # If group structure is empty (e.g., results container not included), fallback to base
            if not group_structure:
                group_structure = base_structure

            SessionGroup.objects.create(
                session=session,
                name=name,
                vdot=vdot,
                structure_json=group_structure 
            )

    # --- Save as Training Block Template ---
    if request.POST.get('save_as_template') == 'on':
        block_id = request.POST.get('block_id')
        week_num = request.POST.get('template_week_number')
        if block_id and week_num:
            block = get_object_or_404(TrainingBlock, id=block_id, created_by=request.user)
            from .models import BlockSessionTemplate
            BlockSessionTemplate.objects.update_or_create(
                block=block,
                week_number=week_num,
                defaults={
                    'title': title,
                    'structure_json': base_structure
                }
            )

    response = HttpResponse()
    response['HX-Redirect'] = reverse('session-detail', kwargs={'pk': session.id})
    return response

@login_required
def session_list_view(request):
    """View to list all sessions in a calendar format, filtered by community"""
    try:
        profile = request.user.profile
    except:
        return redirect('home')
        
    community = profile.community
    if not community:
        return redirect('home')

    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    cal = calendar.Calendar(firstweekday=0) # Monday start
    month_days = cal.monthdayscalendar(year, month)

    sessions = Session.objects.filter(community=community, date__year=year, date__month=month)
    sessions_by_day = {}
    for session in sessions:
        day = session.date.day
        if day not in sessions_by_day:
            sessions_by_day[day] = []
        sessions_by_day[day].append(session)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    month_name = calendar.month_name[month]

    return render(request, 'session_planner/session_list.html', {
        'sessions': sessions,
        'month_days': month_days,
        'year': year,
        'month': month,
        'month_name': month_name,
        'sessions_by_day': sessions_by_day,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': datetime.now().date(),
        'community': community
    })

@login_required
def session_detail_view(request, pk):
    """View to show a single session, ensuring it belongs to user's community."""
    try:
        community = request.user.profile.community
    except:
        return redirect('home')

    if not community:
        return redirect('home')
        
    session = get_object_or_404(Session, pk=pk, community=community)
    
    # Check if user is community manager for edit permissions
    is_manager = community.manager == request.user

    groups_data = []
    for group in session.groups.all():
        groups_data.append(_process_and_calculate_group_plan(group.name, group.vdot, group.get_structure()))
        
    return render(request, 'session_planner/session_detail.html', {
        'session': session,
        'groups': groups_data,
        'is_manager': is_manager
    })
