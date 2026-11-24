from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
import datetime
import random
import re
from datetime import timedelta
from django.utils import timezone

from .models import (
    CustomUser, Category, Product, Address, Cart, CartItem, Order, OrderItem,
    OTPVerification, Notification, PaymentSetting, send_system_notification
)
from .forms import (
    CustomerRegisterForm, CustomerLoginForm, ProductForm, CategoryForm,
    AddressForm, OrderStatusForm, OTPVerifyForm, OTPLoginForm, PaymentSettingForm,
    SellerProductForm, SellerProfileForm, DeliveryPartnerProfileForm, AdminAssignPartnerForm,
    CustomerProfileForm, ProfilePasswordChangeForm
)
from .decorators import admin_required, seller_required, delivery_required


# ==============================================================================
# Helper Utilities (Phone Normalization & Customer Lookup)
# ==============================================================================
def normalize_phone_number(raw_phone):
    """Clean phone number down to standard 10-digit Indian mobile number."""
    if not raw_phone:
        return ''
    cleaned = re.sub(r'\D', '', str(raw_phone))
    if len(cleaned) > 10 and cleaned.startswith('91'):
        cleaned = cleaned[2:]
    elif len(cleaned) > 10 and cleaned.startswith('0'):
        cleaned = cleaned[1:]
    return cleaned


def lookup_customer_by_ident(ident):
    """Find customer by username, email, or phone (flexible formatting)."""
    if not ident:
        return None
    clean_ident = str(ident).strip()
    norm_phone = normalize_phone_number(clean_ident)

    # 1. Direct match on phone, email, or username
    user = CustomUser.objects.filter(
        Q(phone=clean_ident) | Q(phone=norm_phone) | Q(email__iexact=clean_ident) | Q(username__iexact=clean_ident)
    ).first()
    if user:
        return user

    # 2. Check formatted phones in database
    if len(norm_phone) == 10:
        for candidate in CustomUser.objects.exclude(phone__isnull=True).exclude(phone=''):
            cand_digits = re.sub(r'\D', '', candidate.phone)
            if cand_digits.endswith(norm_phone):
                return candidate
    return None


# ==============================================================================
# Cart Utility Helper
# ==============================================================================
def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # If user has an anonymous session cart, merge items
        session_key = request.session.session_key
        if session_key:
            session_cart = Cart.objects.filter(session_key=session_key).first()
            if session_cart and session_cart != cart:
                for item in session_cart.items.all():
                    cart_item, c = CartItem.objects.get_or_create(cart=cart, product=item.product)
                    if not c:
                        cart_item.quantity += item.quantity
                        cart_item.save()
                    else:
                        cart_item.quantity = item.quantity
                        cart_item.save()
                session_cart.delete()
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
        return cart


# ==============================================================================
# Public & Customer Views
# ==============================================================================
def root_redirect(request):
    """
    Entry point for http://127.0.0.1:8000/.
    Always redirects visitors to the Login page so clicking the root link opens the login page.
    """
    return redirect('login')


def home(request):
    featured_products = Product.objects.filter(is_featured=True).select_related('category')[:8]
    deal_products = Product.objects.filter(is_deal=True).select_related('category')[:6]
    categories = Category.objects.annotate(product_count=Count('products'))[:14]
    recent_tech = Product.objects.all().select_related('category').order_by('-created_at')[:8]

    context = {
        'featured_products': featured_products,
        'deal_products': deal_products,
        'categories': categories,
        'recent_tech': recent_tech,
    }
    return render(request, 'home.html', context)


def product_list(request):
    products = Product.objects.select_related('category').all()
    categories = Category.objects.annotate(product_count=Count('products'))

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q)
        )

    # Category filter
    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)

    # Brand filter
    brand = request.GET.get('brand', '').strip()
    if brand:
        products = products.filter(brand__iexact=brand)

    # Price range filter
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except Exception:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except Exception:
            pass

    # Availability filter
    in_stock = request.GET.get('in_stock', '')
    if in_stock == '1':
        products = products.filter(stock__gt=0)

    # Deals / Spotlight filter
    deal = request.GET.get('deal', '')
    if deal == '1':
        products = products.filter(is_deal=True)

    # Featured Tech filter
    featured = request.GET.get('featured', '')
    if featured == '1':
        products = products.filter(is_featured=True)

    # Customer Rating filter
    rating_min = request.GET.get('rating_min', '').strip()
    if rating_min:
        try:
            products = products.filter(rating__gte=Decimal(rating_min))
        except Exception:
            pass

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-rating')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        # Default: featured first, then newest
        products = products.order_by('-is_featured', '-is_deal', '-created_at')

    # Available brands with product count for filter sidebar
    brand_counts = Product.objects.values('brand').annotate(count=Count('id')).order_by('-count')
    all_brands = [b['brand'] for b in brand_counts]

    # Active filters list for chips and badge counts
    active_filters = []
    if selected_category:
        active_filters.append({'type': 'category', 'label': selected_category.name, 'param': 'category'})
    if brand:
        active_filters.append({'type': 'brand', 'label': f"Brand: {brand}", 'param': 'brand'})
    if min_price and max_price:
        active_filters.append({'type': 'price', 'label': f"₹{min_price} - ₹{max_price}", 'param': 'price'})
    elif min_price:
        active_filters.append({'type': 'price', 'label': f"Above ₹{min_price}", 'param': 'min_price'})
    elif max_price:
        active_filters.append({'type': 'price', 'label': f"Under ₹{max_price}", 'param': 'max_price'})
    if in_stock == '1':
        active_filters.append({'type': 'stock', 'label': 'In Stock', 'param': 'in_stock'})
    if deal == '1':
        active_filters.append({'type': 'deal', 'label': 'Spotlight Deals', 'param': 'deal'})
    if featured == '1':
        active_filters.append({'type': 'featured', 'label': 'Featured Only', 'param': 'featured'})
    if rating_min:
        active_filters.append({'type': 'rating', 'label': f"{rating_min}★ & Above", 'param': 'rating_min'})

    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'all_brands': all_brands,
        'brand_counts': brand_counts,
        'query': q,
        'current_brand': brand,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'in_stock': in_stock,
        'deal': deal,
        'featured': featured,
        'rating_min': rating_min,
        'active_filters': active_filters,
    }
    return render(request, 'products/list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.filter(category=product.category).exclude(pk=product.pk)[:4]

    # Parse specs into list of bullet points
    specs_list = [s.strip() for s in product.specs.split('\n') if s.strip()] if product.specs else []

    context = {
        'product': product,
        'related_products': related_products,
        'specs_list': specs_list,
    }
    return render(request, 'products/detail.html', context)


def cart_view(request):
    cart = get_or_create_cart(request)
    context = {
        'cart': cart,
        'items': cart.items.select_related('product').all(),
    }
    return render(request, 'cart.html', context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart = get_or_create_cart(request)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    if quantity < 1:
        quantity = 1

    if product.stock < 1:
        messages.error(request, f"Sorry, {product.name} is currently out of stock.")
        return redirect('product_detail', slug=product.slug)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if cart_item.quantity + quantity > product.stock:
            cart_item.quantity = product.stock
            messages.warning(request, f"Quantity adjusted to available stock ({product.stock} units).")
        else:
            cart_item.quantity += quantity
            messages.success(request, f"Added {quantity} more '{product.name}' to your cart.")
    else:
        cart_item.quantity = min(quantity, product.stock)
        messages.success(request, f"'{product.name}' added to your cart!")
    cart_item.save()

    # Buy Now redirect
    action = request.POST.get('action')
    if action == 'buy_now':
        return redirect('checkout')

    # If AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'cart_count': cart.total_items,
            'cart_subtotal': str(cart.subtotal),
            'message': f"Added '{product.name}' to your cart."
        })

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('cart')


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    if quantity <= 0:
        item.delete()
        messages.info(request, f"Removed '{item.product.name}' from your cart.")
    elif quantity > item.product.stock:
        item.quantity = item.product.stock
        item.save()
        messages.warning(request, f"Maximum available stock for {item.product.name} is {item.product.stock}.")
    else:
        item.quantity = quantity
        item.save()
        messages.success(request, "Cart updated successfully.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'item_quantity': item.quantity if quantity > 0 else 0,
            'item_total': str(item.line_total) if quantity > 0 else '0',
            'subtotal': str(cart.subtotal),
            'grand_total': str(cart.grand_total),
            'cart_count': cart.total_items,
        })

    return redirect('cart')


@require_POST
def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    product_name = item.product.name
    item.delete()
    messages.info(request, f"Removed '{product_name}' from your cart.")
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url == 'checkout':
        if cart.total_items == 0:
            messages.warning(request, "Your cart is now empty. Add items before checking out.")
            return redirect('product_list')
        return redirect('checkout')
    return redirect('cart')


@require_POST
def bulk_remove_from_cart(request):
    cart = get_or_create_cart(request)
    raw_item_ids = request.POST.getlist('selected_items')
    item_ids = []
    for item_id in raw_item_ids:
        try:
            item_ids.append(int(item_id))
        except (ValueError, TypeError):
            pass

    if not item_ids:
        messages.warning(request, "No items selected to delete.")
    else:
        deleted_count, _ = CartItem.objects.filter(cart=cart, id__in=item_ids).delete()
        messages.info(request, f"Successfully removed {deleted_count} item(s) from your order.")

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url == 'checkout':
        if cart.total_items == 0:
            messages.warning(request, "Your cart is now empty. Add items before checking out.")
            return redirect('product_list')
        return redirect('checkout')
    return redirect('cart')


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    if cart.total_items == 0:
        messages.warning(request, "Your shopping cart is empty! Add products before checking out.")
        return redirect('product_list')

    user_addresses = Address.objects.filter(user=request.user)

    if request.method == 'POST':
        address_id = request.POST.get('selected_address')
        payment_method = request.POST.get('payment_method', Order.PAY_UPI)

        # Fallback to default or first saved address if not explicitly selected
        if not address_id and user_addresses.exists():
            default_addr = user_addresses.filter(is_default=True).first() or user_addresses.first()
            address_id = str(default_addr.id)

        shipping_name = ""
        shipping_phone = ""
        shipping_line1 = ""
        shipping_line2 = ""
        shipping_landmark = ""
        shipping_city = ""
        shipping_state = ""
        shipping_pincode = ""

        addr = None
        if address_id and address_id != 'new':
            try:
                addr = Address.objects.filter(pk=int(address_id), user=request.user).first()
            except (ValueError, TypeError):
                addr = None

        if addr:
            shipping_name = addr.full_name
            shipping_phone = addr.phone
            shipping_line1 = addr.address_line1
            shipping_line2 = addr.address_line2
            shipping_landmark = addr.landmark
            shipping_city = addr.city
            shipping_state = addr.state
            shipping_pincode = addr.pincode
        else:
            form = AddressForm(request.POST)
            if form.is_valid():
                new_addr = form.save(commit=False)
                new_addr.user = request.user
                if not user_addresses.exists():
                    new_addr.is_default = True
                new_addr.save()
                shipping_name = new_addr.full_name
                shipping_phone = new_addr.phone
                shipping_line1 = new_addr.address_line1
                shipping_line2 = new_addr.address_line2
                shipping_landmark = new_addr.landmark
                shipping_city = new_addr.city
                shipping_state = new_addr.state
                shipping_pincode = new_addr.pincode
            else:
                messages.error(request, "Please enter all required address details.")
                return render(request, 'checkout.html', {
                    'cart': cart,
                    'addresses': user_addresses,
                    'address_form': form,
                    'payment_setting': PaymentSetting.get_settings(),
                })

        # Determine items to checkout based on selection
        selected_item_ids = request.POST.getlist('selected_items')
        if selected_item_ids:
            checkout_items = cart.items.filter(id__in=selected_item_ids).select_related('product')
        else:
            checkout_items = cart.items.select_related('product').all()

        if not checkout_items.exists():
            messages.error(request, "Please select at least one item from the order summary to proceed.")
            return redirect('checkout')

        # Stock pre-check to prevent overselling on selected items
        for item in checkout_items:
            if item.product.stock < item.quantity:
                messages.error(request, f"Sorry, '{item.product.name}' only has {item.product.stock} units remaining in stock. Please adjust your cart.")
                return redirect('checkout')

        # Calculate accurate totals for selected items
        checkout_subtotal = sum(item.line_total for item in checkout_items)
        checkout_delivery = 0 if (checkout_subtotal >= 500 or checkout_subtotal == 0) else 99
        checkout_gst = round(float(checkout_subtotal) * 0.18, 2)
        checkout_grand_total = checkout_subtotal + checkout_delivery

        # Validate against store Payment Settings
        payment_setting = PaymentSetting.get_settings()
        if payment_method == Order.PAY_UPI and not payment_setting.enable_upi:
            messages.error(request, "UPI payment is currently unavailable. Please select another payment method.")
            return redirect('checkout')
        elif payment_method == Order.PAY_CARD and not payment_setting.enable_card:
            messages.error(request, "Credit / Debit Card payment is currently unavailable.")
            return redirect('checkout')
        elif payment_method == Order.PAY_NETBANKING and not payment_setting.enable_netbanking:
            messages.error(request, "Net Banking is currently unavailable.")
            return redirect('checkout')
        elif payment_method == Order.PAY_COD:
            if not payment_setting.enable_cod:
                messages.error(request, "Cash on Delivery is currently disabled by store management.")
                return redirect('checkout')
            if checkout_grand_total > payment_setting.cod_max_limit:
                messages.error(request, f"Cash on Delivery is only available for orders up to ₹{payment_setting.cod_max_limit:,.2f}. Please select an online payment method.")
                return redirect('checkout')

        # Cash on Delivery (COD) OTP Verification Check
        if payment_method == Order.PAY_COD:
            cod_otp = request.POST.get('cod_otp', '').strip()
            session_cod_otp = request.session.get('cod_otp_code')
            verified = False

            otp_record = OTPVerification.objects.filter(
                purpose=OTPVerification.PURPOSE_COD,
                otp_code=cod_otp,
                is_verified=False
            ).order_by('-created_at').first()

            if otp_record and not otp_record.is_expired():
                otp_record.is_verified = True
                otp_record.user = request.user
                otp_record.save()
                verified = True
            elif session_cod_otp and session_cod_otp == cod_otp:
                verified = True

            if not verified:
                messages.error(request, "Cash on Delivery verification failed: Please enter the 6-digit OTP code to confirm your order.")
                return render(request, 'checkout.html', {
                    'cart': cart,
                    'addresses': user_addresses,
                    'address_form': AddressForm(),
                    'selected_payment_method': 'COD',
                    'cod_error': 'Invalid or missing OTP code. Please enter the 6-digit OTP.',
                    'payment_setting': payment_setting,
                })

            # Create Order for Cash on Delivery (Direct Placement)
            order = Order.objects.create(
                user=request.user,
                shipping_name=shipping_name,
                shipping_phone=shipping_phone,
                shipping_address_line1=shipping_line1,
                shipping_address_line2=shipping_line2,
                shipping_landmark=shipping_landmark,
                shipping_city=shipping_city,
                shipping_state=shipping_state,
                shipping_pincode=shipping_pincode,
                subtotal=checkout_subtotal,
                delivery_charge=checkout_delivery,
                gst_amount=checkout_gst,
                total_amount=checkout_grand_total,
                payment_method=Order.PAY_COD,
                payment_status=Order.PAY_STATUS_PENDING,
                order_status=Order.STATUS_CONFIRMED,
                estimated_delivery_text="Tomorrow by 2:00 PM",
                current_location="Bhiwandi Central Fulfillment Center"
            )

            # Create Order Items and adjust stock
            default_seller = CustomUser.objects.filter(role=CustomUser.ROLE_SELLER, is_active=True).first()
            for item in checkout_items:
                item_seller = item.product.seller or default_seller
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    seller=item_seller,
                    product_name=item.product.name,
                    brand=item.product.brand,
                    model_number=item.product.model_number,
                    warranty_info=item.product.warranty_info,
                    image_url=item.product.display_image,
                    price=item.product.price,
                    mrp=item.product.mrp,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save()

            # Delete only checked out items
            checkout_items.delete()

            # Clear COD OTP session keys
            request.session.pop('cod_otp_code', None)
            request.session.pop('cod_otp_id', None)
            request.session.pop('cod_phone', None)

            # Notifications:
            # 1. Alert Store Admin
            send_system_notification(
                for_admin=True,
                title=f"New COD Order Placed: #{order.order_number}",
                message=f"Customer {order.shipping_name} ({order.user.username}) placed a Cash on Delivery order for ₹{order.total_amount:,.2f} ({order.shipping_city}, {order.shipping_pincode}). Doorstep PIN: {order.delivery_pin}.",
                notification_type=Notification.TYPE_ORDER,
                icon='local_shipping',
                link_url=reverse('admin_order_detail', kwargs={'order_number': order.order_number}),
                order=order
            )
            # 2. Alert Customer
            send_system_notification(
                recipient=order.user,
                title=f"Order Confirmed: #{order.order_number}",
                message=f"Your Cash on Delivery order for ₹{order.total_amount:,.2f} is placed! Estimated delivery: {order.estimated_delivery_text}. Doorstep PIN: {order.delivery_pin}.",
                notification_type=Notification.TYPE_ORDER,
                icon='task_alt',
                link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
                order=order
            )
            # 3. Alert Sellers
            seller_ids = order.items.filter(seller__isnull=False).values_list('seller_id', flat=True).distinct()
            for s_id in seller_ids:
                s_user = CustomUser.objects.filter(id=s_id).first()
                if s_user:
                    send_system_notification(
                        recipient=s_user,
                        title=f"New Order to Prepare: #{order.order_number}",
                        message=f"You have items to pack for Order #{order.order_number} ({order.shipping_city}). Please prepare them for courier pickup.",
                        notification_type=Notification.TYPE_ORDER,
                        icon='inventory_2',
                        link_url=reverse('seller_order_detail', kwargs={'order_number': order.order_number}),
                        order=order
                    )

            messages.success(request, f"Cash on Delivery Order #{order.order_number} successfully placed! Doorstep PIN: {order.delivery_pin}")
            return redirect('order_success', order_number=order.order_number)

        else:
            # Online Payments (Net Banking, Cards, UPI, Wallets, EMI)
            # Create Pending Order and redirect customer to the Bank Payment Gateway portal
            bank_name = request.POST.get('bank_name', 'HDFC Bank')
            bank_account_mode = request.POST.get('bank_account_mode', 'saved')
            bank_account_holder = request.POST.get('bank_account_holder', request.user.get_full_name() or request.user.username)
            bank_account_type = request.POST.get('bank_account_type', 'Savings Account')
            bank_account_number = request.POST.get('bank_account_number', '50100482193847')
            bank_ifsc = request.POST.get('bank_ifsc', 'HDFC0000123')
            bank_customer_id = request.POST.get('bank_customer_id', f"CUST_{request.user.id}")
            bank_branch = request.POST.get('bank_branch', 'Coimbatore Main Branch')

            request.session['selected_bank_name'] = bank_name
            request.session['bank_account_mode'] = bank_account_mode
            request.session['bank_account_holder'] = bank_account_holder
            request.session['bank_account_type'] = bank_account_type
            request.session['bank_account_number'] = bank_account_number
            request.session['bank_ifsc'] = bank_ifsc
            request.session['bank_customer_id'] = bank_customer_id
            request.session['bank_branch'] = bank_branch

            order = Order.objects.create(
                user=request.user,
                shipping_name=shipping_name,
                shipping_phone=shipping_phone,
                shipping_address_line1=shipping_line1,
                shipping_address_line2=shipping_line2,
                shipping_landmark=shipping_landmark,
                shipping_city=shipping_city,
                shipping_state=shipping_state,
                shipping_pincode=shipping_pincode,
                subtotal=checkout_subtotal,
                delivery_charge=checkout_delivery,
                gst_amount=checkout_gst,
                total_amount=checkout_grand_total,
                payment_method=payment_method,
                payment_status=Order.PAY_STATUS_PENDING,
                order_status=Order.STATUS_CONFIRMED,
                estimated_delivery_text="Tomorrow by 2:00 PM",
                current_location="Bhiwandi Central Fulfillment Center"
            )

            # Create Order Items and reserve inventory stock
            default_seller = CustomUser.objects.filter(role=CustomUser.ROLE_SELLER, is_active=True).first()
            for item in checkout_items:
                item_seller = item.product.seller or default_seller
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    seller=item_seller,
                    product_name=item.product.name,
                    brand=item.product.brand,
                    model_number=item.product.model_number,
                    warranty_info=item.product.warranty_info,
                    image_url=item.product.display_image,
                    price=item.product.price,
                    mrp=item.product.mrp,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
                item.product.stock = max(0, item.product.stock - item.quantity)
                item.product.save()

            # Delete only checked out items from cart
            checkout_items.delete()

            # Redirect to Bank Payment Gateway screen
            return redirect('payment_gateway', order_number=order.order_number)

    address_form = AddressForm()
    payment_setting = PaymentSetting.get_settings()
    context = {
        'cart': cart,
        'addresses': user_addresses,
        'address_form': address_form,
        'payment_setting': payment_setting,
    }
    return render(request, 'checkout.html', context)


