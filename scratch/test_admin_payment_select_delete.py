import os
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techmart.settings')
django.setup()

from store.models import CustomUser, Order
from django.test import Client

client = Client()
admin = CustomUser.objects.filter(is_superuser=True).first()
if not admin:
    admin = CustomUser.objects.filter(role='ADMIN').first()

print(f"Testing as admin: {admin.username}")
client.force_login(admin)

# 1. Test GET /admin-dashboard/payments/
resp = client.get('/admin-dashboard/payments/')
print(f"GET /admin-dashboard/payments/ -> {resp.status_code}")
assert resp.status_code == 200
content = resp.content.decode('utf-8')
assert 'selectAllTxn' in content, "selectAllTxn checkbox not found in HTML!"
assert 'txn-row-check' in content, "txn-row-check checkboxes not found in HTML!"
assert 'bulkTxnActions' in content, "bulkTxnActions bar not found in HTML!"
assert 'deleteSingleTxn' in content, "deleteSingleTxn JS action not found in HTML!"
print("Admin Payment transactions table select and delete UI elements verified!")

# 2. Test Single Delete via payment_settings action
cust = CustomUser.objects.filter(role='CUSTOMER').first() or admin
test_single = f"TEST-TXN-SNG-{uuid.uuid4().hex[:6].upper()}"
Order.objects.create(
    order_number=test_single,
    user=cust,
    shipping_name="Test Txn Single",
    shipping_phone="9999999999",
    shipping_address_line1="Test",
    shipping_city="Coimbatore",
    shipping_state="Tamil Nadu",
    shipping_pincode="641001",
    total_amount=500.00,
    subtotal=500.00,
    payment_method="UPI",
    payment_status="PAID"
)

post_sng = client.post('/admin-dashboard/payments/', {
    'action': 'delete_transaction',
    'order_number': test_single
})
print(f"POST single transaction delete -> {post_sng.status_code}")
assert not Order.objects.filter(order_number=test_single).exists(), "Single txn delete failed!"
print("Single transaction delete action verified!")

# 3. Test Bulk Delete via payment_settings action
test_bulk_1 = f"TEST-TXN-B1-{uuid.uuid4().hex[:6].upper()}"
test_bulk_2 = f"TEST-TXN-B2-{uuid.uuid4().hex[:6].upper()}"
Order.objects.create(order_number=test_bulk_1, user=cust, shipping_name="B1", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="641001", total_amount=100, subtotal=100)
Order.objects.create(order_number=test_bulk_2, user=cust, shipping_name="B2", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="641001", total_amount=100, subtotal=100)

post_bulk = client.post('/admin-dashboard/payments/', {
    'action': 'bulk_delete_transactions',
    'order_numbers': [test_bulk_1, test_bulk_2]
})
print(f"POST bulk transaction delete -> {post_bulk.status_code}")
assert not Order.objects.filter(order_number__in=[test_bulk_1, test_bulk_2]).exists(), "Bulk txn delete failed!"
print("Bulk transaction delete action verified!")

# 4. Test Dedicated standalone delete routes
test_route_sng = f"TEST-RTE-SNG-{uuid.uuid4().hex[:6].upper()}"
Order.objects.create(order_number=test_route_sng, user=cust, shipping_name="Route Sng", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="641001", total_amount=100, subtotal=100)
resp_sng_route = client.post(f'/admin-dashboard/orders/{test_route_sng}/delete/', {'next': '/admin-dashboard/payments/'})
print(f"POST standalone order delete -> {resp_sng_route.status_code}")
assert not Order.objects.filter(order_number=test_route_sng).exists()

test_route_b1 = f"TEST-RTE-B1-{uuid.uuid4().hex[:6].upper()}"
test_route_b2 = f"TEST-RTE-B2-{uuid.uuid4().hex[:6].upper()}"
Order.objects.create(order_number=test_route_b1, user=cust, shipping_name="RB1", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="641001", total_amount=100, subtotal=100)
Order.objects.create(order_number=test_route_b2, user=cust, shipping_name="RB2", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="641001", total_amount=100, subtotal=100)
resp_bulk_route = client.post('/admin-dashboard/orders/bulk-delete/', {
    'order_numbers': [test_route_b1, test_route_b2],
    'next': '/admin-dashboard/payments/'
})
print(f"POST standalone bulk delete -> {resp_bulk_route.status_code}")
assert not Order.objects.filter(order_number__in=[test_route_b1, test_route_b2]).exists()

print("\nALL ADMIN PAYMENT TRANSACTION SELECT & DELETE TESTS PASSED SUCCESSFULLY!")
