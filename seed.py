import os
import django
import pymysql
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
pymysql.install_as_MySQLdb()
pymysql.version_info = (2, 2, 1, "final", 0)

# Pre-setup: ensure database exists
def ensure_db_exists():
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'pharmacy')
    port = int(os.getenv('DB_PORT', 3306))
    
    try:
        connection = pymysql.connect(host=host, user=user, password=password, port=port)
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.close()
        connection.close()
        print(f"Database '{db_name}' verified.")
    except Exception as e:
        print(f"Warning: Could not verify/create database: {e}")

ensure_db_exists()

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from rx.models import Category, Medicine, Customer, Sale, SaleItem, PaymentTransaction, DeliveryOption, PharmacySettings

User = get_user_model()

def run_seed():
    print("Running Database Seeds...")
    
    # 1. Create Users
    print("Creating/Updating Users...")
    
    # 1.1 Admin User
    admin, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@gmail.com'})
    if created:
        admin.set_password('admin123')
        admin.is_superuser = True
        admin.is_staff = True
    admin.role = 'ADMIN'
    admin.save()
    print(f"Admin user {'created' if created else 'updated'}.")
        
    # 1.1b New Admin User
    new_admin, created = User.objects.get_or_create(username='newadmin', defaults={'email': 'newadmin@gmail.com'})
    if created:
        new_admin.set_password('newadmin123')
        new_admin.is_superuser = True
        new_admin.is_staff = True
    new_admin.role = 'ADMIN'
    new_admin.save()
    print(f"New admin user {'created' if created else 'updated'}.")
        
    # 1.2 POS Agent
    pos, created = User.objects.get_or_create(username='pos', defaults={'email': 'pos@gmail.com'})
    if created:
        pos.set_password('pos123')
    pos.role = 'POS'
    pos.save()
    print(f"POS user {'created' if created else 'updated'}.")
        
    # 1.3 Customer User
    customer, created = User.objects.get_or_create(username='customer', defaults={'email': 'customer@gmail.com'})
    if created:
        customer.set_password('customer123')
    customer.role = 'USER'
    customer.save()
    print(f"Customer user {'created' if created else 'updated'}.")
        
    # 2. Hierarchical Categories
    print("Creating Categories...")
    category_tree = {
        "Vitamins & Nutrition": {
            "description": "Daily essential supplements",
            "subs": ["Multivitamins", "Minerals", "Biotin", "Calcium"]
        },
        "Healthcare Device": {
            "description": "Medical equipment and tools",
            "subs": ["Monitors", "Support & Braces", "First Aid"]
        },
        "Ayurveda Products": {
            "description": "Herbal and natural healing",
            "subs": ["Ashwagandha", "Triphala", "Chyawanprash"]
        },
        "Personal Care": {
            "description": "Grooming and hygiene",
            "subs": ["Skin Care", "Hair Care", "Oral Care"]
        },
        "Health Conditions": {
            "description": "Targeted remedies",
            "subs": ["Diabetes Care", "Heart Care", "Pain Relief"]
        }
    }

    for main_name, data in category_tree.items():
        main_cat, _ = Category.objects.get_or_create(name=main_name, defaults={'description': data['description']})
        for sub_name in data['subs']:
            Category.objects.get_or_create(name=sub_name, parent=main_cat)

    # 3. Create Medicines
    print("Creating Medicines...")
    meds = [
        {
        "name": "Paracetamol 500mg",
        "category": "Pain Relief",
        "description": "Used to reduce fever and relieve mild to moderate pain.",
        "expiry_date": "2027-05-01",
        "image_url": "https://source.unsplash.com/featured/?medicine,tablet",
        "manufacturer": "PharmaCorp",
        "price": 10.0,
        "reorder_level": 10,
        "side_effects": "Nausea, allergic reactions (rare)",
        "stock": 500,
        "uses": "Fever, headache, body pain"
    },
    {
        "name": "Ibuprofen 400mg",
        "category": "Pain Relief",
        "description": "Anti-inflammatory drug for pain and swelling.",
        "expiry_date": "2026-12-01",
        "image_url": "https://source.unsplash.com/featured/?painkiller,medicine",
        "manufacturer": "Cipla",
        "price": 25.0,
        "reorder_level": 10,
        "side_effects": "Stomach upset, dizziness",
        "stock": 300,
        "uses": "Muscle pain, arthritis, fever"
    },
    {
        "name": "Amoxicillin Capsules",
        "category": "Antibiotics",
        "description": "Antibiotic used to treat bacterial infections.",
        "expiry_date": "2026-09-15",
        "image_url": "https://source.unsplash.com/featured/?capsule,medicine",
        "manufacturer": "Pfizer",
        "price": 80.0,
        "reorder_level": 10,
        "side_effects": "Diarrhea, rash",
        "stock": 150,
        "uses": "Bacterial infections"
    },
    {
        "name": "Cough Syrup",
        "category": "Cold & Flu",
        "description": "Relieves cough symptoms.",
        "expiry_date": "2026-10-01",
        "image_url": "https://source.unsplash.com/featured/?cough,syrup",
        "manufacturer": "Benadryl",
        "price": 90.0,
        "reorder_level": 10,
        "side_effects": "Drowsiness",
        "stock": 140,
        "uses": "Dry cough"
    },
    {
        "name": "Insulin Injection",
        "category": "Diabetes Care",
        "description": "Controls blood sugar levels.",
        "expiry_date": "2026-06-01",
        "image_url": "https://source.unsplash.com/featured/?insulin,injection",
        "manufacturer": "Novo Nordisk",
        "price": 600.0,
        "reorder_level": 10,
        "side_effects": "Low blood sugar",
        "stock": 60,
        "uses": "Diabetes management"
    },
    {
        "name": "Eye Drops",
        "category": "Eye Care",
        "description": "Relieves dry eyes.",
        "expiry_date": "2026-05-01",
        "image_url": "https://source.unsplash.com/featured/?eye,drops",
        "manufacturer": "Refresh Tears",
        "price": 60.0,
        "reorder_level": 10,
        "side_effects": "Temporary burning",
        "stock": 220,
        "uses": "Dry eyes"
    },
    {
        "name": "Vitamin D3 Capsules",
        "category": "Supplements",
        "description": "Improves calcium absorption.",
        "expiry_date": "2027-03-01",
        "image_url": "https://source.unsplash.com/featured/?vitamin,capsule",
        "manufacturer": "Uprise",
        "price": 220.0,
        "reorder_level": 10,
        "side_effects": "Rare side effects",
        "stock": 100,
        "uses": "Vitamin D deficiency"
    },
    {
        "name": "Hand Sanitizer",
        "category": "Hygiene",
        "description": "Kills germs without water.",
        "expiry_date": "2027-01-01",
        "image_url": "https://source.unsplash.com/featured/?sanitizer,medical",
        "manufacturer": "Dettol",
        "price": 70.0,
        "reorder_level": 10,
        "side_effects": "Dry skin",
        "stock": 300,
        "uses": "Hand cleaning"
    },
    {
        "name": "Thermometer Digital",
        "category": "Monitors",
        "description": "Measures body temperature.",
        "expiry_date": "2028-01-01",
        "image_url": "https://source.unsplash.com/featured/?thermometer,digital",
        "manufacturer": "Dr Trust",
        "price": 300.0,
        "reorder_level": 10,
        "side_effects": "None",
        "stock": 110,
        "uses": "Temperature monitoring"
    },
    {
        "name": "Pain Relief Spray",
        "category": "Pain Relief",
        "description": "Provides quick relief from pain.",
        "expiry_date": "2027-01-01",
        "image_url": "https://source.unsplash.com/featured/?pain,spray",
        "manufacturer": "Volini",
        "price": 180.0,
        "reorder_level": 10,
        "side_effects": "Skin irritation",
        "stock": 140,
        "uses": "Muscle pain"
    }
    ]
    
    for med in meds:
        try:
            cat = Category.objects.get(name=med['category'])
            Medicine.objects.get_or_create(
                name=med['name'],
                defaults={
                    'category': cat,
                    'price': med['price'],
                    'stock': med['stock'],
                    'manufacturer': med.get('manufacturer', 'Unknown'),
                    'expiry_date': date.today() + timedelta(days=365)
                }
            )
        except Category.DoesNotExist:
            print(f"Skipping {med['name']}: Category {med['category']} not found.")
    
    # 4. Create Customers
    print("Creating Customers...")
    customer_profile, created = Customer.objects.get_or_create(user=customer, defaults={
        'name': 'Demo Customer',
        'phone': '+977-9800000000',
        'address': 'Dilibazar, Kathmandu'
    })

    # 5. Create Delivery Options
    print("Creating Delivery Options...")
    std_delivery, _ = DeliveryOption.objects.get_or_create(name="Standard Delivery", defaults={
        'description': '3-5 business days',
        'base_charge': 50.0,
        'per_km_charge': 5.0
    })

    # 6. Create Sales/Orders
    print("Creating Sample Orders...")
    if not Sale.objects.filter(customer=customer_profile).exists():
        # Sale 1
        med1 = Medicine.objects.get(name="Paracetamol 500mg")
        sale1 = Sale.objects.create(
            customer=customer_profile,
            total_amount=100.0,
            delivery_option=std_delivery,
            distance_km=2.0,
            delivery_charge=60.0,
            handled_by=admin
        )
        SaleItem.objects.create(sale=sale1, medicine=med1, quantity=4, price=10.0, total=40.0)
        PaymentTransaction.objects.create(sale=sale1, amount=100.0, method='CASH', status='COMPLETED')

        # Sale 2
        med2 = Medicine.objects.get(name="Multivitamin Gold")
        sale2 = Sale.objects.create(
            customer=customer_profile,
            total_amount=950.0,
            delivery_option=std_delivery,
            distance_km=10.0,
            delivery_charge=100.0,
            handled_by=admin
        )
        SaleItem.objects.create(sale=sale2, medicine=med2, quantity=2, price=450.0, total=900.0)
        PaymentTransaction.objects.create(sale=sale2, amount=950.0, method='QR', status='COMPLETED')

        # Sale 3 (Pending)
        med3 = Medicine.objects.get(name="Digital BP Monitor")
        sale3 = Sale.objects.create(
            customer=customer_profile,
            total_amount=2600.0,
            delivery_option=std_delivery,
            distance_km=5.0,
            delivery_charge=75.0,
            handled_by=admin
        )
        SaleItem.objects.create(sale=sale3, medicine=med3, quantity=1, price=2500.0, total=2500.0)
        PaymentTransaction.objects.create(sale=sale3, amount=2600.0, method='ESewa', status='PENDING')

        # Sale 4 (Cancelled)
        med4 = Medicine.objects.get(name="Pure Ashwagandha Powder")
        sale4 = Sale.objects.create(
            customer=customer_profile,
            total_amount=240.0,
            delivery_option=std_delivery,
            distance_km=3.5,
            delivery_charge=67.5,
            handled_by=admin
        )
        SaleItem.objects.create(sale=sale4, medicine=med4, quantity=1, price=180.0, total=180.0)
        PaymentTransaction.objects.create(sale=sale4, amount=240.0, method='CASH', status='CANCELLED')
        print("Sample orders generated.")

    # 8. Pharmacy Settings
    print("Creating Pharmacy Settings...")
    PharmacySettings.objects.get_or_create(
        id=1,
        defaults={
            'name': 'PharmaLogic',
            'email': 'contact@pharmalogic.com',
            'phone': '+977-9876543210',
            'address': 'KTM-04, New Baneshwor, Nepal',
            'gst_number': 'PAN-123456789'
        }
    )
    print("Pharmacy Settings initialized.")

    print("Seeding Complete!")

if __name__ == '__main__':
    run_seed()
