"""
Tech Mart - MySQL Database Inspector
Displays live tables, record counts, and sample records from tech_mart_db.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techmart.settings')
django.setup()

from django.db import connection
from store.models import CustomUser, Product, Order, Category, Address, OTPVerification

def show_database():
    print("=" * 70)
    print("         TECH MART - LIVE MYSQL DATABASE INSPECTION REPORT")
    print("=" * 70)

    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE(), VERSION(), USER(), @@hostname, @@port;")
        current_db, version, user, host, port = cursor.fetchone()
        print(f" [+] Connected Database : {current_db}")
        print(f" [+] MySQL Server Host  : {host}:{port}")
        print(f" [+] MySQL Version      : {version}")
        print(f" [+] Connected User     : {user}")
        print("-" * 70)

        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        print(f" [i] Total Tables in '{current_db}': {len(tables)}\n")
        print(f" {'TABLE NAME':<36} | {'ROW COUNT':>10}")
        print(" " + "-" * 50)
        for t in sorted(tables):
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
            count = cursor.fetchone()[0]
            print(f"  • {t:<35} | {count:>10} rows")

    print("\n" + "=" * 70)
    print(" 1. REGISTERED USERS (store_customuser table)")
    print("=" * 70)
    for u in CustomUser.objects.all():
        print(f"  ID #{u.id:<2} | Username: {u.username:<10} | Role: {u.role:<8} | Email: {u.email}")

    print("\n" + "=" * 70)
    print(" 2. PRODUCT CATALOG (store_product table)")
    print("=" * 70)
    for p in Product.objects.all():
        print(f"  ID #{p.id:<2} | Category: {p.category.name:<12} | Price: ₹{p.price:>10,.2f} | Stock: {p.stock:<3} | {p.name[:38]}")

    print("\n" + "=" * 70)
    print(" 3. LIVE CUSTOMER ORDERS (store_order table)")
    print("=" * 70)
    for o in Order.objects.all().order_by('-created_at'):
        print(f"  Order: {o.order_number} | Customer: {o.user.username:<8} | Total: ₹{o.total_amount:>10,.2f} | Status: {o.order_status:<12} | PIN: {o.delivery_pin}")

    print("\n" + "=" * 70)
    print(" 4. OTP VERIFICATIONS (store_otpverification table)")
    print("=" * 70)
    for otp in OTPVerification.objects.all()[:5]:
        print(f"  Target: {otp.phone_or_email:<18} | Code: {otp.otp_code} | Purpose: {otp.purpose:<12} | Verified: {otp.is_verified}")
    if not OTPVerification.objects.exists():
        print("  (No OTP records yet. Generate one by registering or OTP login!)")

    print("\n" + "=" * 70)
    print(" [✓] DATABASE CONNECTION: 100% OK & ACTIVE IN MYSQL SERVER")
    print("=" * 70)

if __name__ == '__main__':
    show_database()
