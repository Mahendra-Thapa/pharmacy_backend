from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('POS', 'POS Agent'),
        ('USER', 'Customer'),
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='USER')
    phone = models.CharField(max_length=20, blank=True, null=True)

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = (
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('OTHER', 'Other'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=100)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='HOME')
    address_line = models.TextField()
    city = models.CharField(max_length=100, blank=True, default='')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.label} - {self.user.username}"

class DeliveryOption(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    base_charge = models.IntegerField(default=0)
    per_km_charge = models.IntegerField(default=0)
    estimated_days = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', null=True, blank=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    image_url = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

class Medicine(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='medicines')
    manufacturer = models.CharField(max_length=255)
    price = models.IntegerField()
    stock = models.IntegerField(default=0)
    expiry_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    uses = models.TextField(blank=True, null=True) # AI service uses this
    side_effects = models.TextField(blank=True, null=True) # AI service uses this
    reorder_level = models.IntegerField(default=10)
    predicted_demand = models.IntegerField(null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    ai_alert_sent = models.BooleanField(default=False)


    def __str__(self):
        return self.name

def generate_order_number():
    """Generate a unique order number like ORD-XXXXXXXX"""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"

class Sale(models.Model):
    ORDER_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('READY', 'Ready for Pickup/Delivery'),
        ('DISPATCHED', 'Dispatched'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )
    order_number = models.CharField(max_length=20, unique=True, default=generate_order_number, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='sales')
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_processed')
    total_amount = models.IntegerField(default=0)
    delivery_option = models.ForeignKey(DeliveryOption, on_delete=models.SET_NULL, null=True, blank=True)
    delivery_charge = models.IntegerField(default=0)
    distance_km = models.IntegerField(default=0)
    date_added = models.DateTimeField(default=timezone.now)
    # Order Status tracking
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')
    status_changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_changes')
    status_changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_number} on {self.date_added.strftime('%Y-%m-%d')}"

class OrderStatusHistory(models.Model):
    """Track every status change for audit log"""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"Order {self.sale.order_number}: {self.old_status} -> {self.new_status}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.IntegerField() # Price at the time of sale
    total = models.IntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.medicine.name} for Sale {self.sale.id}"

class PaymentTransaction(models.Model):
    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('COD', 'Cash on Delivery'),
        ('QR', 'QR Code / Digital Wallet'),
        ('CARD', 'Card'),
    )
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='payment')
    amount = models.IntegerField()
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='CASH')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='COMPLETED') # e.g., PENDING, COMPLETED
    payment_screenshot = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Sale {self.sale.id} via {self.method}"

class PharmacySettings(models.Model):
    name = models.CharField(max_length=255, default='HealKart')
    qr_code_url = models.TextField(blank=True, null=True)
    admin_contact = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.name