@login_required
def payment_gateway(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    bank_name = request.session.get('selected_bank_name', 'HDFC Bank')
    account_holder = request.session.get('bank_account_holder', request.user.get_full_name() or request.user.username)
    account_type = request.session.get('bank_account_type', 'Savings Account')
    raw_account = request.session.get('bank_account_number', '50100482193847')
    bank_ifsc = request.session.get('bank_ifsc', 'HDFC0000123')
    customer_id = request.session.get('bank_customer_id', f"CUST_{request.user.id}")
    bank_branch = request.session.get('bank_branch', 'Coimbatore Main Branch')

    if len(raw_account) >= 4:
        masked_account = f"•••• •••• {raw_account[-4:]}"
    else:
        masked_account = "•••• •••• 4821"

    # Generate 6-digit demo bank authorization OTP
    demo_otp = f"{random.randint(100000, 999999)}"
    request.session['bank_demo_otp'] = demo_otp

    context = {
        'order': order,
        'bank_name': bank_name,
        'account_holder': account_holder,
        'account_type': account_type,
        'account_number': raw_account,
        'masked_account': masked_account,
        'bank_ifsc': bank_ifsc,
        'customer_id': customer_id,
        'bank_branch': bank_branch,
        'demo_otp': demo_otp,
    }
    return render(request, 'payment_gateway.html', context)


@login_required
@require_POST
def payment_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if order.order_status == Order.STATUS_CANCELLED:
        messages.error(request, f"Order #{order.order_number} has already been cancelled.")
        return redirect('order_history')

    # Mark Order as PAID
    order.payment_status = Order.PAY_STATUS_PAID
    order.save()

    bank_name = request.session.get('selected_bank_name', 'Bank')

    # Bi-directional Notifications:
    # 1. Alert Store Admin
    send_system_notification(
        for_admin=True,
        title=f"Prepaid Order Confirmed: #{order.order_number}",
        message=f"Customer {order.shipping_name} ({order.user.username}) successfully paid ₹{order.total_amount:,.2f} via {order.get_payment_method_display()} ({bank_name}).",
        notification_type=Notification.TYPE_ORDER,
        icon='payments',
        link_url=reverse('admin_order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )
    # 2. Alert Customer
    send_system_notification(
        recipient=order.user,
        title=f"Payment Successful: Order #{order.order_number}",
        message=f"Your payment of ₹{order.total_amount:,.2f} via {order.get_payment_method_display()} was verified. We are preparing your order for shipment.",
        notification_type=Notification.TYPE_ORDER,
        icon='task_alt',
        link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )

    messages.success(request, f"Payment of ₹{order.total_amount:,.2f} successfully authorized via {bank_name}! Order #{order.order_number} confirmed.")
    return redirect('order_success', order_number=order.order_number)


@login_required
@require_POST
def payment_cancel(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    # Restore reserved stock on cancellation (only if not already cancelled)
    if order.order_status != Order.STATUS_CANCELLED:
        for item in order.items.all():
            if item.product:
                item.product.stock = item.product.stock + item.quantity
                item.product.save()

    order.payment_status = Order.PAY_STATUS_FAILED
    order.order_status = Order.STATUS_CANCELLED
    order.save()

    messages.warning(request, f"Payment transaction for Order #{order.order_number} was cancelled. You can retry with another payment method.")
    return redirect('checkout')


# ==============================================================================
# Customer Address Management Views
# ==============================================================================
@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-id')
    form = AddressForm()
    return render(request, 'addresses/list.html', {'addresses': addresses, 'form': form})


@login_required
def address_add(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            if not Address.objects.filter(user=request.user).exists():
                addr.is_default = True
            addr.save()
            messages.success(request, "Delivery address saved successfully!")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('address_list')
        else:
            messages.error(request, "Please check the address form details.")
    return redirect('address_list')


@login_required
def address_edit(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=addr)
        if form.is_valid():
            form.save()
            messages.success(request, f"Address '{addr.full_name}' updated successfully!")
            if next_url:
                return redirect(next_url)
            return redirect('address_list')
        else:
            messages.error(request, "Please correct the errors in the address form.")
    else:
        form = AddressForm(instance=addr)

    return render(request, 'addresses/edit.html', {
        'form': form,
        'address': addr,
        'next_url': next_url,
    })


@login_required
@require_POST
def address_delete(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    name = addr.full_name
    was_default = addr.is_default
    addr.delete()
    if was_default:
        next_addr = Address.objects.filter(user=request.user).first()
        if next_addr:
            next_addr.is_default = True
            next_addr.save()
    messages.success(request, f"Delivery address for '{name}' was removed successfully.")
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('address_list')


# ==============================================================================
# Customer Account Profile View
# ==============================================================================
@login_required(login_url='login')
def customer_profile(request):
    """
    Customer Profile View (also serves as general personal profile).
    Allows customers to view and update personal details, phone number,
    profile picture, view membership tier, wallet balance, recent orders,
    saved addresses, and update their account password.
    """
    user = request.user
    role_view = request.GET.get('view')

    # If seller or delivery partner visits without explicitly requesting personal view,
    # guide them directly to their dedicated role-specific profile portal
    if user.is_seller_user() and role_view != 'personal':
        return redirect('seller_profile')
    if user.is_delivery_partner() and role_view != 'personal':
        return redirect('delivery_profile')

    pwd_form = ProfilePasswordChangeForm(user=user)
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        if action == 'change_password':
            pwd_form = ProfilePasswordChangeForm(user=user, data=request.POST)
            if pwd_form.is_valid():
                new_pwd = pwd_form.cleaned_data['new_password']
                user.set_password(new_pwd)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed successfully!")
                return redirect('customer_profile')
            else:
                form = CustomerProfileForm(instance=user)
                messages.error(request, "Please check the password errors below.")
        else:
            form = CustomerProfileForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Your profile details have been updated successfully!")
                return redirect('customer_profile')
            else:
                messages.error(request, "Please check the errors in your profile form.")
    else:
        form = CustomerProfileForm(instance=user)

    orders_qs = Order.objects.filter(user=user).order_by('-id')
    orders_count = orders_qs.count()
    recent_orders = orders_qs[:5]

    addresses_qs = Address.objects.filter(user=user).order_by('-is_default', '-id')
    addresses_count = addresses_qs.count()
    recent_addresses = addresses_qs[:3]

    active_orders_count = orders_qs.filter(
        order_status__in=[Order.STATUS_CONFIRMED, Order.STATUS_PACKED, Order.STATUS_IN_TRANSIT, Order.STATUS_OUT_FOR_DELIVERY]
    ).count()

    context = {
        'form': form,
        'pwd_form': pwd_form,
        'orders_count': orders_count,
        'recent_orders': recent_orders,
        'active_orders_count': active_orders_count,
        'addresses_count': addresses_count,
        'recent_addresses': recent_addresses,
    }
    return render(request, 'customer/profile.html', context)


@login_required
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'order_success.html', {'order': order})


@login_required
def order_history(request):
    """
    Customer Order History page matching the design in code.html & DESIGN.md
    Displays customer profile header banner, active in-flight tracking, and past orders.
    """
    user_orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')

    filter_status = request.GET.get('status', 'all')
    search_q = request.GET.get('q', '').strip()

    if search_q:
        user_orders = user_orders.filter(
            Q(order_number__icontains=search_q) |
            Q(items__product_name__icontains=search_q) |
            Q(items__brand__icontains=search_q)
        ).distinct()

    if filter_status == 'active':
        user_orders = user_orders.filter(
            order_status__in=[
                Order.STATUS_CONFIRMED,
                Order.STATUS_PACKED,
                Order.STATUS_IN_TRANSIT,
                Order.STATUS_OUT_FOR_DELIVERY
            ]
        )
    elif filter_status == 'delivered':
        user_orders = user_orders.filter(order_status=Order.STATUS_DELIVERED)
    elif filter_status == 'cancelled':
        user_orders = user_orders.filter(order_status=Order.STATUS_CANCELLED)

    all_user_orders = Order.objects.filter(user=request.user)
    total_orders_count = all_user_orders.count()
    active_deliveries_count = all_user_orders.filter(
        order_status__in=[
            Order.STATUS_CONFIRMED,
            Order.STATUS_PACKED,
            Order.STATUS_IN_TRANSIT,
            Order.STATUS_OUT_FOR_DELIVERY
        ]
    ).count()
    saved_addresses = Address.objects.filter(user=request.user)
    saved_addresses_count = saved_addresses.count()

    total_savings = Decimal('0.00')
    for ord in all_user_orders:
        for item in ord.items.all():
            if item.mrp and item.mrp > item.price:
                total_savings += (item.mrp - item.price) * item.quantity

    cancelled_orders_count = all_user_orders.filter(order_status=Order.STATUS_CANCELLED).count()

    context = {
        'orders': user_orders,
        'filter_status': filter_status,
        'search_q': search_q,
        'total_orders_count': total_orders_count,
        'active_deliveries_count': active_deliveries_count,
        'cancelled_orders_count': cancelled_orders_count,
        'saved_addresses': saved_addresses[:2],
        'saved_addresses_count': saved_addresses_count,
        'total_savings': total_savings if total_savings > 0 else Decimal('34900.00'),
    }
    return render(request, 'orders/history.html', context)


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if order.user != request.user and not request.user.is_admin_user():
        messages.error(request, "You are not authorized to view this order.")
        return redirect('order_history')

    context = {
        'order': order,
        'items': order.items.all(),
    }
    return render(request, 'orders/detail.html', context)


@login_required
@require_POST
def customer_cancel_order(request, order_number):
    """
    Allows customers to cancel an active order (CONFIRMED, PACKED, IN_TRANSIT),
    restores product inventory, initiates refund for prepaid orders, and logs cancellation reason.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if order.user != request.user and not request.user.is_admin_user():
        messages.error(request, "You are not authorized to cancel this order.")
        return redirect('order_history')

    if not order.can_cancel:
        messages.error(
            request,
            f"Order #{order.order_number} cannot be cancelled as it is already {order.get_order_status_display().lower()}."
        )
        return redirect('order_detail', order_number=order.order_number)

    reason = request.POST.get('cancellation_reason', '').strip() or 'Cancelled by customer'
    order.cancellation_reason = reason

    # Restore inventory stock for all products in this order
    for item in order.items.all():
        if item.product:
            item.product.stock += item.quantity
            item.product.save()

    # Update order and payment status
    order.order_status = Order.STATUS_CANCELLED

    if order.payment_status == Order.PAY_STATUS_PAID:
        order.payment_status = Order.PAY_STATUS_REFUNDED
        refund_note = f"Full refund of ₹{order.total_amount:,.2f} has been initiated to your original {order.get_payment_method_display()} payment source (expected in 2-4 business days)."
    else:
        order.payment_status = Order.PAY_STATUS_FAILED
        refund_note = "As this was Cash on Delivery / unpaid, no payment deduction was incurred."

    order.save()

    # Bi-directional Notifications:
    # 1. Alert Store Admin
    send_system_notification(
        for_admin=True,
        title=f"Order Cancelled by Customer: #{order.order_number}",
        message=f"Customer {order.shipping_name} ({order.user.username}) cancelled order #{order.order_number}. Reason: {order.cancellation_reason}. Inventory has been restored.",
        notification_type=Notification.TYPE_ORDER,
        icon='cancel',
        link_url=reverse('admin_order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )
    # 2. Alert Customer
    send_system_notification(
        recipient=order.user,
        title=f"Order #{order.order_number} Cancelled",
        message=f"Your order #{order.order_number} has been cancelled. {refund_note}",
        notification_type=Notification.TYPE_ORDER,
        icon='cancel',
        link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )
    # 3. Alert Sellers
    seller_ids = order.items.filter(seller__isnull=False).values_list('seller_id', flat=True).distinct()
    for s_id in seller_ids:
        s_user = CustomUser.objects.filter(id=s_id).first()
        if s_user:
            send_system_notification(
                recipient=s_user,
                title=f"Order Cancelled: #{order.order_number}",
                message=f"Order #{order.order_number} was cancelled by customer {order.shipping_name}. Restocked items in your catalog.",
                notification_type=Notification.TYPE_ORDER,
                icon='cancel',
                link_url=reverse('seller_order_detail', kwargs={'order_number': order.order_number}),
                order=order
            )

    messages.success(
        request,
        f"Order #{order.order_number} has been cancelled successfully. {refund_note}"
    )

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('order_detail', order_number=order.order_number)


@login_required
@require_POST
def customer_delete_order(request, order_number):
    """
    Allows a customer to delete an order from their order history (e.g. cancelled or past orders).
    Restores product inventory if deleting an uncancelled active order.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if order.user != request.user and not request.user.is_admin_user():
        messages.error(request, "You are not authorized to delete this order.")
        return redirect('order_history')

    num = order.order_number
    # If order is active and not cancelled, restore inventory
    if order.order_status in [Order.STATUS_CONFIRMED, Order.STATUS_PACKED, Order.STATUS_IN_TRANSIT, Order.STATUS_OUT_FOR_DELIVERY]:
        for item in order.items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.save()

    send_system_notification(
        for_admin=True,
        title=f"Order Removed by Customer: #{num}",
        message=f"Customer {request.user.username} deleted order #{num} from their account history.",
        notification_type=Notification.TYPE_ORDER,
        icon='delete_sweep',
    )

    order.delete()
    messages.success(request, f"Order #{num} has been successfully deleted from your history.")
    return redirect('order_history')


@login_required
@require_POST
def customer_bulk_delete_orders(request):
    """
    Allows customers to select multiple orders (or clear all cancelled orders) and delete them in bulk.
    """
    action = request.POST.get('action')
    order_ids = request.POST.getlist('order_ids')

    if action == 'clear_cancelled':
        cancelled_orders = Order.objects.filter(user=request.user, order_status=Order.STATUS_CANCELLED)
        count = cancelled_orders.count()
        if count > 0:
            cancelled_orders.delete()
            send_system_notification(
                for_admin=True,
                title="Cancelled Orders Cleared",
                message=f"Customer {request.user.username} cleared all {count} cancelled order(s) from history.",
                notification_type=Notification.TYPE_ORDER,
                icon='delete_sweep',
            )
            messages.success(request, f"Successfully cleared all {count} cancelled order(s) from your order history.")
        else:
            messages.info(request, "No cancelled orders to delete.")
        return redirect('order_history')

    if not order_ids:
        messages.warning(request, "Please select at least one order to delete.")
        return redirect('order_history')

    orders_to_delete = Order.objects.filter(user=request.user, order_number__in=order_ids)
    count = orders_to_delete.count()

    # If deleting active orders, restore inventory
    for ord in orders_to_delete:
        if ord.order_status in [Order.STATUS_CONFIRMED, Order.STATUS_PACKED, Order.STATUS_IN_TRANSIT, Order.STATUS_OUT_FOR_DELIVERY]:
            for item in ord.items.all():
                if item.product:
                    item.product.stock += item.quantity
                    item.product.save()

    orders_to_delete.delete()

    send_system_notification(
        for_admin=True,
        title="Orders Bulk Deleted by Customer",
        message=f"Customer {request.user.username} bulk deleted {count} order(s) from their history.",
        notification_type=Notification.TYPE_ORDER,
        icon='delete_sweep',
    )

    messages.success(request, f"Successfully deleted {count} selected order(s) from your order history.")
    return redirect('order_history')


@login_required
def order_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if order.user != request.user and not request.user.is_admin_user():
        messages.error(request, "You are not authorized to access this invoice.")
        return redirect('order_history')

    # Calculate 9% CGST and 9% SGST breakdown
    taxable_amount = round(float(order.subtotal) / 1.18, 2)
    cgst = round((float(order.subtotal) - taxable_amount) / 2, 2)
    sgst = cgst

    context = {
        'order': order,
        'items': order.items.all(),
        'taxable_amount': taxable_amount,
        'cgst': cgst,
        'sgst': sgst,
    }
    return render(request, 'orders/invoice.html', context)


def pincode_check(request):
    pincode = request.GET.get('pincode', '').strip()
    if len(pincode) == 6 and pincode.isdigit():
        prefix = pincode[:2]
        city_map = {
            '64': ('Coimbatore', 'Tamil Nadu'),
            '60': ('Chennai', 'Tamil Nadu'),
            '62': ('Madurai', 'Tamil Nadu'),
            '63': ('Salem', 'Tamil Nadu'),
            '40': ('Mumbai', 'Maharashtra'),
            '41': ('Pune', 'Maharashtra'),
            '11': ('New Delhi', 'Delhi NCR'),
            '12': ('Gurugram', 'Haryana'),
            '20': ('Noida', 'Uttar Pradesh'),
            '56': ('Bengaluru', 'Karnataka'),
            '50': ('Hyderabad', 'Telangana'),
            '70': ('Kolkata', 'West Bengal'),
            '38': ('Ahmedabad', 'Gujarat'),
        }
        city, state = city_map.get(prefix, ('Coimbatore', 'Tamil Nadu'))
        return JsonResponse({
            'valid': True,
            'pincode': pincode,
            'city': city,
            'state': state,
            'estimated_date': 'Tomorrow by 2:00 PM',
            'express_available': True,
            'message': f"Delivering to {city} {pincode} by Tomorrow, 2:00 PM with Priority Air Express."
        })
    return JsonResponse({
        'valid': False,
        'message': 'Please enter a valid 6-digit Indian PIN code.'
    })


# ==============================================================================
# Authentication Views (with OTP Verification for Customer Role)
# ==============================================================================
def user_register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CustomerRegisterForm(request.POST)
        if form.is_valid():
            cleaned_phone = normalize_phone_number(form.cleaned_data['phone'])
            otp_code = f"{random.randint(100000, 999999)}"
            otp_record = OTPVerification.objects.create(
                phone_or_email=cleaned_phone,
                otp_code=otp_code,
                purpose=OTPVerification.PURPOSE_REGISTRATION,
                session_payload={
                    'username': form.cleaned_data['username'],
                    'email': form.cleaned_data['email'],
                    'password': form.cleaned_data['password1'],
                    'first_name': form.cleaned_data['first_name'],
                    'last_name': form.cleaned_data['last_name'],
                    'phone': cleaned_phone,
                    'gst_number': form.cleaned_data.get('gst_number', ''),
                    'account_type': form.cleaned_data.get('account_type', 'CUSTOMER'),
                    'store_name': form.cleaned_data.get('store_name', ''),
                },
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            request.session['registration_otp_id'] = otp_record.id
            messages.success(request, f"Registration OTP sent to {cleaned_phone}! For Demo testing: Use OTP {otp_code}")
            return redirect('verify_registration_otp')
        else:
            messages.error(request, "Please correct the errors in the registration form below.")
    else:
        form = CustomerRegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def verify_registration_otp(request):
    if request.user.is_authenticated:
        return redirect('home')

    otp_id = request.session.get('registration_otp_id')
    if not otp_id:
        messages.warning(request, "No pending registration found. Please register first.")
        return redirect('register')

    otp_record = get_object_or_404(OTPVerification, id=otp_id, is_verified=False)

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if otp_record.is_expired():
                messages.error(request, "This OTP has expired. Please click 'Resend OTP' to get a new code.")
            elif otp_record.otp_code != entered_otp:
                messages.error(request, "Incorrect OTP code. Please enter the valid 6-digit code.")
            else:
                # Mark OTP as verified
                otp_record.is_verified = True
                otp_record.save()

                # Create the user account in MySQL (Customer or Seller)
                payload = otp_record.session_payload
                target_username = payload['username']
                if CustomUser.objects.filter(username=target_username).exists():
                    cnt = 1
                    while CustomUser.objects.filter(username=f"{target_username}_{cnt}").exists():
                        cnt += 1
                    target_username = f"{target_username}_{cnt}"

                is_seller = payload.get('account_type') == 'SELLER'
                role = CustomUser.ROLE_SELLER if is_seller else CustomUser.ROLE_CUSTOMER
                store_name = payload.get('store_name', '').strip() if is_seller else ''
                if is_seller and not store_name:
                    store_name = f"{payload['first_name'] or payload['username']}'s Tech Store"

                user = CustomUser.objects.create_user(
                    username=target_username,
                    email=payload['email'],
                    password=payload['password'],
                    first_name=payload['first_name'],
                    last_name=payload['last_name'],
                    phone=payload.get('phone', ''),
                    gst_number=payload.get('gst_number', ''),
                    role=role,
                    store_name=store_name,
                    is_verified=True
                )
                otp_record.user = user
                otp_record.save()

                # Bi-directional Notifications:
                # 1. Alert Store Admin
                role_label = "Seller Partner" if is_seller else "Customer"
                send_system_notification(
                    for_admin=True,
                    title=f"New {role_label} Registered: {user.get_full_name() or user.username}",
                    message=f"New {role_label} account created for {user.get_full_name() or user.username} ({user.phone or user.email}). Verified via 6-digit OTP.",
                    notification_type=Notification.TYPE_REGISTRATION,
                    icon='storefront' if is_seller else 'person_add',
                    link_url=reverse('admin_customers')
                )
                # 2. Alert User
                welcome_msg = "Your Seller Account is verified! Start adding your products to the catalog." if is_seller else "Your customer account has been successfully verified! Enjoy fast nationwide delivery."
                send_system_notification(
                    recipient=user,
                    title="Welcome to Tech Mart!",
                    message=welcome_msg,
                    notification_type=Notification.TYPE_SYSTEM,
                    icon='waving_hand',
                    link_url=reverse('seller_dashboard') if is_seller else reverse('product_list')
                )

                # Clean session and log in user
                request.session.pop('registration_otp_id', None)
                login(request, user, backend='store.backends.EmailOrUsernameBackend')
                messages.success(request, f"Mobile number verified successfully! Welcome to Tech Mart, {user.first_name or user.username}!")
                if user.is_admin_user():
                    return redirect('admin_dashboard')
                elif user.is_seller_user():
                    return redirect('seller_dashboard')
                elif user.is_delivery_partner():
                    return redirect('delivery_dashboard')
                return redirect('home')
    else:
        form = OTPVerifyForm()

    return render(request, 'auth/verify_otp.html', {
        'form': form,
        'otp_record': otp_record,
        'title': 'Verify Customer Mobile Number',
        'target': otp_record.phone_or_email,
        'resend_url_name': 'resend_registration_otp'
    })


def resend_registration_otp(request):
    otp_id = request.session.get('registration_otp_id')
    if not otp_id:
        messages.warning(request, "No pending registration found.")
        return redirect('register')

    otp_record = get_object_or_404(OTPVerification, id=otp_id, is_verified=False)
    new_code = f"{random.randint(100000, 999999)}"
    otp_record.otp_code = new_code
    otp_record.expires_at = timezone.now() + timedelta(minutes=10)
    otp_record.save()

    messages.info(request, f"New OTP sent! For Demo testing: Use OTP {new_code}")
    return redirect('verify_registration_otp')


def request_login_otp(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = OTPLoginForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data['identifier'].strip()
            # Customer lookup by phone, email, or username (flexible formatting)
            customer = lookup_customer_by_ident(ident)

            if not customer:
                messages.error(request, f"No customer account found for '{ident}'. Please check or register.")
            elif customer.is_admin_user():
                messages.warning(request, "Admin accounts must log in with username and password on the standard sign-in page.")
            else:
                otp_code = f"{random.randint(100000, 999999)}"
                otp_record = OTPVerification.objects.create(
                    phone_or_email=ident,
                    otp_code=otp_code,
                    purpose=OTPVerification.PURPOSE_LOGIN,
                    user=customer,
                    expires_at=timezone.now() + timedelta(minutes=10)
                )
                request.session['login_otp_id'] = otp_record.id
                messages.success(request, f"Login OTP generated! For Demo testing: Use OTP {otp_code}")
                return redirect('verify_login_otp')
    else:
        form = OTPLoginForm()

    return render(request, 'auth/login_otp.html', {'form': form})


def verify_login_otp(request):
    if request.user.is_authenticated:
        return redirect('home')

    otp_id = request.session.get('login_otp_id')
    if not otp_id:
        messages.warning(request, "No login request in progress. Please enter your mobile or email.")
        return redirect('login_otp')

    otp_record = get_object_or_404(OTPVerification, id=otp_id, is_verified=False)

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            if otp_record.is_expired():
                messages.error(request, "This OTP has expired. Please click 'Resend OTP'.")
            elif otp_record.otp_code != entered_otp:
                messages.error(request, "Incorrect OTP code. Please enter the valid 6-digit code.")
            else:
                otp_record.is_verified = True
                otp_record.save()

                user = otp_record.user
                request.session.pop('login_otp_id', None)
                login(request, user, backend='store.backends.EmailOrUsernameBackend')

                messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                if user.is_admin_user():
                    return redirect('admin_dashboard')
                elif user.is_seller_user():
                    return redirect('seller_dashboard')
                elif user.is_delivery_partner():
                    return redirect('delivery_dashboard')
                return redirect('home')
    else:
        form = OTPVerifyForm()

    return render(request, 'auth/verify_otp.html', {
        'form': form,
        'otp_record': otp_record,
        'title': 'Customer Instant Login OTP',
        'target': otp_record.phone_or_email,
        'resend_url_name': 'resend_login_otp'
    })


def resend_login_otp(request):
    otp_id = request.session.get('login_otp_id')
    if not otp_id:
        messages.warning(request, "No login request in progress.")
        return redirect('login_otp')

    otp_record = get_object_or_404(OTPVerification, id=otp_id, is_verified=False)
    new_code = f"{random.randint(100000, 999999)}"
    otp_record.otp_code = new_code
    otp_record.expires_at = timezone.now() + timedelta(minutes=10)
    otp_record.save()

    messages.info(request, f"New login OTP sent! For Demo testing: Use OTP {new_code}")
    return redirect('verify_login_otp')



def user_login(request):
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            remember_me = request.POST.get('remember_me')
            if remember_me:
                # 2 weeks expiry (14 days = 1209600 seconds)
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)

            # Alert Admin about user login
            if not user.is_admin_user():
                send_system_notification(
                    for_admin=True,
                    title=f"User Logged In: {user.get_full_name() or user.username} ({user.get_role_display()})",
                    message=f"Account {user.get_full_name() or user.username} signed in to their account.",
                    notification_type=Notification.TYPE_LOGIN,
                    icon='login',
                    link_url=reverse('admin_customers')
                )

            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            
            if user.is_admin_user():
                return redirect('admin_dashboard')
            elif user.is_seller_user():
                return redirect('seller_dashboard')
            elif user.is_delivery_partner():
                return redirect('delivery_dashboard')
            
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = CustomerLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('login')


# ==============================================================================
# Interactive AJAX OTP Endpoints (Instant Mobile OTP Verification & Login)
# ==============================================================================
@require_POST
def api_send_otp(request):
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    raw_phone = data.get('phone', '')
    phone = normalize_phone_number(raw_phone)
    if not phone or len(phone) != 10:
        return JsonResponse({'success': False, 'message': 'Please enter a valid 10-digit Indian mobile number.'})

    # Prevent admin from using customer mobile OTP
    existing_user = lookup_customer_by_ident(phone)
    if existing_user and existing_user.is_admin_user():
        return JsonResponse({'success': False, 'message': 'Admin accounts cannot log in via OTP. Please use Admin Password login.'})

    is_new_user = existing_user is None
    otp_code = f"{random.randint(100000, 999999)}"
    purpose = OTPVerification.PURPOSE_REGISTRATION if is_new_user else OTPVerification.PURPOSE_LOGIN

    OTPVerification.objects.create(
        phone_or_email=phone,
        otp_code=otp_code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10)
    )

    return JsonResponse({
        'success': True,
        'otp': otp_code,
        'phone': phone,
        'is_new_user': is_new_user,
        'message': f'OTP sent successfully! (Demo Test OTP: {otp_code})'
    })


@require_POST
def api_verify_otp(request):
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    raw_phone = data.get('phone', '')
    phone = normalize_phone_number(raw_phone)
    entered_otp = data.get('otp', '').strip()
    full_name = data.get('name', '').strip()

    if not phone or not entered_otp:
        return JsonResponse({'success': False, 'message': 'Mobile number and OTP are required.'})

    otp_obj = OTPVerification.objects.filter(
        phone_or_email=phone,
        otp_code=entered_otp,
        is_verified=False
    ).order_by('-created_at').first()

    if not otp_obj:
        return JsonResponse({'success': False, 'message': 'Incorrect OTP code. Please enter the valid 6-digit code.'})

    if otp_obj.is_expired():
        return JsonResponse({'success': False, 'message': 'This OTP has expired. Please click Resend OTP.'})

    otp_obj.is_verified = True
    otp_obj.save()

    # Find existing customer or register new customer in MySQL
    user = lookup_customer_by_ident(phone)
    is_new = user is None
    if not user:
        base_username = f"user_{phone[-6:]}"
        username = base_username
        idx = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}_{idx}"
            idx += 1

        names = full_name.split(' ', 1) if full_name else ['Customer', '']
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ''

        user = CustomUser.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@customer.techmart.in",
            phone=phone,
            role=CustomUser.ROLE_CUSTOMER,
            is_verified=True
        )
        user.set_unusable_password()
        user.save()

        # Bi-directional Notifications:
        # 1. Alert Store Admin
        send_system_notification(
            for_admin=True,
            title=f"New Customer Registered: {user.get_full_name() or user.username}",
            message=f"New customer registered via instant mobile OTP ({phone}).",
            notification_type=Notification.TYPE_REGISTRATION,
            icon='person_add',
            link_url=reverse('admin_customers')
        )
        # 2. Alert Customer
        send_system_notification(
            recipient=user,
            title="Welcome to Tech Mart!",
            message="Your customer mobile account is active! Explore authentic electronics and exclusive member deals.",
            notification_type=Notification.TYPE_SYSTEM,
            icon='waving_hand',
            link_url=reverse('product_list')
        )

    otp_obj.user = user
    otp_obj.save()

    login(request, user, backend='store.backends.EmailOrUsernameBackend')
    messages.success(request, f"Mobile number verified! Welcome to Tech Mart, {user.first_name or user.username}!")

    next_url = request.GET.get('next') or request.POST.get('next')
    if not next_url or next_url == '/':
        if user.is_admin_user():
            next_url = reverse('admin_dashboard')
        elif user.is_seller_user():
            next_url = reverse('seller_dashboard')
        elif user.is_delivery_partner():
            next_url = reverse('delivery_dashboard')
        else:
            next_url = '/'
    return JsonResponse({'success': True, 'redirect_url': next_url})


@require_POST
def api_send_cod_otp(request):
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    phone = data.get('phone', '').strip().replace(' ', '').replace('+91', '').replace('-', '')
    if not phone and request.user.is_authenticated and request.user.phone:
        phone = request.user.phone

    if not phone or len(phone) < 10:
        phone = '9876543210'

    otp_code = f"{random.randint(100000, 999999)}"
    otp_obj = OTPVerification.objects.create(
        phone_or_email=phone,
        otp_code=otp_code,
        purpose=OTPVerification.PURPOSE_COD,
        user=request.user if request.user.is_authenticated else None,
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    request.session['cod_otp_id'] = otp_obj.id
    request.session['cod_otp_code'] = otp_code
    request.session['cod_phone'] = phone

    return JsonResponse({
        'success': True,
        'otp': otp_code,
        'phone': phone,
        'message': f'COD Order Verification OTP generated! (Demo Test OTP: {otp_code})'
    })


@require_POST
def api_verify_cod_otp(request):
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    entered_otp = data.get('otp', '').strip()
    session_otp = request.session.get('cod_otp_code')

    otp_record = OTPVerification.objects.filter(
        purpose=OTPVerification.PURPOSE_COD,
        otp_code=entered_otp,
        is_verified=False
    ).order_by('-created_at').first()

    if (otp_record and not otp_record.is_expired()) or (session_otp and session_otp == entered_otp):
        if otp_record:
            otp_record.is_verified = True
            otp_record.user = request.user if request.user.is_authenticated else None
            otp_record.save()
        return JsonResponse({
            'success': True,
            'message': 'OTP verified successfully! You can now place your Cash on Delivery order.'
        })


@require_POST
def api_send_password_reset_otp(request):
    """
    Generate and dispatch 6-digit OTP to user's registered mobile number for password reset.
    Works for Seller, Delivery Partner, Customer, and Admin accounts.
    """
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    raw_phone = data.get('phone', '').strip()
    if not raw_phone and request.user.is_authenticated and getattr(request.user, 'phone', None):
        raw_phone = request.user.phone

    phone = normalize_phone_number(raw_phone)
    if not phone or len(phone) != 10:
        return JsonResponse({'success': False, 'message': 'Please enter a valid 10-digit registered mobile number.'})

    user = None
    if request.user.is_authenticated:
        user = request.user
        if not user.phone:
            user.phone = phone
            user.save(update_fields=['phone'])
    else:
        user = lookup_customer_by_ident(phone)
        if not user:
            user = CustomUser.objects.filter(phone=phone).first()

    if not user:
        return JsonResponse({'success': False, 'message': f'No registered account found with mobile number +91 {phone}.'})

    otp_code = f"{random.randint(100000, 999999)}"
    OTPVerification.objects.create(
        phone_or_email=phone,
        otp_code=otp_code,
        purpose='PWD_RESET',
        user=user,
        expires_at=timezone.now() + timedelta(minutes=10)
    )

    masked_phone = f"{phone[:2]}******{phone[-2:]}" if len(phone) == 10 else phone
    return JsonResponse({
        'success': True,
        'otp': otp_code,
        'phone': phone,
        'masked_phone': masked_phone,
        'username': user.username,
        'message': f'Verification OTP sent to +91 {phone}! (Demo Test OTP: {otp_code})'
    })


@require_POST
def api_reset_password_otp(request):
    """
    Verify 6-digit mobile OTP and reset account password without requiring the old/current password.
    Supports Seller, Delivery Partner, and Customer accounts.
    """
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        data = request.POST

    raw_phone = data.get('phone', '').strip()
    if not raw_phone and request.user.is_authenticated and getattr(request.user, 'phone', None):
        raw_phone = request.user.phone

    phone = normalize_phone_number(raw_phone)
    entered_otp = data.get('otp', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()

    if not phone or len(phone) != 10:
        return JsonResponse({'success': False, 'message': 'Please enter a valid 10-digit registered mobile number.'})
    if not entered_otp:
        return JsonResponse({'success': False, 'message': 'Please enter the 6-digit verification OTP.'})
    if not new_password or len(new_password) < 6:
        return JsonResponse({'success': False, 'message': 'New password must be at least 6 characters long.'})
    if new_password != confirm_password:
        return JsonResponse({'success': False, 'message': 'New password and confirmation password do not match.'})

    otp_obj = OTPVerification.objects.filter(
        phone_or_email=phone,
        otp_code=entered_otp,
        is_verified=False
    ).order_by('-created_at').first()

    if not otp_obj:
        return JsonResponse({'success': False, 'message': 'Invalid OTP code. Please enter the valid 6-digit code.'})
    if otp_obj.is_expired():
        return JsonResponse({'success': False, 'message': 'This OTP has expired. Please click Resend Code.'})

    user = None
    if request.user.is_authenticated:
        user = request.user
    if not user:
        user = lookup_customer_by_ident(phone)
    if not user:
        user = CustomUser.objects.filter(phone=phone).first()

    if not user:
        return JsonResponse({'success': False, 'message': 'No registered account found with this mobile number.'})

    otp_obj.is_verified = True
    otp_obj.user = user
    otp_obj.save()

    user.set_password(new_password)
    user.save()

    if request.user.is_authenticated and request.user == user:
        update_session_auth_hash(request, user)

    redirect_url = ''
    if user.is_seller_user():
        redirect_url = reverse('seller_profile')
    elif user.is_delivery_partner():
        redirect_url = reverse('delivery_profile')
    elif user.is_admin_user():
        redirect_url = reverse('admin_dashboard')
    else:
        redirect_url = reverse('customer_profile')

    send_system_notification(
        recipient=user,
        title="Security Alert: Password Updated",
        message="Your account password was successfully reset and updated via Mobile OTP verification.",
        notification_type=Notification.TYPE_SYSTEM,
        icon='lock_reset',
        link_url=redirect_url
    )

    return JsonResponse({
        'success': True,
        'message': 'Password has been reset successfully! Your new password is now active.',
        'redirect_url': redirect_url
    })

    return JsonResponse({
        'success': False,
        'message': 'Incorrect OTP code. Please enter the valid 6-digit code or generate a new one.'
    })




# ==============================================================================
# Admin Dashboard & Management Views (Protected with role-based permissions)
# ==============================================================================
@admin_required
def admin_dashboard(request):
    total_sales = Order.objects.filter(payment_status=Order.PAY_STATUS_PAID).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_orders = Order.objects.count()
    active_deliveries = Order.objects.filter(
        order_status__in=[
            Order.STATUS_CONFIRMED,
            Order.STATUS_PACKED,
            Order.STATUS_IN_TRANSIT,
            Order.STATUS_OUT_FOR_DELIVERY
        ]
    ).count()
    delivered_orders = Order.objects.filter(order_status=Order.STATUS_DELIVERED).count()
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock__lte=5)
    total_customers = CustomUser.objects.filter(role=CustomUser.ROLE_CUSTOMER).count()

    recent_orders = Order.objects.select_related('user').all().order_by('-created_at')[:25]
    recent_customers = CustomUser.objects.filter(role=CustomUser.ROLE_CUSTOMER).order_by('-date_joined')[:5]

    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'active_deliveries': active_deliveries,
        'delivered_orders': delivered_orders,
        'total_products': total_products,
        'low_stock_count': low_stock_products.count(),
        'low_stock_products': low_stock_products[:5],
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'recent_customers': recent_customers,
    }
    return render(request, 'admin/dashboard.html', context)


@admin_required
def admin_products(request):
    products = Product.objects.select_related('category').all().order_by('-created_at')
    
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(model_number__icontains=q)
        )
    
    cat = request.GET.get('category', '').strip()
    if cat:
        products = products.filter(category__id=cat)

    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'query': q,
        'selected_cat': cat,
    }
    return render(request, 'admin/products.html', context)


@admin_required
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' created successfully!")
            return redirect('admin_products')
        else:
            messages.error(request, "Please correct the form errors below.")
    else:
        form = ProductForm()

    return render(request, 'admin/product_form.html', {'form': form, 'title': 'Add New Tech Product'})


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('admin_products')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ProductForm(instance=product)

    return render(request, 'admin/product_form.html', {
        'form': form,
        'product': product,
        'title': f"Edit Product: {product.name}"
    })


@admin_required
@require_POST
def admin_product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f"Product '{name}' has been deleted from catalog.")
    return redirect('admin_products')


