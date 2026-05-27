from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, Category, Medicine, Sale, SaleItem, PaymentTransaction, DeliveryOption, PharmacySettings, OrderStatusHistory, Address
import uuid

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'role', 'first_name', 'last_name', 'is_active')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'phone', 'password', 'role', 'first_name', 'last_name')

    def create(self, validated_data):
        # Default new registrations to Customer unless stated otherwise, or perhaps Pharmacist.
        role = validated_data.get('role', 'USER') 
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            phone=validated_data.get('phone', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=role
        )
        return user

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('id', 'label', 'address_type', 'address_line', 'city', 'is_default', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOption
        fields = '__all__'

class MedicineSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Medicine
        fields = '__all__'

class SaleItemSerializer(serializers.ModelSerializer):
    medicine_name = serializers.ReadOnlyField(source='medicine.name')

    class Meta:
        model = SaleItem
        fields = ('id', 'medicine', 'medicine_name', 'quantity', 'price', 'total')

class PaymentTransactionSerializer(serializers.ModelSerializer):
    qr_payment_url = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = ('id', 'amount', 'method', 'status', 'transaction_id', 'timestamp', 'qr_payment_url')

    def get_qr_payment_url(self, obj):
        if obj.method == 'QR':
            # In a real app, this would be an API call to a provider (eSewa/Fonepay)
            # Generating a dummy URL containing the transaction details for testing
            mock_tx_id = obj.transaction_id or uuid.uuid4().hex[:8]
            # e.g. "pay://gateway?amt=100&id=12345"
            return f"pay://mock-gateway?amt={obj.amount}&tx={mock_tx_id}"
        return None

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.ReadOnlyField(source='changed_by.username')
    changed_by_role = serializers.ReadOnlyField(source='changed_by.role')
    changed_by_name = serializers.SerializerMethodField()

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return f"{obj.changed_by.first_name} {obj.changed_by.last_name}".strip() or obj.changed_by.username
        return "System"

    class Meta:
        model = OrderStatusHistory
        fields = ('id', 'old_status', 'new_status', 'changed_by_username', 'changed_by_role', 'changed_by_name', 'changed_at', 'note')

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payment = PaymentTransactionSerializer(read_only=True)
    customer_name = serializers.SerializerMethodField()
    handled_by_name = serializers.ReadOnlyField(source='handled_by.username')
    status_changed_by_name = serializers.SerializerMethodField()
    status_changed_by_role = serializers.ReadOnlyField(source='status_changed_by.role')
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    def get_customer_name(self, obj):
        return obj.customer.name if obj.customer else "Walk-in Customer"

    def get_status_changed_by_name(self, obj):
        if obj.status_changed_by:
            return f"{obj.status_changed_by.first_name} {obj.status_changed_by.last_name}".strip() or obj.status_changed_by.username
        return None

    class Meta:
        model = Sale
        fields = (
            'id', 'order_number', 'customer', 'customer_name', 
            'handled_by', 'handled_by_name', 'total_amount', 'date_added', 
            'items', 'payment', 'delivery_option', 'delivery_charge', 'distance_km',
            'status', 'status_changed_by', 'status_changed_by_name', 
            'status_changed_by_role', 'status_changed_at', 'status_history'
        )

class PharmacySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacySettings
        fields = '__all__'
