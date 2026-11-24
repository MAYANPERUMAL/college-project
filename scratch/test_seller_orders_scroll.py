import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techmart.settings')
django.setup()

from store.models import CustomUser, Order
from django.test import Client

client = Client()
seller = CustomUser.objects.filter(role='SELLER').first()
if not seller:
    seller = CustomUser.objects.filter(is_superuser=True).first()

print(f"Testing with seller: {seller.username}")
client.force_login(seller)

resp = client.get('/seller-dashboard/orders/')
print(f"GET /seller-dashboard/orders/ -> {resp.status_code}")
assert resp.status_code == 200

content = resp.content.decode('utf-8')
assert 'seller-orders-scroll' in content, "seller-orders-scroll class not found!"
assert 'Bottom Scroll' in content, "Bottom Scroll control bar not found!"
assert 'Scroll Left' in content, "Scroll Left button not found!"
assert 'Scroll Right' in content, "Scroll Right button not found!"
assert 'sellerOrdersContainer' in content, "sellerOrdersContainer id not found!"

print("ALL SELLER ORDERS DOWN-SIDE SCROLL CHECKS PASSED SUCCESSFULLY!")
