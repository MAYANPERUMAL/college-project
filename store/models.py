from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
import random
import string


class CustomUser(AbstractUser):
    ROLE_ADMIN = 'ADMIN'
    ROLE_CUSTOMER = 'CUSTOMER'
    ROLE_SELLER = 'SELLER'
    ROLE_DELIVERY = 'DELIVERY'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_SELLER, 'Seller'),
        (ROLE_DELIVERY, 'Delivery Partner'),
    ]

    MEMBERSHIP_STANDARD = 'Standard'
    MEMBERSHIP_SILVER = 'Silver'
    MEMBERSHIP_GOLD = 'Gold'
    MEMBERSHIP_PLATINUM = 'Platinum'
    MEMBERSHIP_CHOICES = [
        (MEMBERSHIP_STANDARD, 'TechMart Member'),
        (MEMBERSHIP_SILVER, 'TechMart Silver'),
        (MEMBERSHIP_GOLD, 'TechMart Gold'),
        (MEMBERSHIP_PLATINUM, 'TechMart Platinum Member'),
    ]

    THEME_LIGHT = 'light'
    THEME_DARK = 'dark'
    THEME_SYSTEM = 'system'
    THEME_CHOICES = [
        (THEME_LIGHT, 'Light Mode'),
        (THEME_DARK, 'Dark Mode'),
        (THEME_SYSTEM, 'System Preference'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default=THEME_SYSTEM,
        help_text="User interface theme preference (light, dark, system)"
    )
    store_name = models.CharField(max_length=150, blank=True, default='', help_text="Seller Business / Store Name")
    seller_bio = models.TextField(blank=True, default='', help_text="Brief store description or seller notes")
    vehicle_type = models.CharField(max_length=50, blank=True, default='Motorcycle', help_text="Delivery vehicle: Motorcycle, Scooter, Electric EV, Van")
    vehicle_number = models.CharField(max_length=50, blank=True, default='', help_text="e.g. TN-38-BH-9821")
    is_available = models.BooleanField(default=True, help_text="Availability status for delivery partners")
    current_city = models.CharField(max_length=100, blank=True, default='Coimbatore', help_text="Operational delivery city")
    phone = models.CharField(max_length=15, blank=True, null=True)
    gst_number = models.CharField(max_length=25, blank=True, null=True, help_text="e.g. 27AAACH8291Q1ZT")
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    membership_tier = models.CharField(max_length=20, choices=MEMBERSHIP_CHOICES, default=MEMBERSHIP_PLATINUM)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=1250.00)
    is_verified = models.BooleanField(default=False, help_text="Verified via 6-digit OTP")

    def is_admin_user(self):
        return self.role == self.ROLE_ADMIN or self.is_staff or self.is_superuser

    def is_customer_user(self):
        return self.role == self.ROLE_CUSTOMER

    def is_seller_user(self):
        return self.role == self.ROLE_SELLER

    def is_delivery_partner(self):
        return self.role == self.ROLE_DELIVERY

    def is_seller(self):
        return self.is_seller_user()

    def is_customer(self):
        return self.is_customer_user()

    def is_delivery(self):
        return self.is_delivery_partner()

    def is_admin(self):
        return self.is_admin_user()

    @property
    def display_store_name(self):
        if self.store_name:
            return self.store_name
        full = self.get_full_name()
        if full:
            return f"{full}'s Store"
        return f"{self.username}'s Store"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon_name = models.CharField(max_length=50, default='devices', help_text="Material Symbol icon name")
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']

    @property
    def display_icon(self):
        """Map icon names or brand aliases to valid Google Material Symbol ligature."""
        mapping = {
            'sony': 'speaker_group',
            'speaker': 'speaker',
            'speakers': 'speaker_group',
            'apple': 'phone_iphone',
            'samsung': 'smartphone',
            'mobile': 'smartphone',
            'mobiles': 'smartphone',
            'phone': 'smartphone',
            'phones': 'smartphone',
            'tablet': 'tablet_mac',
            'tablets': 'tablet_mac',
            'laptop': 'laptop_mac',
            'laptops': 'laptop_mac',
            'tv': 'tv',
            'tvs': 'tv',
            'television': 'tv',
            'audio': 'headphones',
            'headphone': 'headphones',
            'headphones': 'headphones',
            'earphone': 'headphones',
            'earphones': 'headphones',
            'earbuds': 'headphones',
            'mouse': 'mouse',
            'keyboard': 'keyboard',
            'watch': 'watch',
            'watches': 'watch',
            'smartwatch': 'watch',
            'wearable': 'watch',
            'camera': 'photo_camera',
            'gaming': 'sports_esports',
        }
        val = (self.icon_name or '').strip().lower()
        if val in mapping:
            return mapping[val]
        if val and val.replace('_', '').isalnum():
            return val
        return 'devices'

    @property
    def theme_info(self):
        """Return luxurious tailored color palette, gradient, and marketing badge."""
        slug_clean = ((self.slug or '') + ' ' + (self.name or '')).lower()
        if 'audio' in slug_clean or 'headphone' in slug_clean or 'earphone' in slug_clean or 'earbuds' in slug_clean:
            return {
                'accent': '#7c3aed',
                'accent_light': '#ede9fe',
                'glow': 'rgba(124, 58, 237, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #6d28d9 0%, #8b5cf6 100%)',
                'badge': 'Hi-Res',
                'badge_bg': '#ede9fe',
                'badge_color': '#5b21b6',
            }
        elif 'mobile' in slug_clean or 'tablet' in slug_clean or 'smartphone' in slug_clean:
            return {
                'accent': '#0284c7',
                'accent_light': '#e0f2fe',
                'glow': 'rgba(2, 132, 199, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
                'badge': 'Trending',
                'badge_bg': '#e0f2fe',
                'badge_color': '#0369a1',
            }
        elif 'laptop' in slug_clean or 'computing' in slug_clean or 'computer' in slug_clean:
            return {
                'accent': '#4f46e5',
                'accent_light': '#e0e7ff',
                'glow': 'rgba(79, 70, 229, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #4338ca 0%, #6366f1 100%)',
                'badge': 'Pro Tech',
                'badge_bg': '#e0e7ff',
                'badge_color': '#3730a3',
            }
        elif 'tv' in slug_clean or 'television' in slug_clean or 'appliance' in slug_clean:
            return {
                'accent': '#d97706',
                'accent_light': '#fef3c7',
                'glow': 'rgba(217, 119, 6, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #b45309 0%, #f59e0b 100%)',
                'badge': '4K OLED',
                'badge_bg': '#fef3c7',
                'badge_color': '#92400e',
            }
        elif 'watch' in slug_clean or 'wearable' in slug_clean:
            return {
                'accent': '#059669',
                'accent_light': '#d1fae5',
                'glow': 'rgba(5, 150, 105, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #047857 0%, #10b981 100%)',
                'badge': 'Fitness',
                'badge_bg': '#d1fae5',
                'badge_color': '#065f46',
            }
        elif 'speaker' in slug_clean or 'sound' in slug_clean:
            return {
                'accent': '#e11d48',
                'accent_light': '#ffe4e6',
                'glow': 'rgba(225, 29, 72, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #be123c 0%, #f43f5e 100%)',
                'badge': 'Dolby Atmos',
                'badge_bg': '#ffe4e6',
                'badge_color': '#9f1239',
            }
        elif 'access' in slug_clean or 'peripheral' in slug_clean:
            return {
                'accent': '#334155',
                'accent_light': '#f1f5f9',
                'glow': 'rgba(51, 65, 85, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #1e293b 0%, #475569 100%)',
                'badge': 'Essential',
                'badge_bg': '#f1f5f9',
                'badge_color': '#1e293b',
            }
        else:
            return {
                'accent': '#1e463a',
                'accent_light': '#e4eee9',
                'glow': 'rgba(30, 70, 58, 0.22)',
                'icon_bg': 'linear-gradient(135deg, #1e463a 0%, #2d6a58 100%)',
                'badge': 'Featured',
                'badge_bg': '#e4eee9',
                'badge_color': '#143329',
            }

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'category'
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    brand = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    specs = models.TextField(blank=True, help_text="Key specs separated by newline or bullet points")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Selling price in ₹")
    mrp = models.DecimalField(max_digits=10, decimal_places=2, help_text="Maximum Retail Price in ₹")
    stock = models.PositiveIntegerField(default=15)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(max_length=800, blank=True, help_text="Direct image URL if external")
    is_featured = models.BooleanField(default=False)
    is_deal = models.BooleanField(default=False)
    deal_tag = models.CharField(max_length=60, blank=True, default="Deal of the Day")
    warranty_info = models.CharField(max_length=150, default="Official 1-Year Pan-India Warranty")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.8)
    reviews_count = models.PositiveIntegerField(default=24)
    is_active = models.BooleanField(default=True, help_text="Product active / visible status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'product'
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.mrp and self.mrp > self.price:
            return round(((self.mrp - self.price) / self.mrp) * 100)
        return 0

    @property
    def savings(self):
        if self.mrp and self.mrp > self.price:
            return self.mrp - self.price
        return 0

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def emi_starts_from(self):
        # Monthly approximate 12-month EMI
        return round(float(self.price) / 12)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return 'https://placehold.co/600x600/e2e8f0/003092?text=' + self.brand

    @property
    def seller_display(self):
        if self.seller:
            return self.seller.store_name or self.seller.get_full_name() or self.seller.username
        return "TechMart Retail (Direct)"

    def __str__(self):
        return f"{self.brand} {self.name} (₹{self.price})"


class Address(models.Model):
    TYPE_HOME = 'HOME'
    TYPE_OFFICE = 'OFFICE'
    TYPE_OTHER = 'OTHER'
    TYPE_CHOICES = [
        (TYPE_HOME, 'Home'),
        (TYPE_OFFICE, 'Office'),
        (TYPE_OTHER, 'Other'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=255, help_text="Flat, House no., Building, Apartment")
    address_line2 = models.CharField(max_length=255, blank=True, help_text="Area, Street, Sector, Village")
    landmark = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)
    address_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_HOME)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Addresses'

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.city}, {self.pincode} ({self.get_address_type_display()})"


