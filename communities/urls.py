from django.urls import path
from .views import community_list_view, community_detail_view, community_edit_view

urlpatterns = [
    path('', community_list_view, name='community-list'),
    path('<slug:slug>/', community_detail_view, name='community-detail'),
    path('<slug:slug>/edit/', community_edit_view, name='community-edit'),
]