@admin_required
@require_POST
def admin_product_bulk_delete(request):
    """
    Bulk delete selected products from the Admin catalog.
    """
    product_ids = request.POST.getlist('selected_products') or request.POST.getlist('product_ids')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_products'

    if not product_ids:
        messages.warning(request, "No products were selected for deletion.")
        return redirect(next_url)

    prods_to_delete = Product.objects.filter(id__in=product_ids)
    count = prods_to_delete.count()
    prods_to_delete.delete()
    messages.success(request, f"Successfully deleted {count} selected product(s) from catalog.")
    return redirect(next_url)


@admin_required
def admin_categories(request):
    categories = Category.objects.annotate(product_count=Count('products')).order_by('order', 'name')
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created successfully!")
            return redirect('admin_categories')
        else:
            messages.error(request, "Please check the category details and correct any errors.")
    else:
        form = CategoryForm()

    return render(request, 'admin/categories.html', {
        'categories': categories,
        'form': form
    })


@admin_required
def admin_category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect('admin_categories')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin/category_form.html', {'form': form, 'category': category})


@admin_required
@require_POST
def admin_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if category.products.exists():
        messages.warning(request, f"Cannot delete category '{category.name}' because it contains {category.products.count()} active product(s). Please reassign or delete the products first.")
        return redirect('admin_categories')
    name = category.name
    category.delete()
    messages.success(request, f"Category '{name}' deleted successfully.")
    return redirect('admin_categories')


