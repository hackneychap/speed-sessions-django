from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Community, CommunityImage
from .forms import CommunityForm
from merch.models import MerchItem

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
        
    is_manager = (request.user == community.manager)
    return render(request, 'communities/community_detail.html', {
        'community': community,
        'merch_items': merch_items,
        'is_manager': is_manager
    })

@login_required
def community_edit_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if request.user != community.manager:
        return redirect('community-detail', slug=slug)
        
    all_merch = community.merch_items.all()

    if request.method == 'POST':
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
        'all_merch': all_merch
    })
