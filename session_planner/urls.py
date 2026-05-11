from django.urls import path
from .views import (
    edit_training_block_view,
    generate_plan_view, 
    planner_page_view, 
    add_workout_segment, 
    recalculate_group_plan_view, 
    add_repeat_block,
    save_workout_view,
    session_list_view,
    session_detail_view,
    session_edit_view,
    block_list_view,
    create_training_block_view,
    get_schedule_form_view,
    apply_block_to_calendar_view,
    copy_training_block_view
)


urlpatterns = [
    path('', planner_page_view, name='planner-page'),
    path('generate-plan/', generate_plan_view, name='generate-plan'),
    path('add-workout-segment/', add_workout_segment, name='add-workout-segment'),
    path('recalculate-plan/', recalculate_group_plan_view, name='recalculate-plan'),
    path('add-repeat-block/', add_repeat_block, name='add-repeat-block'),
    path('save-workout/', save_workout_view, name='save-workout'),
    path('sessions/', session_list_view, name='session-list'),
    path('sessions/<int:pk>/', session_detail_view, name='session-detail'),
    path('sessions/<int:pk>/edit/', session_edit_view, name='edit-session'),
    
    # Training Blocks
    path('blocks/', block_list_view, name='block-list'),
    path('blocks/create/', create_training_block_view, name='create-block'),
    path('blocks/<int:block_id>/edit/', edit_training_block_view, name='edit-block'),
    path('blocks/<int:block_id>/schedule/', get_schedule_form_view, name='get-schedule-form'),
    path('blocks/apply/', apply_block_to_calendar_view, name='apply-block-to-calendar'),
    path('blocks/<int:block_id>/copy/', copy_training_block_view, name='copy-block'),
]
