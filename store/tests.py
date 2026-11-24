from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from store.models import Category, Product, Cart, CartItem, Order, OrderItem, Notification, send_system_notification, Address
from decimal import Decimal

User = get_user_model()


class TechMartTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Admin
        self.admin_user = User.objects.create_user(
            username='adminuser',
            password='adminpassword',
            role=User.ROLE_ADMIN,
            is_staff=True
        )

        # Create Customer
        self.customer_user = User.objects.create_user(
            username='custuser',
            password='custpassword',
            role=User.ROLE_CUSTOMER,
            first_name='Ankit',
            last_name='Kumar',
            email='ankit@example.com'
        )

        # Create Category and Product
        self.category = Category.objects.create(name='Laptops', slug='laptops', icon_name='laptop')
        self.product = Product.objects.create(
            category=self.category,
            name='Test Laptop Pro 16',
            slug='test-laptop-pro-16',
            brand='TestBrand',
            price=Decimal('75000.00'),
            mrp=Decimal('85000.00'),
            stock=10,
            is_featured=True,
            is_deal=True
        )

    def test_public_pages_accessible(self):
        """Verify home, catalog, and product detail load properly."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(response.status_code, 200)

    def test_role_based_permissions_customer_blocked_from_admin(self):
        """Verify customer cannot access admin dashboard and gets redirected with warning."""
        self.client.login(username='custuser', password='custpassword')
        response = self.client.get(reverse('admin_dashboard'))
        # Should redirect to home with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

        # Also test admin products url
        response = self.client.get(reverse('admin_products'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    def test_role_based_permissions_admin_can_access_admin_dashboard(self):
        """Verify admin user can access admin dashboard."""
        self.client.login(username='adminuser', password='adminpassword')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('admin_products'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('admin_categories'))
        self.assertEqual(response.status_code, 200)

    def test_cart_and_checkout_flow(self):
        """Verify adding product to cart and checkout."""
        self.client.login(username='custuser', password='custpassword')

        # Add to cart
        response = self.client.post(reverse('add_to_cart', kwargs={'product_id': self.product.id}), {'quantity': 2})
        self.assertEqual(response.status_code, 302)

        # Check cart
        cart = Cart.objects.get(user=self.customer_user)
        self.assertEqual(cart.total_items, 2)
        self.assertEqual(cart.subtotal, Decimal('150000.00'))

        # Checkout place order
        checkout_data = {
            'selected_address': 'new',
            'full_name': 'Ankit Kumar',
            'phone': '9876543210',
            'address_line1': 'Flat 101, Galaxy Tower',
            'address_line2': 'Andheri West',
            'landmark': 'Near Metro Station',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400053',
            'address_type': 'HOME',
            'payment_method': 'UPI',
        }
        response = self.client.post(reverse('checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)

        # Verify order created
        order = Order.objects.filter(user=self.customer_user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_amount, Decimal('150000.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)

        # Cart should be empty
        self.assertEqual(cart.items.count(), 0)

        # Stock should be reduced from 10 to 8
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_netbanking_checkout_flow_and_gateway(self):
        """Verify checkout with Net Banking captures account details and displays on gateway."""
        self.client.login(username='custuser', password='custpassword')

        # Add to cart
        self.client.post(reverse('add_to_cart', kwargs={'product_id': self.product.id}), {'quantity': 1})

        # Net Banking checkout with bank account details
        checkout_data = {
            'selected_address': 'new',
            'full_name': 'Rahul Sharma',
            'phone': '9876543210',
            'address_line1': '104, Avinashi Road',
            'address_line2': 'Peelamedu',
            'landmark': 'Opposite PSG Tech',
            'city': 'Coimbatore',
            'state': 'Tamil Nadu',
            'pincode': '641004',
            'address_type': 'HOME',
            'payment_method': 'NETBANKING',
            'bank_name': 'State Bank of India (SBI)',
            'bank_account_mode': 'new',
            'bank_account_holder': 'Rahul Sharma',
            'bank_account_type': 'Savings Account',
            'bank_account_number': '30987654321',
            'bank_ifsc': 'SBIN0001234',
            'bank_customer_id': 'CUST_SBI_9876',
            'bank_branch': 'Coimbatore Main Branch',
        }
        response = self.client.post(reverse('checkout'), checkout_data)
        self.assertEqual(response.status_code, 302)

        order = Order.objects.filter(user=self.customer_user, payment_method='NETBANKING').latest('created_at')
        self.assertEqual(response.url, reverse('payment_gateway', kwargs={'order_number': order.order_number}))

        # Load payment gateway and verify bank details are present
        gw_response = self.client.get(reverse('payment_gateway', kwargs={'order_number': order.order_number}))
        self.assertEqual(gw_response.status_code, 200)
        self.assertContains(gw_response, 'State Bank of India (SBI)')
        self.assertContains(gw_response, 'Rahul Sharma')
        self.assertContains(gw_response, '•••• •••• 4321')
        self.assertContains(gw_response, 'SBIN0001234')
        self.assertContains(gw_response, 'Coimbatore Main Branch')

    def test_customer_registration_and_otp_verification(self):
        """Verify customer registration generates OTP and verifies account."""
        from store.models import OTPVerification

        reg_data = {
            'username': 'newcustomer',
            'first_name': 'Priya',
            'last_name': 'Natarajan',
            'email': 'priya@example.com',
            'phone': '9840123456',
            'gst_number': '',
            'password1': 'CustomerPass123!',
            'password2': 'CustomerPass123!',
        }
        res = self.client.post(reverse('register'), reg_data)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('verify_registration_otp'))

        # Check OTP verification record
        otp_rec = OTPVerification.objects.filter(phone_or_email='9840123456', purpose=OTPVerification.PURPOSE_REGISTRATION).first()
        self.assertIsNotNone(otp_rec)
        self.assertFalse(otp_rec.is_verified)
        self.assertEqual(len(otp_rec.otp_code), 6)

        # Test invalid OTP code
        res_wrong = self.client.post(reverse('verify_registration_otp'), {'otp': '000000'})
        self.assertEqual(res_wrong.status_code, 200) # Re-renders with error
        self.assertFalse(User.objects.filter(username='newcustomer').exists())

        # Test valid OTP code
        res_correct = self.client.post(reverse('verify_registration_otp'), {'otp': otp_rec.otp_code})
        self.assertEqual(res_correct.status_code, 302)
        self.assertEqual(res_correct.url, reverse('home'))

        # Verify created user
        new_user = User.objects.get(username='newcustomer')
        self.assertEqual(new_user.role, User.ROLE_CUSTOMER)
        self.assertTrue(new_user.is_verified)
        self.assertEqual(new_user.phone, '9840123456')

    def test_customer_otp_login_flow(self):
        """Verify customer can log in using 6-digit OTP without password."""
        from store.models import OTPVerification

        # Customer requests login OTP using registered username
        res = self.client.post(reverse('login_otp'), {'identifier': 'custuser'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('verify_login_otp'))

        otp_rec = OTPVerification.objects.filter(user=self.customer_user, purpose=OTPVerification.PURPOSE_LOGIN).first()
        self.assertIsNotNone(otp_rec)

        # Submit valid OTP
        res_verify = self.client.post(reverse('verify_login_otp'), {'otp': otp_rec.otp_code})
        self.assertEqual(res_verify.status_code, 302)
        self.assertEqual(res_verify.url, reverse('home'))

    def test_admin_blocked_from_customer_otp_login(self):
        """Verify admin user is blocked from bypassing password via customer OTP."""
        res = self.client.post(reverse('login_otp'), {'identifier': 'adminuser'})
        self.assertEqual(res.status_code, 200) # Does not redirect to verify
        # Session should not have login_otp_id
        self.assertNotIn('login_otp_id', self.client.session)

    def test_cod_checkout_with_otp_verification(self):
        """Verify Cash on Delivery requires and validates 6-digit OTP code."""
        from store.models import OTPVerification
        from datetime import timedelta
        from django.utils import timezone

        self.client.login(username='custuser', password='custpassword')

        # Add item to cart
        self.client.post(reverse('add_to_cart', kwargs={'product_id': self.product.id}), {'quantity': 1})

        # Try COD checkout WITHOUT OTP -> should fail / re-render
        bad_cod_data = {
            'selected_address': 'new',
            'full_name': 'Ankit Kumar',
            'phone': '9876543210',
            'address_line1': 'Flat 101, Galaxy Tower',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400053',
            'address_type': 'HOME',
            'payment_method': 'COD',
            'cod_otp': '000000',
        }
        res_fail = self.client.post(reverse('checkout'), bad_cod_data)
        self.assertEqual(res_fail.status_code, 200)
        self.assertIn('cod_error', res_fail.context)

        # Generate valid COD OTP
        otp_code = '582914'
        OTPVerification.objects.create(
            phone_or_email='9876543210',
            otp_code=otp_code,
            purpose=OTPVerification.PURPOSE_COD,
            user=self.customer_user,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

        # Submit COD checkout WITH valid OTP -> should succeed and create order
        valid_cod_data = bad_cod_data.copy()
        valid_cod_data['cod_otp'] = otp_code
        res_success = self.client.post(reverse('checkout'), valid_cod_data)
        self.assertEqual(res_success.status_code, 302)

        # Verify order created with payment_status=PENDING and payment_method=COD
        cod_order = Order.objects.filter(user=self.customer_user, payment_method=Order.PAY_COD).first()
        self.assertIsNotNone(cod_order)
        self.assertEqual(cod_order.payment_status, Order.PAY_STATUS_PENDING)

    def test_customer_cancel_order_restores_stock_and_initiates_refund(self):
        """Verify cancelling an active prepaid order updates status, initiates refund, and restores stock."""
        self.client.login(username='custuser', password='custpassword')

        initial_stock = self.product.stock  # 10
        order = Order.objects.create(
            user=self.customer_user,
            shipping_name='Ankit Kumar',
            shipping_phone='9876543210',
            shipping_address_line1='Flat 101, Galaxy Tower',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_pincode='400053',
            subtotal=self.product.price * 2,
            delivery_charge=Decimal('0.00'),
            gst_amount=Decimal('0.00'),
            total_amount=self.product.price * 2,
            payment_method=Order.PAY_UPI,
            payment_status=Order.PAY_STATUS_PAID,
            order_status=Order.STATUS_CONFIRMED,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            mrp=self.product.mrp,
            quantity=2,
            line_total=self.product.price * 2
        )
        # Deduct stock as would happen at checkout
        self.product.stock -= 2
        self.product.save()

        self.assertTrue(order.can_cancel)

        # Cancel the order
        cancel_url = reverse('customer_cancel_order', kwargs={'order_number': order.order_number})
        res = self.client.post(cancel_url, {'cancellation_reason': 'Ordered by mistake / Change of mind'})
        self.assertEqual(res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.STATUS_CANCELLED)
        self.assertEqual(order.payment_status, Order.PAY_STATUS_REFUNDED)
        self.assertEqual(order.cancellation_reason, 'Ordered by mistake / Change of mind')

        # Verify stock was restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_delivered_order_cannot_be_cancelled(self):
        """Verify delivered order can_cancel is False and cancel POST is rejected."""
        self.client.login(username='custuser', password='custpassword')

        order = Order.objects.create(
            user=self.customer_user,
            shipping_name='Ankit Kumar',
            shipping_phone='9876543210',
            shipping_address_line1='Flat 101, Galaxy Tower',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_pincode='400053',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            order_status=Order.STATUS_DELIVERED,
        )
        self.assertFalse(order.can_cancel)

        cancel_url = reverse('customer_cancel_order', kwargs={'order_number': order.order_number})
        res = self.client.post(cancel_url, {'cancellation_reason': 'Too late'})
        self.assertEqual(res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.STATUS_DELIVERED)

    def test_other_customer_cannot_cancel_unauthorized_order(self):
        """Verify another customer cannot cancel someone else's order."""
        other_user = User.objects.create_user(
            username='othercust',
            password='otherpassword',
            role=User.ROLE_CUSTOMER
        )
        self.client.login(username='othercust', password='otherpassword')

        order = Order.objects.create(
            user=self.customer_user,
            shipping_name='Ankit Kumar',
            shipping_phone='9876543210',
            shipping_address_line1='Flat 101, Galaxy Tower',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_pincode='400053',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            order_status=Order.STATUS_CONFIRMED,
        )

        cancel_url = reverse('customer_cancel_order', kwargs={'order_number': order.order_number})
        res = self.client.post(cancel_url, {'cancellation_reason': 'Hacker attempt'})
        self.assertEqual(res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.STATUS_CONFIRMED)

    def test_notifications_bidirectional_admin_and_customer(self):
        """Verify bi-directional notifications: customer actions notify admin, admin updates notify customer."""
        # 1. Customer login triggers admin notification via login view POST
        self.client.post(reverse('login'), {'username': 'custuser', 'password': 'custpassword'})
        admin_login_notifs = Notification.objects.filter(for_admin=True, notification_type=Notification.TYPE_LOGIN)
        self.assertTrue(admin_login_notifs.exists())

        # 2. Customer places COD order with valid OTP -> Admin & Customer get notifications
        from store.models import OTPVerification
        from datetime import timedelta
        from django.utils import timezone
        
        # Add item to cart
        self.client.post(reverse('add_to_cart', kwargs={'product_id': self.product.id}), {'quantity': 1})
        otp_code = '736291'
        OTPVerification.objects.create(
            phone_or_email='9876543210',
            otp_code=otp_code,
            purpose=OTPVerification.PURPOSE_COD,
            user=self.customer_user,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        cod_data = {
            'selected_address': 'new',
            'full_name': 'Ankit Kumar',
            'phone': '9876543210',
            'address_line1': 'Flat 101, Galaxy Tower',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400053',
            'address_type': 'HOME',
            'payment_method': 'COD',
            'cod_otp': otp_code,
        }
        res_order = self.client.post(reverse('checkout'), cod_data)
        self.assertEqual(res_order.status_code, 302)

        created_order = Order.objects.filter(user=self.customer_user, payment_method=Order.PAY_COD).first()
        self.assertIsNotNone(created_order)

        # Check Admin received order notification
        admin_order_notifs = Notification.objects.filter(for_admin=True, order=created_order, notification_type=Notification.TYPE_ORDER)
        self.assertTrue(admin_order_notifs.exists())

        # Check Customer received order confirmation notification
        cust_order_notifs = Notification.objects.filter(recipient=self.customer_user, order=created_order)
        self.assertTrue(cust_order_notifs.exists())

        # 3. Admin updates order status and adds special instruction -> Customer receives notifications
        self.client.login(username='adminuser', password='adminpassword')
        update_url = reverse('admin_order_detail', kwargs={'order_number': created_order.order_number})
        post_data = {
            'order_status': Order.STATUS_PACKED,
            'payment_status': Order.PAY_STATUS_PENDING,
            'courier_name': 'Bluedart Priority',
            'tracking_number': 'BLUEDART12345',
            'current_location': 'Bhiwandi Hub',
            'estimated_delivery_text': 'Tomorrow by 11:00 AM',
            'admin_instruction': 'Package sanitized and sealed with official tamper proof tape.',
        }
        res_update = self.client.post(update_url, post_data)
        self.assertEqual(res_update.status_code, 302)

        # Verify customer received the status milestone notification
        status_notifs = Notification.objects.filter(
            recipient=self.customer_user,
            order=created_order,
            notification_type=Notification.TYPE_STATUS_UPDATE
        )
        self.assertTrue(status_notifs.exists())

        # Verify customer received the special instruction notification
        instruction_notifs = Notification.objects.filter(
            recipient=self.customer_user,
            order=created_order,
            notification_type=Notification.TYPE_INSTRUCTION
        )
        self.assertTrue(instruction_notifs.exists())
        self.assertIn('tamper proof tape', instruction_notifs.first().message)

        # 4. Customer views notifications page and marks all read
        self.client.login(username='custuser', password='custpassword')
        res_list = self.client.get(reverse('notifications_list'))
        self.assertEqual(res_list.status_code, 200)

        # Mark all read
        res_mark_all = self.client.post(reverse('notifications_mark_all_read'))
        self.assertEqual(res_mark_all.status_code, 302)
        unread_count = Notification.objects.filter(recipient=self.customer_user, is_read=False).count()
        self.assertEqual(unread_count, 0)

    def test_admin_broadcast_notification(self):
        """Verify Admin can broadcast storewide announcement to all customers."""
        self.client.login(username='adminuser', password='adminpassword')

        broadcast_url = reverse('admin_broadcast_notification')
        post_data = {
            'target': 'all',
            'title': 'Mega Tech Fest Announced!',
            'message': 'Flat 20% discount on all premium laptops this weekend!',
            'icon': 'campaign',
            'link_url': '/products/',
        }
        res = self.client.post(broadcast_url, post_data)
        self.assertEqual(res.status_code, 302)

        # Verify customer received the broadcast
        cust_notif = Notification.objects.filter(
            recipient=self.customer_user,
            title='Mega Tech Fest Announced!'
        ).first()
        self.assertIsNotNone(cust_notif)
        self.assertEqual(cust_notif.notification_type, Notification.TYPE_INSTRUCTION)
        self.assertEqual(cust_notif.link_url, '/products/')

    def test_customer_can_delete_address(self):
        """Verify customer can delete saved delivery addresses from list or checkout."""
        self.client.login(username='custuser', password='custpassword')

        addr1 = Address.objects.create(
            user=self.customer_user,
            full_name='Ankit Kumar Home',
            phone='9876543210',
            address_line1='Flat 101, Galaxy Tower',
            city='Coimbatore',
            state='Tamil Nadu',
            pincode='641001',
            is_default=True
        )
        addr2 = Address.objects.create(
            user=self.customer_user,
            full_name='Ankit Kumar Office',
            phone='9876543210',
            address_line1='Tech Park, Avinashi Road',
            city='Coimbatore',
            state='Tamil Nadu',
            pincode='641018',
            is_default=False
        )

        # Delete default address with redirect to checkout
        del_url = reverse('address_delete', kwargs={'pk': addr1.id})
        res = self.client.post(del_url, {'next': reverse('checkout')})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('checkout'))

        # Verify addr1 deleted
        self.assertFalse(Address.objects.filter(id=addr1.id).exists())

        # Verify addr2 automatically promoted to default
        addr2.refresh_from_db()
        self.assertTrue(addr2.is_default)

    def test_customer_can_delete_single_order(self):
        """Verify that a customer can delete an individual order from history."""
        self.client.login(username='custuser', password='custpassword')
        order = Order.objects.create(
            user=self.customer_user,
            order_number='TM-DEL-001',
            subtotal=Decimal('59990.00'),
            total_amount=Decimal('59990.00'),
            order_status=Order.STATUS_CANCELLED,
            payment_method=Order.PAY_COD,
            shipping_name='Rahul Test',
            shipping_phone='9876543210',
            shipping_address_line1='Sample street',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            mrp=self.product.mrp,
            quantity=1,
            line_total=self.product.price
        )

        del_url = reverse('customer_delete_order', kwargs={'order_number': order.order_number})
        res = self.client.post(del_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Order.objects.filter(order_number='TM-DEL-001').exists())
        self.assertFalse(OrderItem.objects.filter(product_name=self.product.name, order__order_number='TM-DEL-001').exists())

    def test_customer_can_bulk_delete_orders(self):
        """Verify that a customer can select multiple orders and delete them all at once."""
        self.client.login(username='custuser', password='custpassword')
        ord1 = Order.objects.create(
            user=self.customer_user,
            order_number='TM-BULK-001',
            subtotal=Decimal('10000.00'),
            total_amount=Decimal('10000.00'),
            order_status=Order.STATUS_CANCELLED,
            payment_method=Order.PAY_UPI,
            shipping_name='Rahul Test',
            shipping_phone='9876543210',
            shipping_address_line1='Sample street',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001'
        )
        ord2 = Order.objects.create(
            user=self.customer_user,
            order_number='TM-BULK-002',
            subtotal=Decimal('20000.00'),
            total_amount=Decimal('20000.00'),
            order_status=Order.STATUS_CANCELLED,
            payment_method=Order.PAY_UPI,
            shipping_name='Rahul Test',
            shipping_phone='9876543210',
            shipping_address_line1='Sample street',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001'
        )

        bulk_url = reverse('customer_bulk_delete_orders')
        res = self.client.post(bulk_url, {'order_ids': ['TM-BULK-001', 'TM-BULK-002']})
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Order.objects.filter(order_number__in=['TM-BULK-001', 'TM-BULK-002']).exists())

    def test_customer_clear_all_cancelled_orders(self):
        """Verify that customer can one-click clear all cancelled orders while preserving active orders."""
        self.client.login(username='custuser', password='custpassword')
        ord_cancelled = Order.objects.create(
            user=self.customer_user,
            order_number='TM-CLEAR-CANCELLED',
            subtotal=Decimal('5000.00'),
            total_amount=Decimal('5000.00'),
            order_status=Order.STATUS_CANCELLED,
            payment_method=Order.PAY_COD,
            shipping_name='Rahul Test',
            shipping_phone='9876543210',
            shipping_address_line1='Sample street',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001'
        )
        ord_active = Order.objects.create(
            user=self.customer_user,
            order_number='TM-ACTIVE-KEEP',
            subtotal=Decimal('15000.00'),
            total_amount=Decimal('15000.00'),
            order_status=Order.STATUS_CONFIRMED,
            payment_method=Order.PAY_COD,
            shipping_name='Rahul Test',
            shipping_phone='9876543210',
            shipping_address_line1='Sample street',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001'
        )

        bulk_url = reverse('customer_bulk_delete_orders')
        res = self.client.post(bulk_url, {'action': 'clear_cancelled'})
        self.assertEqual(res.status_code, 302)

        # Cancelled order should be deleted
        self.assertFalse(Order.objects.filter(order_number='TM-CLEAR-CANCELLED').exists())
        # Active order must be retained
        self.assertTrue(Order.objects.filter(order_number='TM-ACTIVE-KEEP').exists())

    def test_login_with_email_address(self):
        """Verify customer can log in using email address instead of username."""
        # Using self.customer_user (email: ankit@example.com)
        res = self.client.post(reverse('login'), {
            'username': 'ankit@example.com',
            'password': 'custpassword'
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.wsgi_request.user.is_authenticated)
        self.assertEqual(res.wsgi_request.user.username, 'custuser')

    def test_payment_cancel_idempotence(self):
        """Verify calling payment_cancel multiple times does not restore inventory stock multiple times."""
        self.client.login(username='custuser', password='custpassword')
        initial_stock = self.product.stock  # 10
        order = Order.objects.create(
            user=self.customer_user,
            shipping_name='Ankit Kumar',
            shipping_phone='9876543210',
            shipping_address_line1='Flat 101',
            shipping_city='Mumbai',
            shipping_state='Maharashtra',
            shipping_pincode='400053',
            subtotal=Decimal('75000.00'),
            total_amount=Decimal('75000.00'),
            order_status=Order.STATUS_CONFIRMED,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            price=self.product.price,
            mrp=self.product.mrp,
            quantity=1,
            line_total=self.product.price
        )
        self.product.stock = 9
        self.product.save()

        cancel_url = reverse('payment_cancel', kwargs={'order_number': order.order_number})
        # 1st cancel
        self.client.post(cancel_url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

        # 2nd cancel should NOT increment stock again
        self.client.post(cancel_url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_admin_category_delete_protection_when_has_products(self):
        """Verify that deleting a category containing products is rejected with a warning."""
        self.client.login(username='adminuser', password='adminpassword')
        del_url = reverse('admin_category_delete', kwargs={'pk': self.category.pk})
        res = self.client.post(del_url, follow=True)
        self.assertEqual(res.status_code, 200)
        # Category should still exist
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_cart_invalid_quantity_safe_fallback(self):
        """Verify that non-numeric or negative quantity in add_to_cart safely defaults to 1."""
        res = self.client.post(
            reverse('add_to_cart', kwargs={'product_id': self.product.id}),
            {'quantity': 'invalid_string'}
        )
        self.assertEqual(res.status_code, 302)
        cart = Cart.objects.filter(session_key=self.client.session.session_key).first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.total_items, 1)

    def test_dynamic_order_year_generation(self):
        """Verify order numbers use the current dynamic year instead of a hardcoded year."""
        from django.utils import timezone
        current_year = str(timezone.now().year)
        order = Order.objects.create(
            user=self.customer_user,
            shipping_name='Test',
            shipping_phone='9876543210',
            shipping_address_line1='Test line',
            shipping_city='Coimbatore',
            shipping_state='Tamil Nadu',
            shipping_pincode='641001',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
        )
        self.assertTrue(order.order_number.startswith(f"TM-{current_year}-"))

    def test_theme_preference_default_and_api_update(self):
        """Verify user theme preference defaults to 'system' and can be updated via API."""
        self.assertEqual(self.customer_user.theme_preference, 'system')

        self.client.login(username='custuser', password='custpassword')
        # Update to dark
        res = self.client.post(
            reverse('api_update_theme'),
            data={'theme': 'dark'},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get('theme'), 'dark')
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.theme_preference, 'dark')

        # Update to light
        res = self.client.post(
            reverse('api_update_theme'),
            data={'theme': 'light'},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.theme_preference, 'light')

        # Invalid choice rejected
        res = self.client.post(
            reverse('api_update_theme'),
            data={'theme': 'invalid_theme'},
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 400)

    def test_admin_customer_bulk_delete_and_single_delete(self):
        """Verify admin can delete customer, seller, and delivery partner accounts."""
        self.client.login(username='adminuser', password='adminpassword')

        # Create temporary seller and customer
        temp_seller = User.objects.create_user(
            username='tempseller',
            email='tempseller@techmart.in',
            password='sellerpass123',
            role=User.ROLE_SELLER,
            store_name='Temp Seller Store'
        )
        temp_cust = User.objects.create_user(
            username='tempcust',
            email='tempcust@techmart.in',
            password='custpass123',
            role=User.ROLE_CUSTOMER
        )

        # Test bulk delete with seller and customer accounts
        res = self.client.post(
            reverse('admin_customer_bulk_delete'),
            data={'selected_customers': [temp_seller.id, temp_cust.id]}
        )
        self.assertEqual(res.status_code, 302)
        self.assertFalse(User.objects.filter(username='tempseller').exists())
        self.assertFalse(User.objects.filter(username='tempcust').exists())

        # Test single delete
        temp_deliv = User.objects.create_user(
            username='tempdeliv',
            email='tempdeliv@techmart.in',
            password='delivpass123',
            role=User.ROLE_DELIVERY
        )
        res_del = self.client.post(reverse('admin_customer_delete', kwargs={'pk': temp_deliv.id}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(User.objects.filter(username='tempdeliv').exists())








