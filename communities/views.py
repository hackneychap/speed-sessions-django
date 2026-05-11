from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Community, CommunityImage, CalendarEvent
from .forms import CommunityForm, CalendarEventForm
from merch.models import MerchItem
from session_planner.models import Session

def community_list_view(request):
    communities = Community.objects.all()
    return render(request, 'communities/community_list.html', {'communities': communities})

@login_required
def community_detail_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    # Only show listed merch
    merch_items = community.merch_items.filter(is_listed=True)
    for item in merch_items:
        item.size_list = [s.strip() for s in item.available_sizes.split(',')]
        item.color_list = [c.strip() for c in item.available_colors.split(',')]
        
    is_manager = request.user in community.managers.all()
    
    # Get the next scheduled workout
    next_session = community.sessions.filter(date__gte=timezone.now().date()).order_by('date').first()
    
    # Get the next calendar event
    event_qs = community.calendar_events.filter(date__gte=timezone.now().date()).order_by('date')
    if not is_manager:
        event_qs = event_qs.filter(is_public=True)
    next_event = event_qs.first()
    
    # Check if visitor is a manager of *another* community
    is_visitor_manager = False
    if request.user.is_authenticated and not is_manager:
        is_visitor_manager = request.user.managed_communities_set.exclude(id=community.id).exists()

    tradeable_blocks = community.training_blocks.filter(is_tradeable=True)

    return render(request, 'communities/community_detail.html', {
        'community': community,
        'merch_items': merch_items,
        'is_manager': is_manager,
        'next_session': next_session,
        'next_event': next_event,
        'is_visitor_manager': is_visitor_manager,
        'tradeable_blocks': tradeable_blocks
    })

@login_required
def create_calendar_event_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if request.user not in community.managers.all():
        return redirect('community-detail', slug=slug)

    if request.method == 'POST':
        form = CalendarEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.community = community
            event.save()
            return redirect('session-list')
    else:
        # Pre-fill date if provided in GET
        initial = {}
        if 'date' in request.GET:
            initial['date'] = request.GET['date']
        form = CalendarEventForm(initial=initial)
    
    return render(request, 'communities/create_event.html', {'form': form, 'community': community})

@login_required
def community_edit_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if request.user not in community.managers.all():
        return redirect('community-detail', slug=slug)
        
    all_merch = community.merch_items.all()

    # Get all members with their users
    members = community.members.select_related('user').all()

    if request.method == 'POST':
        # 0. Handle member management
        promote_user_id = request.POST.get('promote_user')
        if promote_user_id:
            try:
                user_to_promote = members.get(user_id=promote_user_id).user
                community.managers.add(user_to_promote)
            except:
                pass

        demote_user_id = request.POST.get('demote_user')
        if demote_user_id:
            # Prevent a manager from demoting themselves
            if int(demote_user_id) != request.user.id:
                try:
                    user_to_demote = members.get(user_id=demote_user_id).user
                    community.managers.remove(user_to_demote)
                except:
                    pass

        # 1. Handle Merch unlisting
        listed_ids = request.POST.getlist('merch_listed')
        all_merch.update(is_listed=False)
        all_merch.filter(id__in=listed_ids).update(is_listed=True)

        # 2. Handle Community Details & Images
        form = CommunityForm(request.POST, request.FILES, instance=community)
        if form.is_valid():
            form.save()
            
            # Handle gallery images
            gallery_files = request.FILES.getlist('gallery_images')
            if gallery_files:
                # If new images are uploaded, we can either append or replace.
                # For simplicity, let's append until 5 limit.
                current_count = community.gallery_images.count()
                for img in gallery_files:
                    if current_count < 5:
                        CommunityImage.objects.create(community=community, image=img)
                        current_count += 1
            
            return redirect('community-detail', slug=slug)
    else:
        form = CommunityForm(instance=community)
        
    return render(request, 'communities/community_edit.html', {
        'community': community, 
        'form': form,
        'all_merch': all_merch,
        'members': members
    })
