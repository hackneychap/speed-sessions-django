from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
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

@require_POST
def remove_from_cart_view(request, index):
    """View to remove an item from the session cart by its index."""
    cart = request.session.get('cart', [])
    try:
        # Cast index to int and remove
        idx = int(index)
        if 0 <= idx < len(cart):
            cart.pop(idx)
            request.session['cart'] = cart
    except (ValueError, TypeError, IndexError):
        pass
        
    return redirect('checkout')

def checkout_view(request):
    cart = request.session.get('cart', [])
    items = []
    total_price = 0
    
    for item_data in cart:
        try:
            item = MerchItem.objects.get(id=item_data['item_id'])
            items.append({'item': item, 'size': item_data['size'], 'color': item_data['color']})
            total_price += item.price
        except (MerchItem.DoesNotExist, KeyError):
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
            
    initial_data = {}
    if request.user.is_authenticated:
        initial_data = {
            'customer_name': request.user.get_full_name() or request.user.username,
            'customer_email': request.user.email
        }
    form = OrderForm(initial=initial_data)
    return render(request, 'merch/checkout.html', {'form': form, 'items': items, 'total_price': total_price})

@login_required
def user_orders_view(request):
    """View to show the logged-in user's order history."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Define active vs past statuses
    active_statuses = ['PENDING_INVOICE', 'DRAFT_GENERATED', 'PAYMENT_FAILED']
    
    active_orders = orders.filter(status__in=active_statuses)
    past_orders = orders.exclude(status__in=active_statuses)
    
    return render(request, 'merch/user_orders.html', {
        'active_orders': active_orders,
        'past_orders': past_orders
    })

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

from django.db.models import Prefetch
from decimal import Decimal

@login_required
def manage_orders_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if community.manager != request.user:
        return HttpResponseForbidden("You are not the manager of this community.")
    
    # Get all unique orders that have items belonging to this community
    orders = Order.objects.filter(items__community=community).distinct().order_by('-created_at')
    
    # Separate into pending and released
    pending_orders = orders.filter(status='PENDING_INVOICE')
    released_orders = orders.exclude(status='PENDING_INVOICE')
    
    context = {
        'community': community,
        'pending_orders': pending_orders,
        'released_orders': released_orders,
    }
    return render(request, 'merch/manage_orders.html', context)

@login_required
@require_POST
def release_orders_view(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if community.manager != request.user:
        return HttpResponseForbidden("You are not the manager of this community.")
        
    shipping_cost_str = request.POST.get('shipping_cost', '0')
    try:
        total_shipping_cost = Decimal(shipping_cost_str)
    except:
        messages.error(request, "Invalid shipping cost.")
        return redirect('manage-orders', slug=slug)
        
    pending_orders = Order.objects.filter(items__community=community, status='PENDING_INVOICE').distinct()
    
    num_orders = pending_orders.count()
    if num_orders > 0:
        import stripe
        from django.conf import settings
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY
        
        split_cost = round(total_shipping_cost / num_orders, 2)
        released_count = 0
        
        for order in pending_orders:
            try:
                # 1. Ensure Stripe Customer exists
                customer_data = stripe.Customer.list(email=order.customer_email, limit=1).data
                if customer_data:
                    customer = customer_data[0]
                else:
                    customer = stripe.Customer.create(
                        email=order.customer_email,
                        name=order.customer_name,
                        description=f"Runner from {community.name}"
                    )

                # 2. Create Invoice Item for the Merch Base Cost
                stripe.InvoiceItem.create(
                    customer=customer.id,
                    amount=int(order.base_cost * 100), # Stripe uses pence/cents
                    currency="gbp",
                    description=f"Gear Order Base Cost (Order #{order.id})"
                )

                # 3. Create Invoice Item for the Shipping Split
                if split_cost > 0:
                    stripe.InvoiceItem.create(
                        customer=customer.id,
                        amount=int(split_cost * 100),
                        currency="gbp",
                        description=f"Shared Shipping/Delivery Share (Order #{order.id})"
                    )

                # 4. Create and Send the Invoice
                invoice = stripe.Invoice.create(
                    customer=customer.id,
                    auto_advance=True, # Automatically finalize and send
                    collection_method="send_invoice",
                    days_until_due=7
                )
                
                # 5. Update local record
                order.split_shipping_cost = split_cost
                order.status = 'DRAFT_GENERATED'
                order.stripe_invoice_id = invoice.id
                order.save()
                released_count += 1
                
            except stripe.error.StripeError as e:
                messages.error(request, f"Stripe error for {order.customer_email}: {str(e)}")
                continue

        if released_count > 0:
            messages.success(request, f"Successfully released {released_count} orders. Invoices have been sent via Stripe.")
    else:
        messages.info(request, "No pending orders to release.")
        
    return redirect('manage-orders', slug=slug)

@login_required
@require_POST
def update_order_status_view(request, order_id):
    """View for community managers to advance an order's fulfillment status."""
    order = get_object_or_404(Order, id=order_id)
    
    # Permission check: must be the manager of the community associated with items in this order
    # (Simplified: we check the first item's community manager)
    first_item = order.order_items.first()
    if not first_item or first_item.item.community.manager != request.user:
        return HttpResponseForbidden("You are not authorized to update this order.")
        
    new_status = request.POST.get('status')
    valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
    
    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        
        # Enqueue background email task (Django 6.0 Tasks API)
        from .tasks import send_order_status_email
        send_order_status_email.enqueue(order.id)
        
        messages.success(request, f"Order #{order.id} status updated to {order.get_status_display()}. Notification email enqueued.")
    else:
        messages.error(request, "Invalid status update.")
        
    return redirect('manage-orders', slug=first_item.item.community.slug)
