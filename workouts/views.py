from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django import forms
import json
import logging

from communities.models import Community
from .utils import calculate_vdot, calculate_pace_from_vdot, TRAINING_ZONES

logger = logging.getLogger(__name__)

# --- VDOT/Pace Views ---

@csrf_exempt
@require_http_methods(["POST"])
def calculate_vdot_view(request):
    logger.info("Received request for VDOT calculation.")
    try:
        distance_val = request.POST.get("distance_meters")
        time_val = request.POST.get("time_minutes")
        if distance_val is None or time_val is None:
            return JsonResponse({"error": "Request must contain 'distance_meters' and 'time_minutes'."}, status=400)
        distance = float(distance_val)
        time = float(time_val)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid non-numeric values."}, status=400)

    vdot_data = calculate_vdot(distance, time)
    if vdot_data is None:
        return JsonResponse({"error": "Calculation failed."}, status=400)
    return render(request, 'workouts/_vdot_results.html', vdot_data)

@csrf_exempt
@require_http_methods(["POST"])
def calculate_pace_view(request):
    logger.info("Received request for pace calculation.")
    try:
        data = json.loads(request.body)
        vdot = float(data.get("vdot_score"))
        intensity_zone = data.get("intensity_zone")
        distance = float(data.get("target_distance_meters"))
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"error": "Invalid input."}, status=400)

    if intensity_zone not in TRAINING_ZONES:
        return JsonResponse({"error": "Invalid intensity zone."}, status=400)

    pace_data = calculate_pace_from_vdot(vdot, TRAINING_ZONES[intensity_zone]["max"], distance)
    return JsonResponse({
        "vdot_score": vdot,
        "intensity_zone": intensity_zone,
        "target_distance_meters": distance,
        "calculated_pace": pace_data
    }, status=200)

def vdot_calculator_page(request):
    return render(request, 'workouts/vdot_form.html')

# --- Home & Auth Views ---

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

def home_view(request):
    if request.user.is_authenticated:
        return redirect('session-list')
    return render(request, 'home.html')

def signup_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        community_name = request.POST.get('community_name')
        community_id = request.POST.get('community_id')
        if form.is_valid():
            user = form.save()
            if community_id:
                community = Community.objects.get(id=community_id)
                user.profile.community = community
            elif community_name:
                community = Community.objects.create(name=community_name, manager=user)
                user.profile.community = community
            user.profile.save()
            login(request, user)
            return redirect('session-list')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/signup.html', {
        'form': form,
        'communities': Community.objects.all()
    })

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = UserChangeForm(instance=request.user)
    return render(request, 'registration/profile.html', {'form': form})
