import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

User = get_user_model()
users = User.objects.all()

with open('db_status.txt', 'w') as f:
    f.write(f"Total Users: {users.count()}\n")
    for user in users:
        f.write(f"User: {user.username}, Role: {getattr(user, 'role', 'N/A')}, Active: {user.is_active}\n")
