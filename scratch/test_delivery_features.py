import os
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techmart.settings')
django.setup()

from store.models import CustomUser, Order, OrderItem, Product, Category
from django.test import Client

client = Client()

# Get delivery partner
delivery_partner = CustomUser.objects.filter(role='DELIVERY').first()
if not delivery_partner:
    delivery_partner = CustomUser.objects.create_user(
        username='arun_delivery',
        password='Password@123',
        role='DELIVERY',
        phone='9876543210',
        first_name='Arun',
        last_name='Kumar',
        vehicle_type='Bike',
        vehicle_number='TN 38 AB 1234',
        is_available=True
    )
    print("Created delivery partner arun_delivery")
else:
    print(f"Using delivery partner: {delivery_partner.username}")

# Check current orders
print(f"Total orders in DB: {Order.objects.count()}")

customer = CustomUser.objects.filter(role='CUSTOMER').first()
if not customer:
    customer = CustomUser.objects.create_user(
        username='cust_test',
        password='Password@123',
        role='CUSTOMER',
        phone='9876543212',
        first_name='Kavitha',
        last_name='R'
    )

seller = CustomUser.objects.filter(role='SELLER').first()
category = Category.objects.first()
product = Product.objects.first()

if not product and category:
    product = Product.objects.create(
        name="Demo Smartphone X",
        category=category,
        seller=seller,
        price=19999,
        stock=50,
        sku="DEMO-PHONE-1"
    )

# Create 2 active delivery orders if none exist
active_count = Order.objects.filter(delivery_partner=delivery_partner, order_status__in=['CONFIRMED', 'PACKED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY']).count()
if active_count < 2:
    for i in range(1, 3):
        num = f"DEL-ACT-{uuid.uuid4().hex[:6].upper()}"
        order = Order.objects.create(
            order_number=num,
            user=customer,
            delivery_partner=delivery_partner,
            shipping_name=f"Customer Active {i}",
            shipping_phone="9876543210",
            shipping_address_line1="123 Tech Park Road",
            shipping_city="Coimbatore",
            shipping_state="Tamil Nadu",
            shipping_pincode="641001",
            payment_method="ONLINE",
            payment_status="PAID",
            order_status="OUT_FOR_DELIVERY",
            subtotal=15499.00,
            total_amount=15499.00
        )
        if product:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=product.price,
                mrp=product.price,
                line_total=product.price,
                quantity=1,
                seller=seller
            )
        print(f"Created active order #{num}")

# Create 2 completed delivery orders if none exist
completed_count = Order.objects.filter(delivery_partner=delivery_partner, order_status='DELIVERED').count()
if completed_count < 2:
    for i in range(1, 3):
        num = f"DEL-CMP-{uuid.uuid4().hex[:6].upper()}"
        order = Order.objects.create(
            order_number=num,
            user=customer,
            delivery_partner=delivery_partner,
            shipping_name=f"Customer Delivered {i}",
            shipping_phone="9876543211",
            shipping_address_line1="45 Gandhipuram Cross Road",
            shipping_city="Coimbatore",
            shipping_state="Tamil Nadu",
            shipping_pincode="641012",
            payment_method="COD",
            payment_status="PAID",
            order_status="DELIVERED",
            subtotal=8999.00,
            total_amount=8999.00
        )
        if product:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                price=product.price,
                mrp=product.price,
                line_total=product.price,
                quantity=1,
                seller=seller
            )
        print(f"Created completed order #{num}")

# Log in delivery partner
client.force_login(delivery_partner)

# Test GET /delivery-dashboard/
resp = client.get('/delivery-dashboard/')
print(f"GET /delivery-dashboard/ -> {resp.status_code}")
content = resp.content.decode('utf-8')
assert resp.status_code == 200
assert 'selectAllDelivActive' in content, "selectAllDelivActive checkbox not found in dashboard!"
assert 'deliv-active-check' in content, "deliv-active-check checkboxes not found in dashboard!"
assert 'bulkDelivActiveActions' in content, "bulkDelivActiveActions not found in dashboard!"
assert 'deleteActiveDelivery' in content, "deleteActiveDelivery JS action not found in dashboard!"
print("Active deliveries select and delete elements verified!")

# Test GET /delivery-dashboard/history/
resp_hist = client.get('/delivery-dashboard/history/')
print(f"GET /delivery-dashboard/history/ -> {resp_hist.status_code}")
content_hist = resp_hist.content.decode('utf-8')
assert resp_hist.status_code == 200
assert 'selectAllDelivHistory' in content_hist, "selectAllDelivHistory checkbox not found in history!"
assert 'deliv-history-check' in content_hist, "deliv-history-check checkboxes not found in history!"
assert 'bulkDelivHistoryActions' in content_hist, "bulkDelivHistoryActions not found in history!"
assert 'deleteSingleDelivery' in content_hist, "deleteSingleDelivery JS action not found in history!"
print("Completed deliveries select and delete elements verified!")

# Test single delete
test_single_num = f"TEST-DEL-SNG-{uuid.uuid4().hex[:6].upper()}"
sng_order = Order.objects.create(
    order_number=test_single_num,
    user=customer,
    delivery_partner=delivery_partner,
    shipping_name="Test Single Delete",
    shipping_phone="9999999999",
    shipping_address_line1="Test",
    shipping_city="Chennai",
    shipping_state="Tamil Nadu",
    shipping_pincode="600001",
    payment_method="COD",
    order_status="OUT_FOR_DELIVERY",
    subtotal=100.00,
    total_amount=100.00
)
post_resp = client.post(f'/delivery-dashboard/orders/{test_single_num}/delete/', {'next': '/delivery-dashboard/'})
print(f"POST single delete -> {post_resp.status_code}")
assert not Order.objects.filter(order_number=test_single_num).exists(), "Single delete failed!"
print("Single delete successfully verified!")

# Test bulk delete
test_bulk_1 = f"TEST-BLK-1-{uuid.uuid4().hex[:6].upper()}"
test_bulk_2 = f"TEST-BLK-2-{uuid.uuid4().hex[:6].upper()}"
Order.objects.create(order_number=test_bulk_1, user=customer, delivery_partner=delivery_partner, shipping_name="Bulk 1", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="600001", subtotal=10, total_amount=10)
Order.objects.create(order_number=test_bulk_2, user=customer, delivery_partner=delivery_partner, shipping_name="Bulk 2", shipping_phone="999", shipping_address_line1="T", shipping_city="C", shipping_state="TN", shipping_pincode="600001", subtotal=10, total_amount=10)

bulk_resp = client.post('/delivery-dashboard/orders/bulk-delete/', {
    'order_numbers': [test_bulk_1, test_bulk_2],
    'next': '/delivery-dashboard/history/'
})
print(f"POST bulk delete -> {bulk_resp.status_code}")
assert not Order.objects.filter(order_number__in=[test_bulk_1, test_bulk_2]).exists(), "Bulk delete failed!"
print("Bulk delete successfully verified!")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
