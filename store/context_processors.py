from .models import Category, Cart, Order, Notification, Address

def cart_and_categories(request):
    categories = Category.objects.all().only('id', 'name', 'slug')
    cart_item_count = 0
    cart_subtotal = 0
    active_orders_count = 0
    unread_notifications_count = 0
    recent_notifications = []
    delivery_city = 'Coimbatore'
    delivery_pincode = '641001'

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).prefetch_related('items__product').first()
        if cart:
            items = list(cart.items.all())
            cart_item_count = sum(item.quantity for item in items)
            cart_subtotal = sum(item.product.price * item.quantity for item in items)

        active_orders_count = Order.objects.filter(
            user=request.user,
            order_status__in=[
                Order.STATUS_CONFIRMED,
                Order.STATUS_PACKED,
                Order.STATUS_IN_TRANSIT,
                Order.STATUS_OUT_FOR_DELIVERY
            ]
        ).count()

        user_notifs = Notification.objects.filter(recipient=request.user)
        if getattr(request.user, 'role', '') == 'SELLER' or request.path.startswith('/seller/') or request.GET.get('role') == 'seller':
            user_notifs = user_notifs.exclude(
                notification_type=Notification.TYPE_LOGIN
            ).exclude(
                link_url__startswith='/admin-dashboard/'
            )
        unread_notifications_count = user_notifs.filter(is_read=False).count()
        recent_notifications = list(user_notifs.order_by('-created_at')[:25])

        # Single query with order_by to get default or first address
        default_addr = Address.objects.filter(user=request.user).order_by('-is_default', 'id').first()
        if default_addr:
            delivery_city = default_addr.city
            delivery_pincode = default_addr.pincode
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).prefetch_related('items__product').first()
            if cart:
                items = list(cart.items.all())
                cart_item_count = sum(item.quantity for item in items)
                cart_subtotal = sum(item.product.price * item.quantity for item in items)

    return {
        'all_categories': categories,
        'cart_item_count': cart_item_count,
        'cart_subtotal': cart_subtotal,
        'active_orders_count': active_orders_count,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
        'delivery_city': delivery_city,
        'delivery_pincode': delivery_pincode,
        'SITE_NAME': 'Tech Mart',
        'is_admin': request.user.is_authenticated and request.user.is_admin_user(),
    }