class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def total_mrp(self):
        return sum(item.mrp_total for item in self.items.all())

    @property
    def total_discount(self):
        return max(0, self.total_mrp - self.subtotal)

    @property
    def delivery_charge(self):
        # Free delivery over ₹500
        if self.subtotal >= 500 or self.subtotal == 0:
            return 0
        return 99

    @property
    def gst_amount(self):
        # 18% standard electronics GST component (included or calculated)
        return round(float(self.subtotal) * 0.18, 2)

    @property
    def grand_total(self):
        return self.subtotal + self.delivery_charge

    def __str__(self):
        return f"Cart ({self.user.username if self.user else self.session_key})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.product.price * self.quantity

    @property
    def mrp_total(self):
        return self.product.mrp * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_PACKED = 'PACKED'
    STATUS_IN_TRANSIT = 'IN_TRANSIT'
    STATUS_OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Order Confirmed'),
        (STATUS_PACKED, 'Packed & Sealed'),
        (STATUS_IN_TRANSIT, 'In Transit'),
        (STATUS_OUT_FOR_DELIVERY, 'Out for Delivery'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAY_UPI = 'UPI'
    PAY_WALLET = 'WALLET'
    PAY_CARD = 'CARD'
    PAY_NETBANKING = 'NETBANKING'
    PAY_EMI = 'EMI'
    PAY_COD = 'COD'
    PAYMENT_CHOICES = [
        (PAY_UPI, 'UPI (Google Pay / PhonePe / Paytm / QR)'),
        (PAY_WALLET, 'Wallets (Paytm / PhonePe / Amazon Pay)'),
        (PAY_CARD, 'Credit / Debit / ATM Card (Visa, Mastercard, RuPay)'),
        (PAY_NETBANKING, 'Net Banking (All Indian Banks)'),
        (PAY_EMI, 'EMI (Easy Installments & No-Cost EMI)'),
        (PAY_COD, 'Cash on Delivery (OTP Verified)'),
    ]

    PAY_STATUS_PENDING = 'PENDING'
    PAY_STATUS_PAID = 'PAID'
    PAY_STATUS_FAILED = 'FAILED'
    PAY_STATUS_REFUNDED = 'REFUNDED'
    PAY_STATUS_CHOICES = [
        (PAY_STATUS_PENDING, 'Pending'),
        (PAY_STATUS_PAID, 'Paid'),
        (PAY_STATUS_FAILED, 'Failed'),
        (PAY_STATUS_REFUNDED, 'Refunded'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    
    # Snapshot of delivery address
    shipping_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=15)
    shipping_address_line1 = models.CharField(max_length=255)
    shipping_address_line2 = models.CharField(max_length=255, blank=True)
    shipping_landmark = models.CharField(max_length=120, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=6)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAY_UPI)
    payment_status = models.CharField(max_length=20, choices=PAY_STATUS_CHOICES, default=PAY_STATUS_PAID)
    order_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    
    delivery_pin = models.CharField(max_length=4, default="4819", help_text="4-digit secure doorstep delivery PIN")
    courier_name = models.CharField(max_length=100, default="Bluedart Air Express")
    tracking_number = models.CharField(max_length=50, blank=True)
    estimated_delivery_text = models.CharField(max_length=100, default="Tomorrow by 2:00 PM")
    current_location = models.CharField(max_length=150, default="Worli Local Hub")
    cancellation_reason = models.CharField(max_length=255, blank=True, default='')
    
    # Delivery Partner Assignment & Tracking
    delivery_partner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_deliveries')
    delivery_assigned_at = models.DateTimeField(null=True, blank=True)
    delivery_picked_up_at = models.DateTimeField(null=True, blank=True)
    delivery_delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils import timezone
            year = timezone.now().year
            random_digits = ''.join(random.choices(string.digits, k=5))
            self.order_number = f"TM-{year}-{random_digits}"
            while Order.objects.filter(order_number=self.order_number).exists():
                random_digits = ''.join(random.choices(string.digits, k=5))
                self.order_number = f"TM-{year}-{random_digits}"
        if not self.delivery_pin:
            self.delivery_pin = ''.join(random.choices(string.digits, k=4))
        if not self.tracking_number:
            self.tracking_number = ''.join(random.choices(string.digits, k=10))
        super().save(*args, **kwargs)

    @property
    def step_number(self):
        mapping = {
            self.STATUS_CONFIRMED: 1,
            self.STATUS_PACKED: 2,
            self.STATUS_IN_TRANSIT: 3,
            self.STATUS_OUT_FOR_DELIVERY: 4,
            self.STATUS_DELIVERED: 5,
            self.STATUS_CANCELLED: 0,
        }
        return mapping.get(self.order_status, 1)

    @property
    def is_active(self):
        return self.order_status in [
            self.STATUS_CONFIRMED,
            self.STATUS_PACKED,
            self.STATUS_IN_TRANSIT,
            self.STATUS_OUT_FOR_DELIVERY,
        ]

    @property
    def can_cancel(self):
        return self.order_status in [
            self.STATUS_CONFIRMED,
            self.STATUS_PACKED,
            self.STATUS_IN_TRANSIT,
        ]

    def __str__(self):
        return f"#{self.order_number} - {self.user.username} (₹{self.total_amount})"


class OrderItem(models.Model):
    ITEM_STATUS_CONFIRMED = 'CONFIRMED'
    ITEM_STATUS_PACKED = 'PACKED'
    ITEM_STATUS_READY = 'READY_FOR_PICKUP'
    ITEM_STATUS_REJECTED = 'REJECTED'
    ITEM_STATUS_CHOICES = [
        (ITEM_STATUS_CONFIRMED, 'Order Confirmed by Seller'),
        (ITEM_STATUS_PACKED, 'Item Prepared & Packed'),
        (ITEM_STATUS_READY, 'Ready for Delivery Pickup'),
        (ITEM_STATUS_REJECTED, 'Item Rejected / Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    warranty_info = models.CharField(max_length=150, default="Brand 1-Year Warranty")
    image_url = models.CharField(max_length=800, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, choices=ITEM_STATUS_CHOICES, default=ITEM_STATUS_CONFIRMED)

    def save(self, *args, **kwargs):
        if self.product and self.product.seller and not self.seller:
            self.seller = self.product.seller
        elif not self.seller:
            default_seller = CustomUser.objects.filter(role=CustomUser.ROLE_SELLER, is_active=True).first()
            if default_seller:
                self.seller = default_seller
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in {self.order.order_number}"


class OTPVerification(models.Model):
    PURPOSE_REGISTRATION = 'REGISTRATION'
    PURPOSE_LOGIN = 'LOGIN'
    PURPOSE_COD = 'COD_ORDER'
    PURPOSE_CHOICES = [
        (PURPOSE_REGISTRATION, 'Customer Registration'),
        (PURPOSE_LOGIN, 'Customer Login'),
        (PURPOSE_COD, 'Cash on Delivery Verification'),
    ]

    phone_or_email = models.CharField(max_length=100, db_index=True)
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_REGISTRATION)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='otp_codes')
    session_payload = models.JSONField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'OTP Verification'
        verbose_name_plural = 'OTP Verifications'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.purpose} OTP for {self.phone_or_email}: {self.otp_code}"