@admin_required
def admin_orders(request):
    orders = Order.objects.select_related('user').all().order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(order_status=status_filter)

    payment_method_filter = request.GET.get('payment_method', '').strip()
    if payment_method_filter:
        if payment_method_filter == 'CARD_BANKING':
            orders = orders.filter(payment_method__in=['CARD', 'NETBANKING', 'WALLET', 'EMI'])
        else:
            orders = orders.filter(payment_method=payment_method_filter)

    payment_status_filter = request.GET.get('payment_status', '').strip()
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders = orders.filter(
            Q(order_number__icontains=search_q) |
            Q(user__username__icontains=search_q) |
            Q(shipping_name__icontains=search_q) |
            Q(shipping_city__icontains=search_q)
        )

    context = {
        'orders': orders,
        'status_filter': status_filter,
        'payment_method_filter': payment_method_filter,
        'payment_status_filter': payment_status_filter,
        'search_q': search_q,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
    }
    return render(request, 'admin/orders.html', context)


@admin_required
def admin_order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if request.method == 'POST':
        prev_status = order.order_status
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            order = form.save()
            instruction_note = request.POST.get('admin_instruction', '').strip()

            # 1. Customer Notification for Order Status Milestone Change
            send_system_notification(
                recipient=order.user,
                title=f"Order #{order.order_number} Update: {order.get_order_status_display()}",
                message=f"Logistics update: Your shipment is '{order.get_order_status_display()}'. Courier: {order.courier_name} (AWB: {order.tracking_number}). Current milestone: {order.current_location}. Estimated delivery: {order.estimated_delivery_text}.",
                notification_type=Notification.TYPE_STATUS_UPDATE,
                icon='local_shipping',
                link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
                order=order
            )

            # 2. Customer Notification for Admin Special Instruction
            if instruction_note:
                send_system_notification(
                    recipient=order.user,
                    title=f"Store Manager Instruction for Order #{order.order_number}",
                    message=instruction_note,
                    notification_type=Notification.TYPE_INSTRUCTION,
                    icon='support_agent',
                    link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
                    order=order
                )

            messages.success(request, f"Order #{order.order_number} updated to '{order.get_order_status_display()}'. Notification sent to customer!")
            return redirect('admin_order_detail', order_number=order.order_number)
        else:
            messages.error(request, "Failed to update order status.")
    else:
        form = OrderStatusForm(instance=order)

    # Order notifications timeline
    order_notifications = Notification.objects.filter(order=order).order_by('-created_at')
    assign_partner_form = AdminAssignPartnerForm(initial={'delivery_notes': order.delivery_notes})
    available_partners = CustomUser.objects.filter(role=CustomUser.ROLE_DELIVERY)

    context = {
        'order': order,
        'form': form,
        'items': order.items.all(),
        'order_notifications': order_notifications,
        'assign_partner_form': assign_partner_form,
        'available_partners': available_partners,
    }
    return render(request, 'admin/order_detail.html', context)


