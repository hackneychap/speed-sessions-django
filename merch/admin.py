from django.contrib import admin
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django import forms
from .models import MerchItem, Order, OrderItem, MerchImage
import stripe
from django.conf import settings
from djstripe.models import Customer

stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

class ShippingCostForm(forms.Form):
    estimated_total_shipping_cost = forms.DecimalField(max_digits=10, decimal_places=2)

class MerchImageInline(admin.TabularInline):
    model = MerchImage
    extra = 1

@admin.register(MerchItem)
class MerchItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'community', 'price')
    list_filter = ('community',)
    inlines = [MerchImageInline]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_email', 'base_cost', 'split_shipping_cost', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'customer_email', 'stripe_invoice_id')
    actions = ['generate_draft_invoices']

    def generate_draft_invoices(self, request, queryset):
        if 'apply' in request.POST:
            form = ShippingCostForm(request.POST)
            if form.is_valid():
                total_shipping = form.cleaned_data['estimated_total_shipping_cost']
                count = queryset.count()
                split_shipping = total_shipping / count

                for order in queryset:
                    customer_data = stripe.Customer.create(
                        email=order.customer_email,
                        name=order.customer_name,
                    )
                    stripe_customer_id = customer_data.id

                    stripe.InvoiceItem.create(
                        customer=stripe_customer_id,
                        amount=int(order.base_cost * 100),
                        currency="usd",
                        description=f"Merchandise for Order #{order.id}"
                    )
                    stripe.InvoiceItem.create(
                        customer=stripe_customer_id,
                        amount=int(split_shipping * 100),
                        currency="usd",
                        description="Split Batch Shipping"
                    )

                    invoice = stripe.Invoice.create(
                        customer=stripe_customer_id,
                        auto_advance=False,
                        collection_method="send_invoice",
                        days_until_due=7,
                    )

                    order.split_shipping_cost = split_shipping
                    order.stripe_invoice_id = invoice.id
                    order.status = 'DRAFT_GENERATED'
                    order.save()

                self.message_user(request, f"Generated {count} draft invoices with ${split_shipping} shipping each.")
                return HttpResponseRedirect(request.get_full_path())
        else:
            form = ShippingCostForm()

        return render(request, 'admin/merch/shipping_cost_form.html', {
            'orders': queryset,
            'form': form,
            'title': 'Generate Draft Invoices'
        })

    generate_draft_invoices.short_description = "Generate Draft Invoices for selected orders"

admin.site.register(OrderItem)
admin.site.register(MerchImage)