class Notification(models.Model):
    TYPE_ORDER = 'ORDER'
    TYPE_STATUS_UPDATE = 'STATUS_UPDATE'
    TYPE_REGISTRATION = 'REGISTRATION'
    TYPE_LOGIN = 'LOGIN'
    TYPE_INSTRUCTION = 'INSTRUCTION'
    TYPE_SYSTEM = 'SYSTEM'
    TYPE_CHOICES = [
        (TYPE_ORDER, 'Order Activity'),
        (TYPE_STATUS_UPDATE, 'Order Status Milestone'),
        (TYPE_REGISTRATION, 'New Account Registration'),
        (TYPE_LOGIN, 'Customer Login'),
        (TYPE_INSTRUCTION, 'Admin Instruction / Announcement'),
        (TYPE_SYSTEM, 'System Notification'),
    ]

    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    for_admin = models.BooleanField(default=False, help_text="True if this notification is for store administrators")
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    icon = models.CharField(max_length=50, default='notifications')
    link_url = models.CharField(max_length=255, blank=True, help_text="URL for one-click navigation")
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = "Admin" if self.for_admin else (self.recipient.username if self.recipient else "Broadcast")
        return f"[{target}] {self.title}"


def send_system_notification(recipient=None, for_admin=False, title='', message='', notification_type=Notification.TYPE_SYSTEM, icon='notifications', link_url='', order=None):
    """
    Central helper function to deliver notifications.
    If for_admin=True, delivers to all store administrators.
    If recipient is provided, delivers directly to that user.
    """
    from django.db.models import Q
    if for_admin:
        admins = CustomUser.objects.filter(
            Q(role=CustomUser.ROLE_ADMIN) | Q(is_staff=True) | Q(is_superuser=True)
        ).distinct()
        created_notifs = []
        for admin_user in admins:
            notif = Notification.objects.create(
                recipient=admin_user,
                for_admin=True,
                title=title,
                message=message,
                notification_type=notification_type,
                icon=icon,
                link_url=link_url,
                order=order,
            )
            created_notifs.append(notif)
        return created_notifs
    elif recipient:
        return Notification.objects.create(
            recipient=recipient,
            for_admin=False,
            title=title,
            message=message,
            notification_type=notification_type,
            icon=icon,
            link_url=link_url,
            order=order,
        )
    return None


