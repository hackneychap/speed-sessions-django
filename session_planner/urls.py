from django.urls import path
from .views import differentiated_plan_view,planner_page_view,add_workout_segment,recalculate_group_plan_view


urlpatterns = [
    path('', planner_page_view, name='planner-page'),
    path('generate-plan/',differentiated_plan_view,name='generate-plan' ),
    path('add-workout-segment/', add_workout_segment, name='add-workout-segment'),
    path('recalculate-plan/', recalculate_group_plan_view, name='recalculate-plan'),
]