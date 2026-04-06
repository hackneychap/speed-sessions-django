from django.db import models
from django.contrib.auth.models import User
from communities.models import Community

class MerchItem(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='merch_items')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_sizes = models.CharField(max_length=200, help_text="Comma separated sizes, e.g., S,M,L,XL")
    available_colors = models.CharField(max_length=200, help_text="Comma separated colors, e.g., Red,Blue,Black")
    is_listed = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.community.name}"

class MerchImage(models.Model):
    item = models.ForeignKey(MerchItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='merch_images/')
    
    def __str__(self):
        return f"Image for {self.item.name}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING_INVOICE', 'Pending Invoice Calculation'),
        ('DRAFT_GENERATED', 'Draft Invoice Generated'),
        ('PAID_AWAITING_PRINT', 'Paid - Awaiting Print'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='merch_orders')
    customer_name = models.CharField(max_length=255, default="Guest")
    customer_email = models.EmailField()
    shipping_address = models.TextField(default="")
    
    items = models.ManyToManyField(MerchItem, through='OrderItem')
    
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    split_shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING_INVOICE')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(MerchItem, on_delete=models.CASCADE)
    size = models.CharField(max_length=50)
    color = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
