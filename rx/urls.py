from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CustomerViewSet, CategoryViewSet,
    MedicineViewSet, SaleViewSet, PaymentTransactionViewSet, LoginView, DeliveryOptionViewSet, PharmacySettingsViewSet,
    FileUploadView, AddressViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'medicines', MedicineViewSet)
router.register(r'sales', SaleViewSet)
router.register(r'payment-transactions', PaymentTransactionViewSet)
router.register(r'delivery-options', DeliveryOptionViewSet)
router.register(r'pharmacy-settings', PharmacySettingsViewSet)
router.register(r'addresses', AddressViewSet, basename='address')

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('', include(router.urls)),
]
