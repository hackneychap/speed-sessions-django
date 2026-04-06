from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from .models import MerchItem, Order, OrderItem, MerchImage
from .forms import OrderForm, MerchItemForm
from django.contrib import messages
from communities.models import Community
from django.contrib.auth.decorators import login_required

def add_to_cart_view(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        size = request.POST.get('size')
        color = request.POST.get('color')
        cart = request.session.get('cart', [])
        cart.append({'item_id': item_id, 'size': size, 'color': color})
        request.session['cart'] = cart
        referer = request.META.get('HTTP_REFERER', 'home')
        return redirect(referer)
    return redirect('home')

def checkout_view(request):
    cart = request.session.get('cart', [])
    items = []
    total_price = 0
    
    for item_data in cart:
        try:
            item = MerchItem.objects.get(id=item_data['item_id'])
            items.append({'item': item, 'size': item_data['size'], 'color': item_data['color']})
            total_price += item.price
        except MerchItem.DoesNotExist:
            continue
        
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.base_cost = total_price
            order.status = 'PENDING_INVOICE'
            order.save()
            
            for entry in items:
                OrderItem.objects.create(
                    order=order,
                    item=entry['item'],
                    size=entry['size'],
                    color=entry['color'],
                    price_at_order=entry['item'].price
                )
                
            request.session['cart'] = []
            
            # Return HTMX partial
            return HttpResponse("<div class='p-6 bg-green-900/40 border border-green-800 rounded text-green-200'>Thank you! Your order has been pooled. You will receive an invoice in about two weeks.</div>")
        else:
            # Handle invalid form (return form with errors)
            return render(request, 'merch/checkout.html', {'form': form, 'items': items, 'total_price': total_price})
            
    form = OrderForm()
    return render(request, 'merch/checkout.html', {'form': form, 'items': items, 'total_price': total_price})

@login_required
def add_merch_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if community.manager != request.user:
        return redirect('community-detail', slug=slug)

    if request.method == 'POST':
        form = MerchItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.community = community
            item.save()
            
            images = request.FILES.getlist('images')
            for img in images:
                MerchImage.objects.create(item=item, image=img)
            
            messages.success(request, "Merchandise item added successfully.")
            return redirect('community-detail', slug=slug)
    else:
        form = MerchItemForm()
    
    return render(request, 'merch/add_merch.html', {'form': form, 'community': community})
