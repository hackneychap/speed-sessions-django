# workouts/urls.py

from django.urls import path
from .views import calculate_vdot_view, calculate_pace_view,vdot_calculator_page

urlpatterns = [
    # This defines the URL for our view.
    # e.g., http://127.0.0.1:8000/api/calculate-vdot/
    path('calculator/', vdot_calculator_page, name='vdot-calculator-page'),

    path('calculate-vdot/', calculate_vdot_view, name='calculate-vdot'),
    path('calculate-pace/', calculate_pace_view, name='calculate-pace'),
]
