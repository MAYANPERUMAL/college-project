from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Category, Product, Address, Cart, CartItem, Order, OrderItem, OTPVerification


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'membership_tier')
    list_filter = ('role', 'is_staff', 'is_active', 'membership_tier')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Membership Details', {'fields': ('role', 'phone', 'gst_number', 'profile_image', 'membership_tier', 'wallet_balance')}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_name', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'mrp', 'stock', 'is_featured', 'is_deal')
    list_filter = ('category', 'brand', 'is_featured', 'is_deal')
    search_fields = ('name', 'brand', 'model_number')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'state', 'pincode', 'address_type', 'is_default')
    list_filter = ('city', 'state', 'address_type', 'is_default')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'payment_method', 'payment_status', 'order_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'shipping_name', 'shipping_phone')
    inlines = [OrderItemInline]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'total_items', 'subtotal', 'created_at')


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_or_email', 'otp_code', 'purpose', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_verified', 'created_at')
    search_fields = ('phone_or_email', 'otp_code')
    readonly_fields = ('otp_code', 'created_at')