class PaymentSetting(models.Model):
    """
    Store-wide Payment Gateway & UPI QR Code Configuration.
    Allows Store Administrators to upload a custom UPI QR Code image,
    configure their UPI ID / VPA, toggle payment methods, and manage limits.
    """
    # UPI & QR Configurations
    upi_id = models.CharField(max_length=100, default='mayanperumal123@oksbi', help_text="Store UPI ID / VPA (e.g. mayanperumal123@oksbi)")
    merchant_name = models.CharField(max_length=150, default='Tech Mart', help_text="Business / Payee display name")
    qr_image = models.ImageField(upload_to='payment_qr/', blank=True, null=True, help_text="Custom UPI QR Code image")
    upi_note = models.CharField(max_length=150, default='Tech Mart Order', help_text="Default UPI transaction note")

    # Payment Gateway Toggles
    enable_upi = models.BooleanField(default=True, help_text="Enable UPI Intent & QR Code payments")
    enable_card = models.BooleanField(default=True, help_text="Enable Credit & Debit card payments")
    enable_netbanking = models.BooleanField(default=True, help_text="Enable Net Banking / Direct Bank Portal")
    enable_cod = models.BooleanField(default=True, help_text="Enable Cash on Delivery")
    cod_max_limit = models.DecimalField(max_digits=10, decimal_places=2, default=100000.00, help_text="Maximum cart total allowed for COD")

    # Bank Transfer / Settlement Details
    bank_name = models.CharField(max_length=100, default='State Bank of India', blank=True)
    account_number = models.CharField(max_length=50, default='30981273918', blank=True)
    ifsc_code = models.CharField(max_length=20, default='SBIN0001234', blank=True)
    account_holder_name = models.CharField(max_length=150, default='TechMart Electronics Pvt Ltd', blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment & QR Setting"
        verbose_name_plural = "Payment & QR Settings"

    def __str__(self):
        return f"Payment Settings ({self.upi_id})"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    @property
    def get_qr_url(self):
        if self.qr_image and hasattr(self.qr_image, 'url'):
            return self.qr_image.url
        from django.templatetags.static import static
        return static('images/gpay_qr.jpg')