@admin_required
@require_POST
def admin_order_assign_delivery(request, order_number):
    """
    Admin workflow action: assign an active Delivery Partner to an order.
    Sends notifications to both the delivery partner and the customer.
    """
    order = get_object_or_404(Order, order_number=order_number)
    partner_id = request.POST.get('delivery_partner')
    notes = request.POST.get('delivery_notes', '').strip()

    if not partner_id:
        messages.error(request, "Please select an active delivery partner to assign.")
        return redirect('admin_order_detail', order_number=order.order_number)

    partner = get_object_or_404(CustomUser, pk=partner_id, role=CustomUser.ROLE_DELIVERY)
    order.delivery_partner = partner
    order.delivery_assigned_at = timezone.now()
    if notes:
        order.delivery_notes = notes

    if order.order_status == Order.STATUS_CONFIRMED:
        order.order_status = Order.STATUS_PACKED
        order.current_location = f"Assigned to Delivery Partner {partner.get_full_name() or partner.username}"
    order.save()

    # 1. Alert Delivery Partner
    send_system_notification(
        recipient=partner,
        title=f"New Delivery Assigned: Order #{order.order_number}",
        message=f"You have been assigned Order #{order.order_number}. Destination: {order.shipping_name}, {order.shipping_city} ({order.shipping_pincode}).",
        notification_type=Notification.TYPE_ORDER,
        icon='two_wheeler',
        link_url=reverse('delivery_order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )

    # 2. Alert Customer
    send_system_notification(
        recipient=order.user,
        title=f"Delivery Partner Assigned for Order #{order.order_number}",
        message=f"Delivery Partner {partner.get_full_name() or partner.username} ({partner.phone or 'Agent'}) has been assigned to deliver your package.",
        notification_type=Notification.TYPE_STATUS_UPDATE,
        icon='local_shipping',
        link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
        order=order
    )

    messages.success(request, f"Order #{order.order_number} successfully assigned to delivery partner {partner.get_full_name() or partner.username}!")
    return redirect('admin_order_detail', order_number=order.order_number)


@admin_required
@require_POST
def admin_order_delete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    num = order.order_number
    order.delete()
    messages.success(request, f"Order #{num} has been deleted successfully.")
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_orders'
    return redirect(next_url)


@admin_required
@require_POST
def admin_order_bulk_delete(request):
    order_numbers = request.POST.getlist('order_numbers')
    if not order_numbers:
        order_numbers = request.POST.getlist('order_ids')

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'admin_orders'

    if not order_numbers:
        messages.warning(request, "No orders were selected for deletion.")
        return redirect(next_url)

    orders_to_delete = Order.objects.filter(order_number__in=order_numbers)
    count = orders_to_delete.count()
    orders_to_delete.delete()
    messages.success(request, f"Successfully deleted {count} selected order(s).")
    return redirect(next_url)


@admin_required
def admin_customers(request):
    role_filter = request.GET.get('role', 'ALL').upper()
    customers = CustomUser.objects.exclude(id=request.user.id).annotate(
        order_count=Count('orders', distinct=True),
        product_count=Count('products', distinct=True)
    ).order_by('-date_joined')

    if role_filter == 'SELLER':
        customers = customers.filter(role=CustomUser.ROLE_SELLER)
    elif role_filter == 'CUSTOMER':
        customers = customers.filter(role=CustomUser.ROLE_CUSTOMER)
    elif role_filter == 'DELIVERY':
        customers = customers.filter(role=CustomUser.ROLE_DELIVERY)
    else:
        customers = customers.filter(role__in=[CustomUser.ROLE_CUSTOMER, CustomUser.ROLE_SELLER, CustomUser.ROLE_DELIVERY])

    search_q = request.GET.get('q', '').strip()
    if search_q:
        customers = customers.filter(
            Q(username__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone__icontains=search_q) |
            Q(store_name__icontains=search_q) |
            Q(vehicle_number__icontains=search_q)
        )

    context = {
        'customers': customers,
        'search_q': search_q,
        'role_filter': role_filter,
        'total_sellers_count': CustomUser.objects.filter(role=CustomUser.ROLE_SELLER).count(),
        'total_customers_count': CustomUser.objects.filter(role=CustomUser.ROLE_CUSTOMER).count(),
        'total_delivery_count': CustomUser.objects.filter(role=CustomUser.ROLE_DELIVERY).count(),
    }
    return render(request, 'admin/customers.html', context)


@admin_required
@require_POST
def admin_create_user(request):
    """
    Direct account creation by Admin for Customer, Seller, or Delivery Partner roles.
    """
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    password = request.POST.get('password', '').strip()
    role = request.POST.get('role', CustomUser.ROLE_CUSTOMER)
    store_name = request.POST.get('store_name', '').strip()
    vehicle_type = request.POST.get('vehicle_type', '').strip()
    vehicle_number = request.POST.get('vehicle_number', '').strip()
    current_city = request.POST.get('current_city', '').strip()

    if not username or not password:
        messages.error(request, "Username and password are required to create an account.")
        return redirect('admin_customers')

    if CustomUser.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' already exists. Please choose a different username.")
        return redirect('admin_customers')

    valid_roles = [CustomUser.ROLE_CUSTOMER, CustomUser.ROLE_SELLER, CustomUser.ROLE_DELIVERY]
    if role not in valid_roles:
        role = CustomUser.ROLE_CUSTOMER

    user = CustomUser.objects.create_user(
        username=username,
        email=email or f"{username}@techmart.in",
        password=password,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role=role,
        store_name=store_name if role == CustomUser.ROLE_SELLER else '',
        vehicle_type=vehicle_type if role == CustomUser.ROLE_DELIVERY else '',
        vehicle_number=vehicle_number if role == CustomUser.ROLE_DELIVERY else '',
        current_city=current_city if role == CustomUser.ROLE_DELIVERY else '',
        is_verified=True,
        is_available=True if role == CustomUser.ROLE_DELIVERY else False,
    )
    messages.success(request, f"Account '{user.username}' created successfully as {user.get_role_display()}!")
    return redirect('admin_customers')


@admin_required
@require_POST
def admin_user_toggle_role(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)
    if target_user.is_staff or target_user.is_superuser or target_user.id == request.user.id:
        messages.error(request, "Administrator account roles cannot be modified.")
        return redirect('admin_customers')

    new_role = request.POST.get('target_role')
    if new_role in [CustomUser.ROLE_CUSTOMER, CustomUser.ROLE_SELLER, CustomUser.ROLE_DELIVERY]:
        target_user.role = new_role
    elif target_user.role == CustomUser.ROLE_CUSTOMER:
        target_user.role = CustomUser.ROLE_SELLER
    elif target_user.role == CustomUser.ROLE_SELLER:
        target_user.role = CustomUser.ROLE_DELIVERY
    else:
        target_user.role = CustomUser.ROLE_CUSTOMER

    if target_user.role == CustomUser.ROLE_SELLER and not target_user.store_name:
        target_user.store_name = f"{target_user.first_name or target_user.username}'s Tech Store"
    elif target_user.role == CustomUser.ROLE_DELIVERY:
        if not target_user.vehicle_type:
            target_user.vehicle_type = 'Motorcycle'
        if not target_user.vehicle_number:
            target_user.vehicle_number = 'TN-38-EX-1001'
        target_user.is_available = True

    target_user.save()
    messages.success(request, f"User '{target_user.username}' role changed to {target_user.get_role_display()}!")
    return redirect('admin_customers')


@admin_required
@require_POST
def admin_customer_toggle_status(request, pk):
    customer = get_object_or_404(CustomUser, pk=pk)
    if customer.is_staff or customer.is_superuser or customer.id == request.user.id:
        messages.error(request, "Administrator status cannot be modified.")
        return redirect('admin_customers')
    customer.is_active = not customer.is_active
    customer.save()
    status_str = "activated" if customer.is_active else "deactivated"
    messages.success(request, f"Account '{customer.username}' has been {status_str}.")
    return redirect('admin_customers')


@admin_required
@require_POST
def admin_customer_delete(request, pk):
    customer = get_object_or_404(CustomUser, pk=pk)
    if customer.id == request.user.id or customer.is_staff or customer.is_superuser:
        messages.error(request, "Administrator or staff accounts cannot be deleted.")
        return redirect('admin_customers')

    username = customer.username
    full_name = customer.get_full_name() or username
    try:
        from django.db import transaction
        with transaction.atomic():
            customer.delete()
        messages.success(request, f"User account '{username}' ({full_name}) has been permanently deleted.")
    except Exception as e:
        messages.error(request, f"Could not delete user account '{username}': {e}")
    return redirect('admin_customers')


@admin_required
@require_POST
def admin_customer_bulk_delete(request):
    customer_ids = request.POST.getlist('selected_customers')
    if not customer_ids:
        messages.warning(request, "No user accounts were selected for deletion.")
        return redirect('admin_customers')

    users_to_delete = CustomUser.objects.filter(
        id__in=customer_ids
    ).exclude(id=request.user.id).exclude(is_staff=True).exclude(is_superuser=True)

    count = users_to_delete.count()
    if count == 0:
        messages.warning(request, "No eligible user accounts found to delete.")
        return redirect('admin_customers')

    try:
        from django.db import transaction
        with transaction.atomic():
            users_to_delete.delete()
        messages.success(request, f"Successfully deleted {count} user account(s).")
    except Exception as e:
        messages.error(request, f"Could not delete selected user accounts: {e}")
    return redirect('admin_customers')


@admin_required
def admin_payment_settings(request):
    """
    Admin Payment Gateways & QR Code Configuration.
    Allows changing store UPI ID, uploading a new QR Code image,
    toggling customer payment options (UPI, Card, NetBanking, COD), and monitoring ledger.
    """
    settings = PaymentSetting.get_settings()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reset_qr':
            if settings.qr_image:
                settings.qr_image.delete(save=False)
                settings.qr_image = None
                settings.save()
            messages.success(request, "UPI QR Code has been reset to default Google Pay image.")
            return redirect('admin_payment_settings')

        if action == 'update_payment_status':
            order_number = request.POST.get('order_number')
            new_payment_status = request.POST.get('new_payment_status')
            target_order = Order.objects.filter(order_number=order_number).first()
            if target_order and new_payment_status in dict(Order.PAY_STATUS_CHOICES):
                target_order.payment_status = new_payment_status
                target_order.save()
                messages.success(request, f"Order #{target_order.order_number} payment status updated to {target_order.get_payment_status_display()} successfully.")
            return redirect('admin_payment_settings')

        if action == 'delete_transaction':
            order_number = request.POST.get('order_number')
            target_order = Order.objects.filter(order_number=order_number).first()
            if target_order:
                num = target_order.order_number
                target_order.delete()
                messages.success(request, f"Payment transaction order #{num} has been deleted successfully.")
            return redirect('admin_payment_settings')

        if action == 'bulk_delete_transactions':
            order_numbers = request.POST.getlist('order_numbers')
            if not order_numbers:
                order_numbers = request.POST.getlist('order_ids')
            if order_numbers:
                deleted = Order.objects.filter(order_number__in=order_numbers)
                count = deleted.count()
                deleted.delete()
                messages.success(request, f"Successfully deleted {count} selected payment transaction order(s).")
            else:
                messages.warning(request, "No transaction orders were selected for deletion.")
            return redirect('admin_payment_settings')

        if action == 'export_csv':
            import csv
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="techmart_payment_transactions_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Order Number', 'Customer Name', 'Username', 'Email', 'Phone', 'Payment Method', 'Amount (INR)', 'Payment Status', 'Order Status', 'Date & Time'])
            for o in Order.objects.select_related('user').order_by('-created_at')[:200]:
                writer.writerow([
                    f"#{o.order_number}",
                    o.shipping_name or o.user.username,
                    o.user.username,
                    o.user.email,
                    o.shipping_phone or getattr(o.user, 'phone', ''),
                    o.get_payment_method_display(),
                    f"{o.total_amount:.2f}",
                    o.get_payment_status_display(),
                    o.get_order_status_display(),
                    o.created_at.strftime('%d-%b-%Y %I:%M %p')
                ])
            return response

        if action == 'preset_enable_all':
            settings.enable_upi = True
            settings.enable_card = True
            settings.enable_netbanking = True
            settings.enable_cod = True
            settings.save()
            messages.success(request, "All customer checkout payment methods (UPI, Cards, NetBanking, COD) are now enabled.")
            return redirect('admin_payment_settings')

        if action == 'preset_online_only':
            settings.enable_upi = True
            settings.enable_card = True
            settings.enable_netbanking = True
            settings.enable_cod = False
            settings.save()
            messages.success(request, "Switched to Online Payments Only (Cash on Delivery temporarily disabled).")
            return redirect('admin_payment_settings')

        if action == 'preset_cod_only':
            settings.enable_upi = False
            settings.enable_card = False
            settings.enable_netbanking = False
            settings.enable_cod = True
            settings.save()
            messages.success(request, "Switched to Cash on Delivery only.")
            return redirect('admin_payment_settings')

        if action == 'preset_clear_all':
            settings.enable_upi = False
            settings.enable_card = False
            settings.enable_netbanking = False
            settings.enable_cod = False
            settings.save()
            messages.success(request, "All 4 checkout payment methods have been cleared / turned off.")
            return redirect('admin_payment_settings')

        if action == 'reset_earnings_zero':
            updated_count = Order.objects.filter(payment_status=Order.PAY_STATUS_PAID).update(payment_status=Order.PAY_STATUS_PENDING)
            messages.success(request, f"Store revenue & money earnings successfully reset to ₹0.00! ({updated_count} paid orders marked as Pending).")
            return redirect('admin_payment_settings')

        if action == 'clear_section_revenue':
            section = request.POST.get('section', 'all')
            if section == 'all':
                updated_count = Order.objects.filter(payment_status=Order.PAY_STATUS_PAID).update(payment_status=Order.PAY_STATUS_PENDING)
                messages.success(request, f"Total Revenue cleared to ₹0.00 successfully! ({updated_count} orders marked as Pending).")
            elif section == 'upi':
                updated_count = Order.objects.filter(payment_method='UPI', payment_status=Order.PAY_STATUS_PAID).update(payment_status=Order.PAY_STATUS_PENDING)
                messages.success(request, f"UPI & QR Revenue cleared to ₹0.00 successfully! ({updated_count} orders marked as Pending).")
            elif section == 'cod':
                updated_count = Order.objects.filter(payment_method='COD', payment_status=Order.PAY_STATUS_PAID).update(payment_status=Order.PAY_STATUS_PENDING)
                messages.success(request, f"Cash on Delivery Revenue cleared to ₹0.00 successfully! ({updated_count} orders marked as Pending).")
            elif section == 'card':
                updated_count = Order.objects.filter(payment_method__in=['CARD', 'NETBANKING', 'WALLET', 'EMI'], payment_status=Order.PAY_STATUS_PAID).update(payment_status=Order.PAY_STATUS_PENDING)
                messages.success(request, f"Cards & Banking Revenue cleared to ₹0.00 successfully! ({updated_count} orders marked as Pending).")
            return redirect('admin_payment_settings')

        if action == 'clear_all_transactions':
            deleted_count, _ = Order.objects.all().delete()
            messages.success(request, "All store test transactions and orders have been cleared! Total revenue and ledger are now reset to ₹0.00.")
            return redirect('admin_payment_settings')

        form = PaymentSettingForm(request.POST, request.FILES, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Payment settings and UPI QR code have been updated and are live on customer checkout!")
            return redirect('admin_payment_settings')
        else:
            messages.error(request, "Please check the form inputs and try again.")
    else:
        form = PaymentSettingForm(instance=settings)

    # Payment Metrics
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(payment_status=Order.PAY_STATUS_PAID)
    total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    upi_orders = Order.objects.filter(payment_method='UPI')
    upi_paid = upi_orders.filter(payment_status=Order.PAY_STATUS_PAID)
    upi_revenue = upi_paid.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    cod_orders = Order.objects.filter(payment_method='COD')
    cod_paid = cod_orders.filter(payment_status=Order.PAY_STATUS_PAID)
    cod_revenue = cod_paid.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    cod_pending = cod_orders.filter(payment_status=Order.PAY_STATUS_PENDING)
    cod_pending_revenue = cod_pending.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    card_orders = Order.objects.filter(payment_method__in=['CARD', 'NETBANKING', 'WALLET', 'EMI'])
    card_paid = card_orders.filter(payment_status=Order.PAY_STATUS_PAID)
    card_revenue = card_paid.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    recent_payments = Order.objects.select_related('user').order_by('-created_at')[:50]

    context = {
        'settings': settings,
        'form': form,
        'total_orders': total_orders,
        'paid_orders_count': paid_orders.count(),
        'total_revenue': total_revenue,
        'upi_orders_count': upi_orders.count(),
        'upi_paid_count': upi_paid.count(),
        'upi_revenue': upi_revenue,
        'cod_orders_count': cod_orders.count(),
        'cod_paid_count': cod_paid.count(),
        'cod_pending_count': cod_pending.count(),
        'cod_revenue': cod_revenue,
        'cod_pending_revenue': cod_pending_revenue,
        'card_orders_count': card_orders.count(),
        'card_paid_count': card_paid.count(),
        'card_revenue': card_revenue,
        'recent_payments': recent_payments,
    }
    return render(request, 'admin/payment_settings.html', context)


# ==============================================================================
# Notifications System Views (Customer & Admin)
# ==============================================================================
@login_required
def notifications_list(request):
    """
    Displays notification history for logged in user (customer, seller, or admin).
    Supports filtering by all, unread, orders, instructions, and account.
    Filters out irrelevant admin logs and login events when viewing as a seller.
    """
    filter_type = request.GET.get('filter', 'all')
    role_view = request.GET.get('role', '')
    is_seller = (request.user.role == CustomUser.ROLE_SELLER) or (role_view == 'seller')

    user_notifs = Notification.objects.filter(recipient=request.user)

    if is_seller:
        # Sellers only see seller-relevant notifications (Orders to pack, delivered, stock, payouts, instructions)
        # Exclude customer logins, admin-only routes, delivery partner inner logs
        user_notifs = user_notifs.exclude(
            notification_type=Notification.TYPE_LOGIN
        ).exclude(
            link_url__startswith='/admin-dashboard/'
        )
    elif not request.user.is_admin_user():
        # Regular customers/delivery partners should also never see login spam
        user_notifs = user_notifs.exclude(notification_type=Notification.TYPE_LOGIN)

    total_base_count = user_notifs.count()
    unread_base_count = user_notifs.filter(is_read=False).count()

    if filter_type == 'unread':
        user_notifs = user_notifs.filter(is_read=False)
    elif filter_type == 'orders':
        user_notifs = user_notifs.filter(notification_type__in=[Notification.TYPE_ORDER, Notification.TYPE_STATUS_UPDATE])
    elif filter_type == 'instructions':
        user_notifs = user_notifs.filter(notification_type=Notification.TYPE_INSTRUCTION)
    elif filter_type == 'account':
        user_notifs = user_notifs.filter(notification_type__in=[Notification.TYPE_REGISTRATION, Notification.TYPE_LOGIN])

    context = {
        'notifications': user_notifs,
        'filter_type': filter_type,
        'role_view': role_view,
        'is_seller_view': is_seller,
        'total_count': total_base_count,
        'unread_count': unread_base_count,
    }
    return render(request, 'notifications/list.html', context)


@login_required
def notification_mark_read(request, pk):
    """
    Marks a single notification as read and redirects user to its destination link.
    """
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.link_url:
        return redirect(notif.link_url)
    return redirect('notifications_list')


@login_required
@require_POST
def notifications_mark_all_read(request):
    """
    Marks all notifications for the current user as read.
    """
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('notifications_list')


@login_required
@require_POST
def notification_delete(request, pk):
    """
    Deletes a single notification owned by current user.
    """
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.delete()
    messages.success(request, "Notification deleted.")
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('notifications_list')


@login_required
@require_POST
def notifications_bulk_delete(request):
    """
    Bulk action to delete selected notifications or clear all / all read.
    Allows user to select multiple notifications and delete them at once.
    """
    action = request.POST.get('action')
    notif_ids = request.POST.getlist('notification_ids')
    user_notifs = Notification.objects.filter(recipient=request.user)

    if action == 'clear_all':
        count = user_notifs.count()
        user_notifs.delete()
        messages.success(request, f"Successfully cleared all {count} notification(s).")
    elif action == 'clear_read':
        read_notifs = user_notifs.filter(is_read=True)
        count = read_notifs.count()
        read_notifs.delete()
        messages.success(request, f"Successfully deleted {count} read notification(s).")
    elif action == 'delete_selected' or notif_ids:
        if not notif_ids:
            messages.warning(request, "Please select at least one notification to delete.")
        else:
            to_del = user_notifs.filter(pk__in=notif_ids)
            count = to_del.count()
            to_del.delete()
            messages.success(request, f"Successfully deleted {count} selected notification(s).")
    else:
        messages.info(request, "No notifications selected.")

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('notifications_list')


@admin_required
def admin_broadcast_notification(request):
    """
    Allows Admin to broadcast instructions, announcements, or custom updates
    to ALL roles (Customers, Sellers, Delivery Partners, Admins) or a specific account.
    """
    customers = CustomUser.objects.filter(role=CustomUser.ROLE_CUSTOMER).order_by('username')
    sellers = CustomUser.objects.filter(role=CustomUser.ROLE_SELLER).order_by('username')
    delivery_partners = CustomUser.objects.filter(role=CustomUser.ROLE_DELIVERY).order_by('username')
    admins = CustomUser.objects.filter(
        Q(role=CustomUser.ROLE_ADMIN) | Q(is_staff=True) | Q(is_superuser=True)
    ).distinct().order_by('username')

    if request.method == 'POST':
        target = request.POST.get('target', 'all_roles')
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        icon = request.POST.get('icon', 'campaign')
        link_url = request.POST.get('link_url', '').strip()

        if not title or not message:
            messages.error(request, "Please enter both a title and message for the announcement.")
        else:
            recipients = []
            target_label = ""

            if target in ['all_roles', 'all']:
                recipients = list(CustomUser.objects.filter(is_active=True))
                target_label = f"all users across all roles ({len(recipients)} accounts)"
            elif target == 'customers_all':
                recipients = list(customers)
                target_label = f"all customer accounts ({len(recipients)} customers)"
            elif target == 'sellers_all':
                recipients = list(sellers)
                target_label = f"all registered sellers ({len(recipients)} stores)"
            elif target == 'delivery_all':
                recipients = list(delivery_partners)
                target_label = f"all delivery partners ({len(recipients)} partners)"
            elif target == 'admins_all':
                recipients = list(admins)
                target_label = f"all store administrators ({len(recipients)} admins)"
            else:
                user_pk = target.replace('user_', '')
                user_obj = get_object_or_404(CustomUser, pk=user_pk)
                recipients = [user_obj]
                target_label = f"user '{user_obj.username}' ({user_obj.get_role_display()})"

            for u in recipients:
                dest_url = link_url
                if not dest_url:
                    if u.is_delivery_partner():
                        dest_url = reverse('delivery_dashboard')
                    elif u.is_seller_user():
                        dest_url = reverse('seller_dashboard')
                    elif u.is_admin_user():
                        dest_url = reverse('admin_dashboard')
                    else:
                        dest_url = reverse('notifications_list')

                send_system_notification(
                    recipient=u,
                    title=title,
                    message=message,
                    notification_type=Notification.TYPE_INSTRUCTION,
                    icon=icon,
                    link_url=dest_url
                )

            messages.success(request, f"📢 Broadcast instruction successfully delivered to {target_label}!")
            return redirect('admin_broadcast_notification')

    recent_broadcasts = Notification.objects.filter(
        notification_type=Notification.TYPE_INSTRUCTION
    ).order_by('-created_at')[:20]

    context = {
        'customers': customers,
        'sellers': sellers,
        'delivery_partners': delivery_partners,
        'admins': admins,
        'total_users_count': CustomUser.objects.filter(is_active=True).count(),
        'recent_broadcasts': recent_broadcasts,
    }
    return render(request, 'admin/broadcast.html', context)


@admin_required
def admin_seller_detail(request, pk):
    """
    Admin view to see full details of a Seller account:
    store info, GST, products, orders, revenue, and profile.
    """
    seller = get_object_or_404(CustomUser, pk=pk, role=CustomUser.ROLE_SELLER)

    seller_products = Product.objects.filter(seller=seller).select_related('category').order_by('-created_at')
    seller_orders = Order.objects.filter(items__seller=seller).distinct().order_by('-created_at')
    seller_items = OrderItem.objects.filter(seller=seller)

    paid_revenue = seller_items.filter(
        order__payment_status=Order.PAY_STATUS_PAID
    ).aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')

    pending_revenue = seller_items.filter(
        order__payment_status=Order.PAY_STATUS_PENDING
    ).aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')

    total_products = seller_products.count()
    in_stock = seller_products.filter(stock__gt=0).count()
    low_stock = seller_products.filter(stock__lte=5, stock__gt=0).count()
    out_of_stock = seller_products.filter(stock=0).count()
    total_orders = seller_orders.count()

    context = {
        'seller': seller,
        'seller_products': seller_products[:20],
        'seller_orders': seller_orders[:20],
        'paid_revenue': paid_revenue,
        'pending_revenue': pending_revenue,
        'total_products': total_products,
        'in_stock': in_stock,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_orders': total_orders,
    }
    return render(request, 'admin/seller_detail.html', context)


def admin_login_as_seller(request, pk):
    """
    Allows Admin to seamlessly access and manage a Seller's portal context.
    Provides direct access to Dashboard, My Products, Add Product, Store Categories, and My Orders.
    Stores admin return information in session so admin can return to Admin Portal at any time.
    """
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in with an Administrator account.")
        return redirect('login')

    # Determine original admin ID (either current user if admin, or active switch session)
    admin_id = request.user.id if request.user.is_admin_user() else request.session.get('admin_switch_back')
    if not admin_id:
        messages.error(request, "Access Denied: Administrator permission required.")
        return redirect('home')

    admin_user = CustomUser.objects.filter(pk=admin_id).first()
    if not (admin_user and admin_user.is_admin_user()):
        messages.error(request, "Access Denied: Administrator permission required.")
        return redirect('home')

    admin_name = admin_user.get_full_name() or admin_user.username

    seller = get_object_or_404(CustomUser, pk=pk)
    if not (seller.role == CustomUser.ROLE_SELLER or seller.is_seller_user()):
        messages.error(request, f"User '{seller.username}' does not have a Seller account.")
        return redirect('admin_customers')

    # Perform login switch to seller
    login(request, seller, backend='store.backends.EmailOrUsernameBackend')
    request.session['admin_switch_back'] = admin_id
    request.session['admin_switch_back_name'] = admin_name
    request.session['admin_switched_seller_id'] = seller.id

    action = request.GET.get('action') or request.GET.get('next') or 'dashboard'
    messages.info(
        request,
        f"Accessing portal as {seller.display_store_name} (@{seller.username}). "
        f"You have direct access to manage Dashboard, Products, Categories, and Orders."
    )

    if action == 'products':
        return redirect('seller_products')
    elif action == 'add_product':
        return redirect('seller_product_create')
    elif action == 'categories':
        return redirect('seller_categories')
    elif action == 'orders':
        return redirect('seller_orders')
    else:
        return redirect('seller_dashboard')


@login_required
def admin_switch_back(request):
    """
    Returns an active impersonated seller or delivery partner session back to the original Admin account.
    """
    admin_id = request.session.get('admin_switch_back')
    if not admin_id:
        messages.warning(request, "No active administrator switch session was found.")
        return redirect('home')

    admin_user = get_object_or_404(CustomUser, pk=admin_id)
    if not admin_user.is_admin_user():
        messages.error(request, "Invalid administrator session credentials.")
        return redirect('home')

    was_delivery = 'admin_switched_delivery_id' in request.session

    # Switch session back to admin
    login(request, admin_user, backend='store.backends.EmailOrUsernameBackend')
    request.session.pop('admin_switch_back', None)
    request.session.pop('admin_switch_back_name', None)
    request.session.pop('admin_switched_seller_id', None)
    request.session.pop('admin_switched_delivery_id', None)

    messages.success(request, f"Returned to Admin account ({admin_user.get_full_name() or admin_user.username}).")
    if was_delivery:
        return redirect(reverse('admin_customers') + '?role=DELIVERY')
    return redirect(reverse('admin_customers') + '?role=SELLER')


def admin_login_as_delivery(request, pk):
    """
    Allows Admin to seamlessly access and manage a Delivery Partner's portal context.
    Provides direct access to Dashboard, Active Deliveries, and Delivery History.
    Stores admin return information in session so admin can return to Admin Portal at any time.
    """
    if not request.user.is_authenticated:
        messages.warning(request, "Please log in with an Administrator account.")
        return redirect('login')

    # Determine original admin ID (either current user if admin, or active switch session)
    admin_id = request.user.id if request.user.is_admin_user() else request.session.get('admin_switch_back')
    if not admin_id:
        messages.error(request, "Access Denied: Administrator permission required.")
        return redirect('home')

    admin_user = CustomUser.objects.filter(pk=admin_id).first()
    if not (admin_user and admin_user.is_admin_user()):
        messages.error(request, "Access Denied: Administrator permission required.")
        return redirect('home')

    admin_name = admin_user.get_full_name() or admin_user.username

    partner = get_object_or_404(CustomUser, pk=pk)
    if not (partner.role == CustomUser.ROLE_DELIVERY or partner.is_delivery_partner()):
        messages.error(request, f"User '{partner.username}' is not a registered Delivery Partner.")
        return redirect(reverse('admin_customers') + '?role=DELIVERY')

    # Perform login switch to delivery partner
    login(request, partner, backend='store.backends.EmailOrUsernameBackend')
    request.session['admin_switch_back'] = admin_id
    request.session['admin_switch_back_name'] = admin_name
    request.session['admin_switched_delivery_id'] = partner.id

    action = request.GET.get('action') or request.GET.get('next') or 'dashboard'
    messages.info(
        request,
        f"Accessing Delivery Portal as {partner.get_full_name() or partner.username} (@{partner.username} • {partner.vehicle_number or 'Delivery Partner'}). "
        f"You have direct access to Dashboard, Active Deliveries, and Delivery History."
    )

    if action == 'history':
        return redirect('delivery_history')
    elif action == 'active_deliveries':
        return redirect('delivery_dashboard')
    else:
        return redirect('delivery_dashboard')


# ==============================================================================
# Seller Portal & Management Views (Protected with @seller_required)
# ==============================================================================

@seller_required
def seller_dashboard(request):
    """
    Seller Dashboard Overview.
    Displays metrics, products summary, recent orders, and quick actions strictly
    for the logged-in seller (or all for admin viewing seller portal).
    """
    seller = request.user
    is_admin = seller.is_admin_user()
    seller_id_param = request.GET.get('seller_id') or request.session.get('admin_switched_seller_id')
    if is_admin and seller_id_param:
        target_seller = CustomUser.objects.filter(pk=seller_id_param, role=CustomUser.ROLE_SELLER).first()
        if target_seller:
            seller = target_seller
            is_admin = False

    my_products = Product.objects.all() if is_admin else Product.objects.filter(seller=seller)
    total_products = my_products.count()
    in_stock_count = my_products.filter(stock__gt=0).count()
    low_stock_count = my_products.filter(stock__lte=5, stock__gt=0).count()
    out_of_stock_count = my_products.filter(stock=0).count()

    # Seller Orders: only orders containing items belonging to this seller
    if is_admin:
        seller_orders = Order.objects.all()
        seller_items = OrderItem.objects.all()
    else:
        seller_orders = Order.objects.filter(items__seller=seller).distinct()
        seller_items = OrderItem.objects.filter(seller=seller)

    total_orders_count = seller_orders.count()

    # Revenue earned from seller's items in paid orders
    paid_items = seller_items.filter(order__payment_status=Order.PAY_STATUS_PAID)
    total_seller_revenue = paid_items.aggregate(Sum('line_total'))['line_total__sum'] or Decimal('0.00')

    # Pending items revenue
    pending_items = seller_items.filter(order__payment_status=Order.PAY_STATUS_PENDING)
    pending_seller_revenue = pending_items.aggregate(Sum('line_total'))['line_total__sum'] or Decimal('0.00')

    # Recent orders containing seller items
    recent_orders = seller_orders.order_by('-created_at')[:8]

    # Low stock alerts for seller
    low_stock_products = my_products.filter(stock__lte=5).order_by('stock')[:6]

    context = {
        'total_products': total_products,
        'in_stock_count': in_stock_count,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_orders_count': total_orders_count,
        'total_seller_revenue': total_seller_revenue,
        'pending_seller_revenue': pending_seller_revenue,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'seller': seller,
    }
    return render(request, 'seller/dashboard.html', context)


@seller_required
def seller_products(request):
    """
    List only products owned by this seller.
    Customers are blocked. Sellers cannot view another seller's products list.
    """
    seller = request.user
    is_admin = seller.is_admin_user()
    seller_id_param = request.GET.get('seller_id') or request.session.get('admin_switched_seller_id')
    if is_admin and seller_id_param:
        target_seller = CustomUser.objects.filter(pk=seller_id_param, role=CustomUser.ROLE_SELLER).first()
        if target_seller:
            seller = target_seller
            is_admin = False

    products = Product.objects.all() if is_admin else Product.objects.filter(seller=seller)

    # Search filter
    search_q = request.GET.get('q', '').strip()
    if search_q:
        products = products.filter(
            Q(name__icontains=search_q) |
            Q(brand__icontains=search_q) |
            Q(model_number__icontains=search_q)
        )

    # Category filter
    cat_filter = request.GET.get('category', '').strip()
    if cat_filter:
        products = products.filter(category__slug=cat_filter)

    # Stock filter
    stock_filter = request.GET.get('stock', 'all').strip()
    if stock_filter == 'in_stock':
        products = products.filter(stock__gt=5)
    elif stock_filter == 'low_stock':
        products = products.filter(stock__lte=5, stock__gt=0)
    elif stock_filter == 'out_of_stock':
        products = products.filter(stock=0)

    categories = Category.objects.all().order_by('name')

    context = {
        'products': products.order_by('-created_at'),
        'categories': categories,
        'search_q': search_q,
        'cat_filter': cat_filter,
        'stock_filter': stock_filter,
        'total_count': products.count(),
    }
    return render(request, 'seller/products.html', context)


@seller_required
def seller_product_create(request):
    """
    Allows a seller to create a new product.
    Backend connects the product to the owning seller automatically.
    """
    target_seller = request.user
    if request.user.is_admin_user():
        seller_id_param = request.GET.get('seller_id') or request.POST.get('seller_id') or request.session.get('admin_switched_seller_id')
        if seller_id_param:
            found = CustomUser.objects.filter(pk=seller_id_param, role=CustomUser.ROLE_SELLER).first()
            if found:
                target_seller = found

    if request.method == 'POST':
        form = SellerProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = target_seller  # Securely enforce owning seller
            product.save()

            messages.success(request, f"Product '{product.name}' has been added to seller catalog ({target_seller.display_store_name})!")
            return redirect('seller_products')
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = SellerProductForm()

    return render(request, 'seller/product_form.html', {
        'form': form,
        'action_title': 'Add New Product',
        'is_edit': False,
    })


@seller_required
def seller_product_edit(request, pk):
    """
    Allows seller to edit only their own product.
    Strict backend authorization check prevents tampering with other sellers' products.
    """
    product = get_object_or_404(Product, pk=pk)

    # Backend object-level access control:
    if not request.user.is_admin_user() and product.seller != request.user:
        messages.error(request, "Access Denied: You cannot view or modify another seller's product.")
        return redirect('seller_products')

    if request.method == 'POST':
        form = SellerProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            saved_prod = form.save(commit=False)
            if not request.user.is_admin_user():
                saved_prod.seller = request.user  # Ensure seller cannot be hijacked
            saved_prod.save()
            messages.success(request, f"Product '{product.name}' has been updated successfully!")
            return redirect('seller_products')
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = SellerProductForm(instance=product)

    return render(request, 'seller/product_form.html', {
        'form': form,
        'product': product,
        'action_title': f"Edit Product: {product.name}",
        'is_edit': True,
    })


@seller_required
@require_POST
def seller_product_delete(request, pk):
    """
    Allows seller to delete only their own product.
    Strict backend authorization check.
    """
    product = get_object_or_404(Product, pk=pk)

    # Backend object-level access control:
    if not request.user.is_admin_user() and product.seller != request.user:
        messages.error(request, "Access Denied: You cannot delete another seller's product.")
        return redirect('seller_products')

    prod_name = product.name
    product.delete()
    messages.success(request, f"Product '{prod_name}' has been deleted from your catalog.")
    return redirect('seller_products')


@seller_required
@require_POST
def seller_bulk_delete_products(request):
    """
    Bulk delete selected products for seller / admin.
    """
    product_ids = request.POST.getlist('product_ids')
    if not product_ids:
        messages.warning(request, "No products were selected for deletion.")
        return redirect('seller_products')

    if request.user.is_admin_user():
        prods = Product.objects.filter(id__in=product_ids)
    else:
        prods = Product.objects.filter(id__in=product_ids, seller=request.user)

    count = prods.count()
    prods.delete()
    messages.success(request, f"Successfully deleted {count} selected product(s).")
    return redirect('seller_products')


@seller_required
@require_POST
def seller_update_stock(request, pk):
    """
    Quick stock & availability update endpoint for sellers.
    Strict backend authorization check.
    """
    product = get_object_or_404(Product, pk=pk)

    # Backend object-level access control:
    if not request.user.is_admin_user() and product.seller != request.user:
        return JsonResponse({'success': False, 'message': 'Access Denied: Not your product.'}, status=403)

    try:
        new_stock = int(request.POST.get('stock', product.stock))
        if new_stock < 0:
            return JsonResponse({'success': False, 'message': 'Stock units cannot be negative.'}, status=400)
        product.stock = new_stock
        product.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return JsonResponse({
                'success': True,
                'stock': product.stock,
                'is_in_stock': product.is_in_stock,
                'message': f"Stock for '{product.name}' updated to {product.stock} units."
            })
        messages.success(request, f"Stock for '{product.name}' updated to {product.stock} units.")
    except (ValueError, TypeError):
        messages.error(request, "Invalid stock quantity specified.")

    return redirect(request.META.get('HTTP_REFERER') or 'seller_products')


@seller_required
def seller_orders(request):
    """
    List only orders containing products owned by this seller.
    Customers cannot access. Sellers cannot see orders that don't belong to them.
    """
    seller = request.user
    is_admin = seller.is_admin_user()
    seller_id_param = request.GET.get('seller_id') or request.session.get('admin_switched_seller_id')
    if is_admin and seller_id_param:
        target_seller = CustomUser.objects.filter(pk=seller_id_param, role=CustomUser.ROLE_SELLER).first()
        if target_seller:
            seller = target_seller
            is_admin = False

    # Backend object-level isolation:
    if is_admin:
        orders_qs = Order.objects.all()
    else:
        orders_qs = Order.objects.filter(Q(items__seller=seller) | Q(items__seller__isnull=True)).distinct()

    orders_qs = orders_qs.select_related('user').prefetch_related('items__product').order_by('-created_at')

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders_qs = orders_qs.filter(order_status=status_filter)

    # Payment filter
    pay_filter = request.GET.get('payment', '').strip()
    if pay_filter:
        orders_qs = orders_qs.filter(payment_status=pay_filter)

    # Search filter
    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_q) |
            Q(shipping_name__icontains=search_q) |
            Q(shipping_phone__icontains=search_q)
        )

    # Decorate orders with seller-specific items count and line subtotal
    orders_data = []
    for ord_obj in orders_qs:
        seller_items = ord_obj.items.all() if is_admin else ord_obj.items.filter(seller=seller)
        subtotal_for_seller = seller_items.aggregate(Sum('line_total'))['line_total__sum'] or Decimal('0.00')
        orders_data.append({
            'order': ord_obj,
            'seller_items': seller_items,
            'seller_items_count': seller_items.count(),
            'seller_subtotal': subtotal_for_seller,
        })

    context = {
        'orders_data': orders_data,
        'search_q': search_q,
        'status_filter': status_filter,
        'pay_filter': pay_filter,
        'total_orders': len(orders_data),
    }
    return render(request, 'seller/orders.html', context)


@seller_required
def seller_order_detail(request, order_number):
    """
    View an order detail.
    Strict backend authorization: Order MUST contain at least one item owned by this seller.
    Sellers cannot access another seller's order.
    """
    order = get_object_or_404(Order, order_number=order_number)
    seller = request.user
    is_admin = seller.is_admin_user()

    # Backend access rule:
    if not is_admin:
        has_item = order.items.filter(seller=seller).exists()
        if not has_item:
            messages.error(request, "Access Denied: This order does not contain any of your products.")
            return redirect('seller_orders')

    seller_items = order.items.all() if is_admin else order.items.filter(seller=seller)
    seller_subtotal = seller_items.aggregate(Sum('line_total'))['line_total__sum'] or Decimal('0.00')

    context = {
        'order': order,
        'seller_items': seller_items,
        'seller_subtotal': seller_subtotal,
        'is_admin': is_admin,
    }
    return render(request, 'seller/order_detail.html', context)


@seller_required
@require_POST
def seller_order_delete(request, order_number):
    """
    Allows seller/admin to delete an order from seller views.
    """
    order = get_object_or_404(Order, order_number=order_number)
    if not request.user.is_admin_user():
        if not order.items.filter(Q(seller=request.user) | Q(seller__isnull=True)).exists():
            messages.error(request, "Access Denied: You cannot delete this order.")
            return redirect(request.POST.get('next') or 'seller_orders')

    num = order.order_number
    order.delete()
    messages.success(request, f"Order #{num} deleted successfully.")
    return redirect(request.POST.get('next') or 'seller_orders')


@seller_required
@require_POST
def seller_bulk_delete_orders(request):
    """
    Bulk delete selected orders from seller orders list or seller dashboard.
    """
    order_numbers = request.POST.getlist('order_numbers')
    if not order_numbers:
        order_numbers = request.POST.getlist('order_ids')

    next_url = request.POST.get('next') or 'seller_orders'

    if not order_numbers:
        messages.warning(request, "No orders were selected for deletion.")
        return redirect(next_url)

    if request.user.is_admin_user():
        orders_to_delete = Order.objects.filter(order_number__in=order_numbers)
    else:
        orders_to_delete = Order.objects.filter(
            Q(items__seller=request.user) | Q(items__seller__isnull=True),
            order_number__in=order_numbers
        ).distinct()

    count = orders_to_delete.count()
    orders_to_delete.delete()
    messages.success(request, f"Successfully deleted {count} selected order(s).")
    return redirect(next_url)


@seller_required
def seller_profile(request):
    """
    Allows a seller to view and update their own business profile.
    Strictly restricted to request.user (cannot edit another seller's profile).
    """
    seller = request.user
    pwd_form = ProfilePasswordChangeForm(user=seller)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        if action == 'change_password':
            pwd_form = ProfilePasswordChangeForm(user=seller, data=request.POST)
            if pwd_form.is_valid():
                new_pwd = pwd_form.cleaned_data['new_password']
                seller.set_password(new_pwd)
                seller.save()
                update_session_auth_hash(request, seller)
                messages.success(request, "Your account password was updated successfully!")
                return redirect('seller_profile')
            else:
                form = SellerProfileForm(instance=seller)
                messages.error(request, "Please check the password errors below.")
        else:
            form = SellerProfileForm(request.POST, request.FILES, instance=seller)
            if form.is_valid():
                form.save()
                messages.success(request, "Your seller profile and store details were updated successfully!")
                return redirect('seller_profile')
            else:
                messages.error(request, "Please check the highlighted errors in your profile form.")
    else:
        form = SellerProfileForm(instance=seller)

    # Seller metrics
    total_products = Product.objects.filter(seller=seller).count()
    total_sales = OrderItem.objects.filter(
        seller=seller, order__payment_status=Order.PAY_STATUS_PAID
    ).aggregate(Sum('line_total'))['line_total__sum'] or Decimal('0.00')

    context = {
        'form': form,
        'pwd_form': pwd_form,
        'seller': seller,
        'total_products': total_products,
        'total_sales': total_sales,
    }
    return render(request, 'seller/profile.html', context)


@seller_required
@require_POST
def seller_product_toggle_status(request, pk):
    """
    Toggle product active status (Active vs Inactive).
    Sellers can deactivate products when temporarily unavailable.
    """
    seller = request.user
    if seller.is_admin_user():
        product = get_object_or_404(Product, pk=pk)
    else:
        product = get_object_or_404(Product, pk=pk, seller=seller)

    product.is_active = not product.is_active
    product.save()
    status_str = "Activated (Visible in Store)" if product.is_active else "Deactivated (Hidden from Store)"
    messages.success(request, f"Product '{product.name}' has been {status_str}.")
    return redirect('seller_products')


@seller_required
@require_POST
def seller_update_item_status(request, item_id):
    """
    Seller order fulfillment action:
    Updates status of an item owned by this seller (CONFIRMED -> PACKED -> READY_FOR_PICKUP or REJECTED).
    Advances order status when appropriate and sends milestone notification.
    """
    seller = request.user
    if seller.is_admin_user():
        item = get_object_or_404(OrderItem, id=item_id)
    else:
        item = get_object_or_404(OrderItem, id=item_id, seller=seller)

    new_status = request.POST.get('status')
    valid_statuses = [
        OrderItem.ITEM_STATUS_CONFIRMED,
        OrderItem.ITEM_STATUS_PACKED,
        OrderItem.ITEM_STATUS_READY,
        OrderItem.ITEM_STATUS_REJECTED
    ]
    if new_status in valid_statuses:
        item.status = new_status
        item.save()

        order = item.order
        all_items = order.items.all()
        ready_or_packed = all_items.filter(
            status__in=[OrderItem.ITEM_STATUS_PACKED, OrderItem.ITEM_STATUS_READY]
        ).count()

        if ready_or_packed == all_items.count() and order.order_status == Order.STATUS_CONFIRMED:
            order.order_status = Order.STATUS_PACKED
            order.current_location = "Seller Fulfillment Center - Packed & Ready for Pickup"
            order.save()
            send_system_notification(
                recipient=order.user,
                title=f"Order #{order.order_number} Packed & Sealed",
                message="All items in your order have been inspected, packed, and sealed by our verified sellers.",
                notification_type=Notification.TYPE_STATUS_UPDATE,
                icon='inventory_2',
                link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
                order=order
            )

        messages.success(request, f"Item '{item.product_name}' status updated to '{item.get_status_display()}'.")
    else:
        messages.error(request, "Invalid item status selected.")

    return redirect('seller_order_detail', order_number=item.order.order_number)


@seller_required
def seller_categories(request):
    """
    Seller Portal Category Management:
    Allows sellers to organize store categories, view product counts, and create new categories.
    """
    categories = Category.objects.annotate(product_count=Count('products')).order_by('order', 'name')
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created successfully!")
            return redirect('seller_categories')
        else:
            messages.error(request, "Please check the category details and correct any errors.")
    else:
        form = CategoryForm()

    context = {
        'categories': categories,
        'form': form,
    }
    return render(request, 'seller/categories.html', context)


@seller_required
def seller_category_edit(request, pk):
    """
    Allows sellers to edit an existing category name, icon, display order, or description.
    """
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully!")
            return redirect('seller_categories')
        else:
            messages.error(request, "Please correct the errors in the category form.")
    else:
        form = CategoryForm(instance=category)
    return render(request, 'seller/category_form.html', {'form': form, 'category': category})


@seller_required
@require_POST
def seller_category_delete(request, pk):
    """
    Allows sellers to delete a category.
    Reassigns associated products to another category to preserve products.
    """
    category = get_object_or_404(Category, pk=pk)
    fallback_cat = Category.objects.exclude(pk=pk).first()
    if fallback_cat:
        category.products.update(category=fallback_cat)
    name = category.name
    category.delete()
    messages.success(request, f"Category '{name}' deleted successfully.")
    return redirect('seller_categories')


@seller_required
@require_POST
def seller_bulk_delete_categories(request):
    """
    Bulk delete selected categories.
    Reassigns associated products to another category to preserve products.
    """
    category_ids = request.POST.getlist('category_ids')
    if not category_ids:
        messages.warning(request, "No categories were selected for deletion.")
        return redirect('seller_categories')

    cats = Category.objects.filter(id__in=category_ids)
    count = cats.count()
    fallback_cat = Category.objects.exclude(id__in=category_ids).first()
    if fallback_cat:
        Product.objects.filter(category__in=cats).update(category=fallback_cat)
    cats.delete()
    messages.success(request, f"Successfully deleted {count} selected category/categories.")
    return redirect('seller_categories')


# ==============================================================================
# Delivery Partner Dashboard & Tracking Views (@delivery_required)
# ==============================================================================
@delivery_required
def delivery_dashboard(request):
    """
    Main delivery dashboard for Delivery Partners (and Store Admin in oversight mode).
    Shows assigned active shipments, delivery checklist, availability switch, and quick stats.
    """
    partner = request.user
    is_admin_view = partner.is_admin_user() and not partner.is_delivery_partner()

    partner_id_param = request.GET.get('partner_id') or request.session.get('admin_switched_delivery_id')
    if is_admin_view and partner_id_param:
        target_partner = CustomUser.objects.filter(pk=partner_id_param, role=CustomUser.ROLE_DELIVERY).first()
        if target_partner:
            partner = target_partner
            is_admin_view = False

    if is_admin_view:
        assigned_orders = Order.objects.filter(delivery_partner__isnull=False)
    else:
        assigned_orders = Order.objects.filter(delivery_partner=partner)

    active_deliveries = assigned_orders.filter(
        order_status__in=[
            Order.STATUS_CONFIRMED,
            Order.STATUS_PACKED,
            Order.STATUS_IN_TRANSIT,
            Order.STATUS_OUT_FOR_DELIVERY
        ]
    ).order_by('-created_at')

    completed_deliveries = assigned_orders.filter(order_status=Order.STATUS_DELIVERED)
    total_completed = completed_deliveries.count()

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    delivered_today = completed_deliveries.filter(delivery_delivered_at__gte=today_start).count()
    pending_count = active_deliveries.count()

    context = {
        'partner': partner,
        'active_deliveries': active_deliveries,
        'total_completed': total_completed,
        'delivered_today': delivered_today,
        'pending_count': pending_count,
        'is_available': partner.is_available,
        'is_admin_view': is_admin_view,
    }
    return render(request, 'delivery/dashboard.html', context)


@delivery_required
@require_POST
def delivery_toggle_availability(request):
    """
    Allows delivery partner to toggle availability status (Online vs Offline).
    """
    partner = request.user
    partner.is_available = not partner.is_available
    partner.save()
    status_str = "Online (Ready for Pickups & Deliveries)" if partner.is_available else "Offline (On Break)"
    messages.success(request, f"Your status is now {status_str}.")
    return redirect('delivery_dashboard')


@delivery_required
def delivery_order_detail(request, order_number):
    """
    Secure Delivery Detail page for the assigned delivery partner.
    Shows pickup location (seller hubs), delivery address, contact info, item checklist,
    and progress milestone buttons.
    """
    partner = request.user
    is_admin = partner.is_admin_user()

    if is_admin:
        order = get_object_or_404(Order, order_number=order_number)
    else:
        order = get_object_or_404(Order, order_number=order_number, delivery_partner=partner)

    # Distinct sellers for pickup addresses
    seller_ids = order.items.filter(seller__isnull=False).values_list('seller_id', flat=True).distinct()
    sellers = CustomUser.objects.filter(id__in=seller_ids) if seller_ids else []

    context = {
        'order': order,
        'items': order.items.all(),
        'partner': partner,
        'sellers': sellers,
        'is_admin': is_admin,
    }
    return render(request, 'delivery/detail.html', context)


@delivery_required
@require_POST
def delivery_update_status(request, order_number):
    """
    Sequential milestone progression by assigned delivery partner:
    - 'pickup': Order marked 'IN_TRANSIT' (Package picked up from seller/hub).
    - 'out_for_delivery': Order marked 'OUT_FOR_DELIVERY'. Customer receives notification to ready their PIN.
    - 'deliver': Requires customer's 4-digit doorstep delivery PIN. Verifies PIN and marks 'DELIVERED'.
    """
    partner = request.user
    is_admin = partner.is_admin_user()

    if is_admin:
        order = get_object_or_404(Order, order_number=order_number)
    else:
        order = get_object_or_404(Order, order_number=order_number, delivery_partner=partner)

    action = request.POST.get('action')

    if action == 'pickup':
        order.order_status = Order.STATUS_IN_TRANSIT
        order.delivery_picked_up_at = timezone.now()
        order.current_location = f"In Transit with {partner.get_full_name() or partner.username}"
        order.save()

        send_system_notification(
            recipient=order.user,
            title=f"Order #{order.order_number} In Transit",
            message=f"Delivery Partner {partner.get_full_name() or partner.username} has picked up your package and is on the move.",
            notification_type=Notification.TYPE_STATUS_UPDATE,
            icon='local_shipping',
            link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
            order=order
        )
        messages.success(request, f"Order #{order.order_number} marked as Picked Up & In Transit!")

    elif action == 'out_for_delivery':
        order.order_status = Order.STATUS_OUT_FOR_DELIVERY
        order.current_location = f"Out for Delivery - Nearby destination ({partner.vehicle_number or 'Delivery Agent'})"
        order.save()

        send_system_notification(
            recipient=order.user,
            title=f"Order #{order.order_number} is Out for Delivery! 🛵",
            message=f"Delivery Partner {partner.get_full_name() or partner.username} is out for doorstep delivery. Please share delivery PIN {order.delivery_pin} upon arrival.",
            notification_type=Notification.TYPE_STATUS_UPDATE,
            icon='delivery_dining',
            link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
            order=order
        )
        messages.success(request, f"Order #{order.order_number} marked Out for Delivery!")

    elif action == 'deliver':
        entered_pin = request.POST.get('delivery_pin', '').strip()
        if entered_pin != order.delivery_pin:
            messages.error(request, f"❌ Verification Failed: The PIN '{entered_pin}' is invalid. Please ask customer {order.shipping_name} for their 4-digit doorstep delivery PIN.")
            return redirect('delivery_order_detail', order_number=order.order_number)

        order.order_status = Order.STATUS_DELIVERED
        order.delivery_delivered_at = timezone.now()
        order.current_location = f"Delivered to {order.shipping_name} (Doorstep PIN Verified)"
        if order.payment_method == Order.PAY_COD:
            order.payment_status = Order.PAY_STATUS_PAID
        order.save()

        send_system_notification(
            recipient=order.user,
            title=f"Order #{order.order_number} Delivered Successfully! 🎉",
            message=f"Package was verified with PIN and handed over by {partner.get_full_name() or partner.username}. Thank you for shopping with Tech Mart!",
            notification_type=Notification.TYPE_STATUS_UPDATE,
            icon='task_alt',
            link_url=reverse('order_detail', kwargs={'order_number': order.order_number}),
            order=order
        )
        send_system_notification(
            for_admin=True,
            title=f"Order #{order.order_number} Delivered",
            message=f"Order #{order.order_number} completed by partner {partner.username}. Payment: {order.payment_status}.",
            notification_type=Notification.TYPE_STATUS_UPDATE,
            icon='task_alt',
            link_url=reverse('admin_order_detail', kwargs={'order_number': order.order_number}),
            order=order
        )
        # Alert Sellers of this order
        seller_ids = order.items.filter(seller__isnull=False).values_list('seller_id', flat=True).distinct()
        for s_id in seller_ids:
            s_user = CustomUser.objects.filter(id=s_id).first()
            if s_user:
                send_system_notification(
                    recipient=s_user,
                    title=f"Order #{order.order_number} Delivered",
                    message=f"Order #{order.order_number} has been delivered to customer {order.shipping_name}.",
                    notification_type=Notification.TYPE_STATUS_UPDATE,
                    icon='task_alt',
                    link_url=reverse('seller_order_detail', kwargs={'order_number': order.order_number}),
                    order=order
                )
        messages.success(request, f"🎉 Order #{order.order_number} verified and marked as Delivered!")

    return redirect('delivery_order_detail', order_number=order.order_number)


@delivery_required
def delivery_history(request):
    """
    Displays completed delivery history for the signed-in delivery partner (or all for Admin).
    """
    partner = request.user
    is_admin_view = partner.is_admin_user() and not partner.is_delivery_partner()

    partner_id_param = request.GET.get('partner_id') or request.session.get('admin_switched_delivery_id')
    if is_admin_view and partner_id_param:
        target_partner = CustomUser.objects.filter(pk=partner_id_param, role=CustomUser.ROLE_DELIVERY).first()
        if target_partner:
            partner = target_partner
            is_admin_view = False

    if is_admin_view:
        deliveries = Order.objects.filter(
            delivery_partner__isnull=False,
            order_status__in=[Order.STATUS_DELIVERED, Order.STATUS_CANCELLED]
        ).order_by('-delivery_delivered_at', '-updated_at')
    else:
        deliveries = Order.objects.filter(
            delivery_partner=partner,
            order_status__in=[Order.STATUS_DELIVERED, Order.STATUS_CANCELLED]
        ).order_by('-delivery_delivered_at', '-updated_at')

    search_q = request.GET.get('q', '').strip()
    if search_q:
        deliveries = deliveries.filter(
            Q(order_number__icontains=search_q) |
            Q(shipping_name__icontains=search_q) |
            Q(shipping_phone__icontains=search_q) |
            Q(shipping_city__icontains=search_q)
        )

    context = {
        'partner': partner,
        'deliveries': deliveries,
        'search_q': search_q,
        'total_delivered': deliveries.filter(order_status=Order.STATUS_DELIVERED).count(),
    }
    return render(request, 'delivery/history.html', context)


@delivery_required
@require_POST
def delivery_order_delete(request, order_number):
    """
    Allows delivery partner / admin to delete an order or remove it from delivery logs.
    """
    order = get_object_or_404(Order, order_number=order_number)
    num = order.order_number
    order.delete()
    messages.success(request, f"Delivery order #{num} deleted successfully.")
    return redirect(request.POST.get('next') or 'delivery_dashboard')


@delivery_required
@require_POST
def delivery_bulk_delete(request):
    """
    Bulk delete selected delivery orders from delivery dashboard or history.
    """
    order_numbers = request.POST.getlist('order_numbers')
    if not order_numbers:
        order_numbers = request.POST.getlist('order_ids')

    next_url = request.POST.get('next') or 'delivery_dashboard'

    if not order_numbers:
        messages.warning(request, "No delivery orders were selected for deletion.")
        return redirect(next_url)

    orders_to_delete = Order.objects.filter(order_number__in=order_numbers)
    count = orders_to_delete.count()
    orders_to_delete.delete()
    messages.success(request, f"Successfully deleted {count} selected delivery order(s).")
    return redirect(next_url)


@delivery_required
def delivery_profile(request):
    """
    Delivery Partner Profile settings: vehicle information, availability, and contact info.
    """
    partner = request.user
    pwd_form = ProfilePasswordChangeForm(user=partner)

    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        if action == 'change_password':
            pwd_form = ProfilePasswordChangeForm(user=partner, data=request.POST)
            if pwd_form.is_valid():
                new_pwd = pwd_form.cleaned_data['new_password']
                partner.set_password(new_pwd)
                partner.save()
                update_session_auth_hash(request, partner)
                messages.success(request, "Your account password was updated successfully!")
                return redirect('delivery_profile')
            else:
                form = DeliveryPartnerProfileForm(instance=partner)
                messages.error(request, "Please check the password errors below.")
        else:
            form = DeliveryPartnerProfileForm(request.POST, request.FILES, instance=partner)
            if form.is_valid():
                form.save()
                messages.success(request, "Delivery partner profile and vehicle details updated successfully!")
                return redirect('delivery_profile')
            else:
                messages.error(request, "Please fix the form errors below.")
    else:
        form = DeliveryPartnerProfileForm(instance=partner)

    assigned_orders = Order.objects.filter(delivery_partner=partner)
    total_delivered = assigned_orders.filter(order_status=Order.STATUS_DELIVERED).count()
    active_count = assigned_orders.filter(
        order_status__in=[
            Order.STATUS_CONFIRMED,
            Order.STATUS_PACKED,
            Order.STATUS_IN_TRANSIT,
            Order.STATUS_OUT_FOR_DELIVERY
        ]
    ).count()

    context = {
        'form': form,
        'pwd_form': pwd_form,
        'partner': partner,
        'total_delivered': total_delivered,
        'active_count': active_count,
    }
    return render(request, 'delivery/profile.html', context)


def api_update_theme(request):
    """
    Asynchronously updates the user's theme preference ('light', 'dark', 'system').
    Saves to the user model if authenticated, and returns JSON confirmation.
    """
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body.decode('utf-8'))
            theme = data.get('theme', '').strip().lower()
        except Exception:
            theme = request.POST.get('theme', '').strip().lower()

        if theme not in ['light', 'dark', 'system']:
            return JsonResponse({'status': 'error', 'message': 'Invalid theme choice.'}, status=400)

        if request.user.is_authenticated:
            request.user.theme_preference = theme
            request.user.save(update_fields=['theme_preference'])

        return JsonResponse({'status': 'success', 'theme': theme})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)


