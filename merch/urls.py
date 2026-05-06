from django.urls import path
from .views import add_to_cart_view, checkout_view, add_merch_view, manage_orders_view, release_orders_view, user_orders_view, remove_from_cart_view, update_order_status_view

urlpatterns = [
    path('add-to-cart/', add_to_cart_view, name='add-to-cart'),
    path('checkout/', checkout_view, name='checkout'),
    path('community/<slug:slug>/add-merch/', add_merch_view, name='add-merch'),
    path('community/<slug:slug>/manage-orders/', manage_orders_view, name='manage-orders'),
    path('community/<slug:slug>/release-orders/', release_orders_view, name='release-orders'),
    path('my-orders/', user_orders_view, name='user-orders'),
    path('remove-from-cart/<int:index>/', remove_from_cart_view, name='remove-from-cart'),
    path('order/<int:order_id>/update-status/', update_order_status_view, name='update-order-status'),
]
