from django.urls import path
from .views import add_to_cart_view, checkout_view, add_merch_view

urlpatterns = [
    path('add-to-cart/', add_to_cart_view, name='add-to-cart'),
    path('checkout/', checkout_view, name='checkout'),
    path('community/<slug:slug>/add-merch/', add_merch_view, name='add-merch'),
]
