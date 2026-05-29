from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
import uuid
from .models import Customer, Category, Medicine, Sale, SaleItem, PaymentTransaction, DeliveryOption, PharmacySettings, OrderStatusHistory, Address
from .serializers import (
    UserSerializer, UserRegistrationSerializer, CustomerSerializer, CategorySerializer,
    MedicineSerializer, SaleSerializer, PaymentTransactionSerializer, DeliveryOptionSerializer, 
    PharmacySettingsSerializer, OrderStatusHistorySerializer, AddressSerializer
)
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from .utils import send_stock_alert_email
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader
from datetime import timedelta

class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.data.get('file')
        if not file_obj:
            return Response({'error': 'No file part found'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Explicitly specifying folder for organized storage
            upload_data = cloudinary.uploader.upload(
                file_obj,
                folder="pharmacy_management_system",
                resource_type="auto"
            )
            
            return Response({
                'secure_url': upload_data.get('secure_url'),
                'public_id': upload_data.get('public_id'),
                'format': upload_data.get('format')
            }, status=status.HTTP_200_OK)
        except Exception as e:
            # Log exact error for debugging
            print(f"[Cloudinary Error]: {str(e)}")
            return Response({'error': f'Cloudinary upload failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        # Admin endpoint to change user role and is_active status
        if request.user.role != 'ADMIN':
            return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)
            
        user = self.get_object()
        new_role = request.data.get('role')
        new_status = request.data.get('is_active')
        
        if new_role and new_role in ['ADMIN', 'POS', 'USER']:
            user.role = new_role
        
        if new_status is not None:
            user.is_active = bool(new_status)
            
        user.save()
        return Response({'status': 'User status updated successfully', 'user': UserSerializer(user).data})

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
            
        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        # Profile/Password Update
        data = request.data
        if 'password' in data and data['password']:
            # Require current password for security
            current_password = data.get('current_password')
            if not current_password:
                return Response({'error': 'Current password is required to change password'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user.check_password(current_password):
                return Response({'error': 'Current password incorrect'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(data['password'])
            del data['password']
        
        serializer = UserSerializer(user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        from django.db.models import Q
        from django.contrib.auth import authenticate
        
        username_or_email = request.data.get('username')
        password = request.data.get('password')

        if not username_or_email or not password:
            return Response({'error': 'Credentials missing'}, status=status.HTTP_400_BAD_REQUEST)

        # Try searching by username or email
        user = User.objects.filter(Q(username=username_or_email) | Q(email=username_or_email)).first()

        if user:
            authenticated_user = authenticate(username=user.username, password=password)
            if authenticated_user:
                if not authenticated_user.is_active:
                    return Response({'error': 'Account deactivated'}, status=status.HTTP_403_FORBIDDEN)
                
                token, _ = Token.objects.get_or_create(user=authenticated_user)
                return Response({
                    'token': token.key,
                    'user': UserSerializer(authenticated_user).data
                })

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-created_at')
    serializer_class = CustomerSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer

    @action(detail=False, methods=['get'])
    def ai_analysis(self, request):
        # AI Logic: Predict demand and alert for low stock
        medicines = Medicine.objects.all()
        alerts = []
        for med in medicines:
            # Simple AI logic for demo: if stock < 2*avg_daily_sales (mocked)
            # In real case, we'd use a small regression model here
            if med.stock < med.reorder_level and not med.ai_alert_sent:
                email_sent = send_stock_alert_email(med.name, med.stock, med.reorder_level)
                med.ai_alert_sent = True
                med.save()
                alerts.append({
                    "id": med.id,
                    "name": med.name,
                    "stock": med.stock,
                    "reorder_level": med.reorder_level,
                    "email_sent": email_sent,
                    "message": f"Critical Stock Alert for {med.name}. Immediate restock recommended and email alert sent to admin."
                })
            elif med.stock >= med.reorder_level:
                med.ai_alert_sent = False
                med.save()
        
        # Mocking demand prediction
        for med in medicines:
            med.predicted_demand = med.stock + 50 # Mock prediction
            med.save()

        return Response({
            "alerts": alerts,
            "predictions": MedicineSerializer(medicines, many=True).data
        })

class DeliveryOptionViewSet(viewsets.ModelViewSet):
    queryset = DeliveryOption.objects.filter(is_active=True)
    serializer_class = DeliveryOptionSerializer

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        from django.db.models import Q
        sales = Sale.objects.filter(
            Q(customer__user=user) | Q(handled_by=user)
        ).distinct().order_by('-date_added')
        serializer = SaleSerializer(sales, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Sale.objects.none()
        
        queryset = Sale.objects.all().order_by('-date_added')
        
        # Search by username/customer name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                customer__name__icontains=search
            ) | queryset.filter(
                customer__user__username__icontains=search
            ) | queryset.filter(
                order_number__icontains=search
            )

        from django.db.models import Q
        if user.role == 'ADMIN':
            return queryset.order_by('-date_added')
        if user.role == 'POS':
            return queryset.filter(handled_by=user).order_by('-date_added')
        return queryset.filter(Q(customer__user=user) | Q(handled_by=user)).distinct().order_by('-date_added')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        customer_id = data.get('customer') or data.get('customer_id')
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'CASH')
        payment_screenshot = data.get('payment_screenshot')
        delivery_option_id = data.get('delivery_option')
        distance_km = float(data.get('distance_km', 0))
        
        if not items:
            return Response({"error": "No items provided for the sale"}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate Delivery Charge
        delivery_charge = 0
        if delivery_option_id:
            try:
                opt = DeliveryOption.objects.get(id=delivery_option_id)
                delivery_charge = float(opt.base_charge) + (distance_km * float(opt.per_km_charge))
            except DeliveryOption.DoesNotExist:
                pass

        # Robust Customer Association
        customer = None
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
            except (Customer.DoesNotExist, ValueError):
                pass
        
        # If no customer provided but user is logged in, link to their profile
        if not customer and request.user.is_authenticated:
            customer, _ = Customer.objects.get_or_create(
                user=request.user,
                defaults={'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username}
            )

        sale = Sale.objects.create(
            customer=customer,
            handled_by=request.user if request.user.is_authenticated else None,
            total_amount=0,
            delivery_option_id=delivery_option_id,
            delivery_charge=delivery_charge,
            distance_km=distance_km,
            status='PENDING'
        )
        
        # Record initial status history
        OrderStatusHistory.objects.create(
            sale=sale,
            old_status=None,
            new_status='PENDING',
            changed_by=request.user if request.user.is_authenticated else None,
            note='Order created'
        )

        total_amount = 0
        for item in items:
            medicine_id = item.get('medicine_id')
            quantity = item.get('quantity')
            
            try:
                medicine = Medicine.objects.get(id=medicine_id)
            except Medicine.DoesNotExist:
                return Response({"error": f"Medicine with id {medicine_id} not found"}, status=status.HTTP_400_BAD_REQUEST)

            if medicine.stock < quantity:
                return Response({"error": f"Insufficient stock for {medicine.name}"}, status=status.HTTP_400_BAD_REQUEST)

            item_total = float(medicine.price) * quantity
            total_amount += item_total

            # Update stock
            medicine.stock -= quantity
            medicine.save()

            # Create Sale Item
            SaleItem.objects.create(
                sale=sale,
                medicine=medicine,
                quantity=quantity,
                price=medicine.price,
                total=item_total
            )

        final_total = total_amount + float(delivery_charge)
        sale.total_amount = final_total
        sale.save()

        # Generate Payment Transaction
        payment = PaymentTransaction.objects.create(
            sale=sale,
            amount=final_total,
            method=payment_method,
            status='PENDING' if payment_method in ['QR', 'COD'] else 'COMPLETED',
            transaction_id=data.get('transaction_id') or (uuid.uuid4().hex[:10] if payment_method == 'QR' else None),
            payment_screenshot=payment_screenshot
        )

        serializer = self.get_serializer(sale)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Allow ADMIN/POS to update order status and optionally payment status"""
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        if user.role not in ['ADMIN', 'POS']:
            return Response({'error': 'Only ADMIN or POS can update order status'}, status=status.HTTP_403_FORBIDDEN)

        sale = self.get_object()
        new_status = request.data.get('status')
        new_payment_status = request.data.get('payment_status')
        note = request.data.get('note', '')

        # Validate order status
        valid_statuses = ['PENDING', 'CONFIRMED', 'PROCESSING', 'READY', 'DISPATCHED', 'DELIVERED', 'CANCELLED']
        if not new_status or new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Valid: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

        # Update order status
        old_status = sale.status
        sale.status = new_status
        sale.status_changed_by = user
        sale.status_changed_at = timezone.now()
        sale.save()

        # Optional: Update payment status if provided
        if new_payment_status:
            valid_payment_statuses = ['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED']
            if new_payment_status not in valid_payment_statuses:
                return Response({'error': f'Invalid payment status. Valid: {valid_payment_statuses}'}, status=status.HTTP_400_BAD_REQUEST)
            # Ensure there is a payment transaction linked
            payment = getattr(sale, 'payment', None)
            if payment:
                payment.status = new_payment_status
                payment.save()
            else:
                # Create a new payment transaction if missing (fallback)
                payment = PaymentTransaction.objects.create(
                    sale=sale,
                    amount=sale.total_amount,
                    method='UNKNOWN',
                    status=new_payment_status,
                )

        # Record order status history
        OrderStatusHistory.objects.create(
            sale=sale,
            old_status=old_status,
            new_status=new_status,
            changed_by=user,
            note=note
        )

        # Return updated sale (serializer includes nested payment status)
        serializer = self.get_serializer(sale)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Allow user to edit order within 30 minutes of creation; ADMIN can always edit"""
        user = request.user
        sale = self.get_object()
        
        if user.role == 'ADMIN':
            return super().update(request, *args, **kwargs)
        
        # For regular users: only allow within 30 minutes
        time_since_order = timezone.now() - sale.date_added
        if time_since_order > timedelta(minutes=30):
            return Response(
                {"error": "Order editing is only allowed within 30 minutes of placing the order."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Users can only edit their own orders
        if user.role == "USER" and (not sale.customer or sale.customer.user != user):
            return Response(
                {"error": "Unauthorized access to this order protocol."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Handle items update if provided
        items_data = request.data.get("items")
        if items_data is not None:
            with transaction.atomic():
                # Revert old stock
                for item in sale.items.all():
                    item.medicine.stock += item.quantity
                    item.medicine.save()

                # Clear existing items
                sale.items.all().delete()

                # Create new items and calculate total
                total_amount = 0
                for item_data in items_data:
                    medicine_id = item_data.get("medicine_id")
                    quantity = int(item_data.get("quantity", 0))

                    if quantity <= 0:
                        continue

                    try:
                        medicine = Medicine.objects.get(id=medicine_id)
                        if medicine.stock < quantity:
                            return Response(
                                {
                                    "error": f"Insufficient stock for {medicine.name}. Available: {medicine.stock}"
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        price = medicine.price
                        SaleItem.objects.create(
                            sale=sale,
                            medicine=medicine,
                            quantity=quantity,
                            price=price,
                        )
                        medicine.stock -= quantity
                        medicine.save()
                        total_amount += price * quantity
                    except Medicine.DoesNotExist:
                        continue

                sale.total_amount = total_amount
                # Update status slightly if it was just PENDING to trigger potential logic
                sale.save()

        # Update other fields using serializer (like delivery_option)
        serializer = self.get_serializer(sale, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Order deletion is prohibited for non-admin users."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

class PaymentTransactionViewSet(viewsets.ModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer

    def get_queryset(self):
        queryset = PaymentTransaction.objects.all().order_by('-timestamp')
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(timestamp__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(timestamp__date__lte=to_date)
            
        return queryset

    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        payment = self.get_object()
        if payment.status == 'PENDING':
            payment.status = 'COMPLETED'
            payment.save()
            return Response({'status': 'Payment marked as completed'})
        return Response({'error': 'Payment already processed'}, status=status.HTTP_400_BAD_REQUEST)

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            from .models import Address as AddressModel
            return AddressModel.objects.none()
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        is_default = serializer.validated_data.get('is_default', False)
        # If this is the user's first address, make it default
        if not Address.objects.filter(user=user).exists():
            is_default = True
        # If setting as default, un-default the rest
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        serializer.save(user=user, is_default=is_default)

    def perform_update(self, serializer):
        user = self.request.user
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        serializer.save()

    def perform_destroy(self, instance):
        user = instance.user
        was_default = instance.is_default
        instance.delete()
        # If deleted address was default, promote the most recent one
        if was_default:
            next_addr = Address.objects.filter(user=user).first()
            if next_addr:
                next_addr.is_default = True
                next_addr.save()

    @action(detail=True, methods=['patch'])
    def set_default(self, request, pk=None):
        address = self.get_object()
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save()
        return Response(AddressSerializer(address).data)

class PharmacySettingsViewSet(viewsets.ModelViewSet):
    queryset = PharmacySettings.objects.all()
    serializer_class = PharmacySettingsSerializer

    def get_queryset(self):
        # Ensure at least one settings object exists
        if not PharmacySettings.objects.exists():
            PharmacySettings.objects.create(name='HealKart')
        return PharmacySettings.objects.all()
