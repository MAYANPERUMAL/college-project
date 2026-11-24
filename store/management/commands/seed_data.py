from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Category, Product, Address, Order, OrderItem, Cart, CartItem
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = "Populate Tech Mart with comprehensive initial categories, products, admin and demo customer data"

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding for Tech Mart...")

        # 1. Admin Account
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@techmart.in',
                'first_name': 'Admin',
                'last_name': 'Officer',
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'membership_tier': User.MEMBERSHIP_PLATINUM,
            }
        )
        admin_user.set_password('admin123')
        admin_user.role = User.ROLE_ADMIN
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("✓ Admin user created: admin / admin123"))

        # 2. Demo Customer Account (Rahul Sharma - matches code.html design)
        customer_user, created = User.objects.get_or_create(
            username='rahul',
            defaults={
                'email': 'rahul.sharma@example.com',
                'first_name': 'Rahul',
                'last_name': 'Sharma',
                'phone': '+91 98201 44829',
                'gst_number': '27AAACH8291Q1ZT',
                'role': User.ROLE_CUSTOMER,
                'membership_tier': User.MEMBERSHIP_PLATINUM,
                'wallet_balance': Decimal('1250.00'),
            }
        )
        customer_user.set_password('customer123')
        customer_user.role = User.ROLE_CUSTOMER
        customer_user.phone = '+91 98201 44829'
        customer_user.gst_number = '27AAACH8291Q1ZT'
        customer_user.membership_tier = User.MEMBERSHIP_PLATINUM
        customer_user.wallet_balance = Decimal('1250.00')
        customer_user.save()
        self.stdout.write(self.style.SUCCESS("✓ Demo customer created: rahul / customer123"))

        # 3. Demo Seller Account
        seller_user, _ = User.objects.get_or_create(
            username='seller_tech',
            defaults={
                'email': 'seller@techmart.in',
                'first_name': 'Dinesh',
                'last_name': 'Kumar',
                'phone': '9876543220',
                'role': User.ROLE_SELLER,
                'store_name': 'TechZone Electronics',
                'seller_bio': 'Authorized electronics dealer offering genuine branded products with warranty.',
                'gst_number': '33AAACH8291Q1ZT',
                'is_verified': True,
            }
        )
        seller_user.set_password('seller123')
        seller_user.role = User.ROLE_SELLER
        seller_user.save()
        self.stdout.write(self.style.SUCCESS("✓ Demo seller created: seller_tech / seller123"))

        # 4. Demo Delivery Partners
        delivery_ravi, _ = User.objects.get_or_create(
            username='delivery_ravi',
            defaults={
                'email': 'ravi@delivery.techmart.in',
                'first_name': 'Ravi',
                'last_name': 'Kumar',
                'phone': '9876543221',
                'role': User.ROLE_DELIVERY,
                'vehicle_type': 'Motorcycle',
                'vehicle_number': 'TN-38-BZ-4412',
                'current_city': 'Coimbatore',
                'is_available': True,
                'is_verified': True,
            }
        )
        delivery_ravi.set_password('delivery123')
        delivery_ravi.role = User.ROLE_DELIVERY
        delivery_ravi.save()
        self.stdout.write(self.style.SUCCESS("✓ Demo delivery partner created: delivery_ravi / delivery123"))

        delivery_suresh, _ = User.objects.get_or_create(
            username='delivery_suresh',
            defaults={
                'email': 'suresh@delivery.techmart.in',
                'first_name': 'Suresh',
                'last_name': 'R',
                'phone': '9876543222',
                'role': User.ROLE_DELIVERY,
                'vehicle_type': 'EV Scooter',
                'vehicle_number': 'TN-38-CK-8821',
                'current_city': 'Coimbatore',
                'is_available': True,
                'is_verified': True,
            }
        )
        delivery_suresh.set_password('delivery123')
        delivery_suresh.role = User.ROLE_DELIVERY
        delivery_suresh.save()
        self.stdout.write(self.style.SUCCESS("✓ Demo delivery partner created: delivery_suresh / delivery123"))

        # 5. Categories
        categories_data = [
            ('Mobiles & Tablets', 'mobiles-tablets', 'smartphone', 'Flagship 5G phones and pro tablets', 1),
            ('Laptops & Computing', 'laptops-computing', 'laptop_mac', 'Thin & lights, creators, and work stations', 2),
            ('Audio & Headphones', 'audio-headphones', 'headphones', 'ANC noise cancelling headphones, earbuds and speakers', 3),
            ('Smart TVs & Appliances', 'smart-tvs-appliances', 'tv', '4K OLED displays, Google TVs and smart appliances', 4),
            ('Smartwatches & Wearables', 'smartwatches-wearables', 'watch', 'Fitness trackers, cellular smartwatches, and smart rings', 5),
            ('Accessories & Peripherals', 'accessories', 'mouse', 'High precision mice, mechanical keyboards, chargers and cases', 6),
        ]

        categories_map = {}
        for name, slug, icon, desc, order in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon_name': icon, 'description': desc, 'order': order}
            )
            categories_map[slug] = cat
        self.stdout.write(self.style.SUCCESS(f"✓ {len(categories_map)} categories verified."))

        # 4. Products
        products_data = [
            {
                'category': categories_map['laptops-computing'],
                'name': 'Apple MacBook Air M3 (13.6-inch, 16GB Unified Memory, 512GB SSD, Midnight)',
                'slug': 'apple-macbook-air-m3-midnight',
                'brand': 'Apple',
                'model_number': 'MRXN3HN/A',
                'price': Decimal('114900.00'),
                'mrp': Decimal('124900.00'),
                'stock': 12,
                'is_featured': True,
                'is_deal': True,
                'deal_tag': 'Republic Day Mega Deal',
                'warranty_info': 'Official Apple India 1-Year Warranty',
                'rating': Decimal('4.9'),
                'reviews_count': 48,
                'image_url': 'https://lh3.googleusercontent.com/aida-public/AB6AXuDcUX50XUav1JENLiMLIiekKOsJ8cJOc5eA-WMe8wSFDdX_vEhc3V5dJ_Cab16ycqCPQBSdAhwUI6pplDRiKCSriHx9PwSlJRY08Sfy-qmwZIUNCUKi3i6OF13TLZmn50-Uu4p_NvZouQSzbP_VSHMd49gkCVnTKeR12-kytdl0CQ8tAZNL8_3451XgXyns-Pyk4AHVtd_TzGsC852B0vKH8XbsH40OKMmwh4YOm9BX',
                'specs': '13.6-inch Liquid Retina Display with True Tone\nApple M3 chip with 8-core CPU and 10-core GPU\n16GB Unified Memory for effortless multitasking\n512GB ultra-fast SSD storage\nMagSafe 3 charging port and two Thunderbolt / USB 4 ports\nUp to 18 hours of battery life with silent fanless design',
                'description': 'The redesigned MacBook Air M3 is supercharged by the next-generation M3 chip, delivering extraordinary speed and power efficiency inside an impossibly thin aluminum enclosure. Work, game, and create anything, anywhere.'
            },
            {
                'category': categories_map['audio-headphones'],
                'name': 'Sony WH-1000XM5 Wireless Active Noise Cancelling Headphones (Platinum Silver)',
                'slug': 'sony-wh-1000xm5-silver',
                'brand': 'Sony',
                'model_number': 'WH1000XM5/S',
                'price': Decimal('26990.00'),
                'mrp': Decimal('34990.00'),
                'stock': 18,
                'is_featured': True,
                'is_deal': True,
                'deal_tag': 'Spotlight Deal',
                'warranty_info': 'Sony Official 1-Yr Brand Warranty',
                'rating': Decimal('4.8'),
                'reviews_count': 92,
                'image_url': 'https://lh3.googleusercontent.com/aida-public/AB6AXuDoXyDBESgjP-S4pV3wQYfYxFU0x16NTpucxIQtbYQLMCWewAmt-ZCuWtsoQMFDTDNhCfTnTmjTszn_bAATlK6v07YWP6_xBMW6bskb3ybHkWuRoK-U1Y8IEw5lM8zoid2xH5MxpoEVtzC2A0lx6Sfxi1S04P-RalPshmBAhHXjmUiaEMXsOFOQA8tw19FzXlGZ3WIHlkfGU0olsMo7fIofkVHYItKGARNhAF0M3rzg',
                'specs': 'Auto NC Optimizer automatically adjusts noise cancelling based on wearing conditions\nSpecially developed 30mm carbon driver unit delivers high-resolution audio\nCrystal-clear hands-free calling with 4 beamforming microphones\nMultipoint connection allows switching between two devices seamlessly\nUp to 30-hour battery life with 3-minute quick charging for 3 hours playback',
                'description': 'With two processors and eight microphones, the Sony WH-1000XM5 pushes the boundaries of active noise cancellation and sound immersion. Designed with soft fit leather for fatigue-free all-day comfort.'
            },
            {
                'category': categories_map['accessories'],
                'name': 'OnePlus 12 Protective Bumper Case (Emerald Green)',
                'slug': 'oneplus-12-protective-bumper-case-emerald',
                'brand': 'OnePlus',
                'model_number': 'OP12-CASE-EM',
                'price': Decimal('1299.00'),
                'mrp': Decimal('1999.00'),
                'stock': 35,
                'is_featured': False,
                'is_deal': False,
                'deal_tag': '',
                'warranty_info': '6-Month Official Brand Warranty',
                'rating': Decimal('4.6'),
                'reviews_count': 14,
                'image_url': 'https://lh3.googleusercontent.com/aida-public/AB6AXuBvQ2d5X-LNVZ0CDmKzs4RZs10lB33SimJY9zqZP2jGOAyYsW0UGFRsj5bY6IxQfg1GX6H9HPMSjczA-KbCrfhKGpoNgOZpwQzWKFV3JTycxOQNxS_m8iEd7DWLDaJD1bViw1ewJYOCXIL3xLrvxOv1NL_EE_mujxUerenCN7ytKn6MtjQOi5m62XRZX2VcOD-K_KM96tHK7OKB9vzUh5JbRX0rnr0Mkg0smF2mehyU',
                'specs': 'Impact-absorbing corner air cushions\nTactile matte grip texture prevents slips\nRaised edges to safeguard screen and camera module\nPrecision cutouts for alert slider and microphone ports',
                'description': 'Engineered to preserve the sleek form factor of your OnePlus 12 while delivering reliable drop defense and tactile grip.'
            },
            {
                'category': categories_map['accessories'],
                'name': 'Logitech MX Master 3S Wireless Performance Mouse (Graphite)',
                'slug': 'logitech-mx-master-3s-graphite',
                'brand': 'Logitech',
                'model_number': '910-006561',
                'price': Decimal('8495.00'),
                'mrp': Decimal('10995.00'),
                'stock': 20,
                'is_featured': True,
                'is_deal': False,
                'deal_tag': '',
                'warranty_info': '1-Year Logitech India Limited Hardware Warranty',
                'rating': Decimal('4.9'),
                'reviews_count': 76,
                'image_url': 'https://lh3.googleusercontent.com/aida-public/AB6AXuDE5dLj9h3VWGomAy8dw_ZCpQlOcLcf_GpBWPk3cNuP0bNLZfWz-7mDlQo1lCCjXy8QTdBGa3x7RszzBVYLYqlq_D1MvjhZMX9FhIBUKn5e-BMyrYIV4n5h5gg1lFte1myOADbFci4gKzpixxbqp7iapW-cqgehcjOcQsQk-lixUZp5Nm8Mv0TCxLfprmXccTP-ug7AQNv04HaS2Q9Tuqlu5PGuRobleo_xThk58l9L',
                'specs': 'Quiet Clicks deliver satisfying tactile feel with 90% less click noise\n8,000 DPI track-on-glass optical sensor\nMagSpeed electromagnetic scrolling scrolls 1,000 lines per second\nConnect across up to 3 computers with Logitech Flow\nUSB-C quick recharge: 1 min charge gives 3 hours use',
                'description': 'An icon remastered. Feel every moment of your workflow with even more precision, tactility, and performance, thanks to Quiet Clicks and an 8,000 DPI track-on-glass sensor.'
            },
            {
                'category': categories_map['mobiles-tablets'],
                'name': 'Samsung Galaxy S24 Ultra 5G (Titanium Gray, 12GB RAM, 256GB Storage)',
                'slug': 'samsung-galaxy-s24-ultra-titanium',
                'brand': 'Samsung',
                'model_number': 'SM-S928B',
                'price': Decimal('129999.00'),
                'mrp': Decimal('144999.00'),
                'stock': 7,
                'is_featured': True,
                'is_deal': True,
                'deal_tag': 'Flagship Festival Drop',
                'warranty_info': 'Samsung India 1-Year Comprehensive Warranty',
                'rating': Decimal('4.9'),
                'reviews_count': 118,
                'image_url': 'https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=600&q=80',
                'specs': '6.8-inch Dynamic AMOLED 2X Display (120Hz, 2600 nits peak brightness)\nSnapdragon 8 Gen 3 for Galaxy with ray-tracing hardware support\n200MP Quad Telephoto Camera with ProVisual AI Engine\nBuilt-in S Pen with titanium chassis\n5000 mAh intelligent battery with 45W super fast charge',
                'description': 'Meet Galaxy S24 Ultra with Galaxy AI. Search like never before, get quick language interpretation on a call, convert voice recordings into summaries, and effortlessly edit your photos.'
            },
            {
                'category': categories_map['smart-tvs-appliances'],
                'name': 'Sony Bravia 55-inch 4K Ultra HD Smart Google TV (Black)',
                'slug': 'sony-bravia-55-inch-4k-google-tv',
                'brand': 'Sony',
                'model_number': 'KD-55X74L',
                'price': Decimal('59990.00'),
                'mrp': Decimal('79990.00'),
                'stock': 9,
                'is_featured': True,
                'is_deal': True,
                'deal_tag': 'Entertainment Special',
                'warranty_info': 'Sony 1-Year Warranty + 1-Year Additional on Panel',
                'rating': Decimal('4.7'),
                'reviews_count': 64,
                'image_url': 'https://images.unsplash.com/photo-1593784991095-a205069470b6?auto=format&fit=crop&w=600&q=80',
                'specs': '4K HDR Processor X1 for lifelike color and contrast\nGoogle TV with Google Assistant voice control\nDolby Audio with open baffle 20W speakers\nMotionflow XR 200 ensures blur-free sports and movies\nALLM (Auto Low Latency Mode) for PlayStation 5 gaming',
                'description': 'Experience movies, sports, and games in rich 4K clarity. Sony Bravia combines real-world colors with smart Google TV streaming.'
            },
            {
                'category': categories_map['smartwatches-wearables'],
                'name': 'Apple Watch Series 10 GPS 46mm (Jet Black Aluminum with Sport Band)',
                'slug': 'apple-watch-series-10-jet-black',
                'brand': 'Apple',
                'model_number': 'MWUG3HN/A',
                'price': Decimal('46900.00'),
                'mrp': Decimal('49900.00'),
                'stock': 15,
                'is_featured': True,
                'is_deal': False,
                'deal_tag': '',
                'warranty_info': 'Apple Official 1-Year Warranty',
                'rating': Decimal('4.8'),
                'reviews_count': 32,
                'image_url': 'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=600&q=80',
                'specs': 'Thinnest Apple Watch ever with the biggest display yet\nAdvanced health insights including Sleep Apnea notifications\nFast charging up to 80% in about 30 minutes\nWater resistant 50m with Depth and Water Temperature sensors\nPrecision ECG and Blood Oxygen sensor suite',
                'description': 'Apple Watch Series 10 is a major milestone. Featuring our biggest, most advanced display yet, showing more information on screen than ever.'
            }
        ]

        for p_data in products_data:
            p_data['seller'] = seller_user
            Product.objects.update_or_create(
                slug=p_data['slug'],
                defaults=p_data
            )
        self.stdout.write(self.style.SUCCESS(f"✓ {len(products_data)} products seeded."))

        # 5. Addresses for Rahul
        addr1, _ = Address.objects.get_or_create(
            user=customer_user,
            full_name='Rahul Sharma',
            address_line1='Flat 402 Sea Green, Off Veer Savarkar Marg',
            city='Mumbai',
            defaults={
                'phone': '+91 98201 44829',
                'address_line2': 'Prabhadevi',
                'landmark': 'Near Siddhivinayak Temple',
                'state': 'Maharashtra',
                'pincode': '400025',
                'address_type': Address.TYPE_HOME,
                'is_default': True,
            }
        )

        addr2, _ = Address.objects.get_or_create(
            user=customer_user,
            full_name='Rahul Sharma (Office)',
            address_line1='Level 7, Maker Maxity, Bandra Kurla Complex',
            city='Mumbai',
            defaults={
                'phone': '+91 98201 44829',
                'address_line2': 'Bandra East',
                'landmark': 'Next to MCA Club',
                'state': 'Maharashtra',
                'pincode': '400051',
                'address_type': Address.TYPE_OFFICE,
                'is_default': False,
            }
        )
        self.stdout.write(self.style.SUCCESS("✓ Saved delivery addresses seeded."))

        # 6. Orders for Rahul (Matching code.html design)
        macbook = Product.objects.get(slug='apple-macbook-air-m3-midnight')
        sony_headphone = Product.objects.get(slug='sony-wh-1000xm5-silver')
        bumper_case = Product.objects.get(slug='oneplus-12-protective-bumper-case-emerald')
        mouse = Product.objects.get(slug='logitech-mx-master-3s-graphite')

        # Order 1: Active In-Transit Spotlight Order (#TM-2025-89412)
        ord1, ord1_created = Order.objects.get_or_create(
            order_number='TM-2025-89412',
            defaults={
                'user': customer_user,
                'shipping_name': 'Rahul Sharma',
                'shipping_phone': '+91 98201 44829',
                'shipping_address_line1': addr1.address_line1,
                'shipping_address_line2': addr1.address_line2,
                'shipping_landmark': addr1.landmark,
                'shipping_city': addr1.city,
                'shipping_state': addr1.state,
                'shipping_pincode': addr1.pincode,
                'subtotal': Decimal('141890.00'),
                'delivery_charge': Decimal('0.00'),
                'gst_amount': Decimal('21644.24'),
                'total_amount': Decimal('141890.00'),
                'payment_method': Order.PAY_UPI,
                'payment_status': Order.PAY_STATUS_PAID,
                'order_status': Order.STATUS_IN_TRANSIT,
                'delivery_pin': '4819',
                'courier_name': 'Bluedart Air Express',
                'tracking_number': '8491023910',
                'estimated_delivery_text': 'Tomorrow by 2:00 PM',
                'current_location': 'Worli Local Hub (3:20 PM)',
            }
        )
        if ord1_created:
            OrderItem.objects.create(
                order=ord1,
                product=macbook,
                product_name=macbook.name,
                brand=macbook.brand,
                model_number=macbook.model_number,
                warranty_info=macbook.warranty_info,
                image_url=macbook.display_image,
                price=macbook.price,
                mrp=macbook.mrp,
                quantity=1,
                line_total=macbook.price
            )
            OrderItem.objects.create(
                order=ord1,
                product=sony_headphone,
                product_name=sony_headphone.name,
                brand=sony_headphone.brand,
                model_number=sony_headphone.model_number,
                warranty_info=sony_headphone.warranty_info,
                image_url=sony_headphone.display_image,
                price=sony_headphone.price,
                mrp=sony_headphone.mrp,
                quantity=1,
                line_total=sony_headphone.price
            )

        # Order 2: Active Dispatched Order (#TM-2025-87102)
        ord2, ord2_created = Order.objects.get_or_create(
            order_number='TM-2025-87102',
            defaults={
                'user': customer_user,
                'shipping_name': 'Rahul Sharma',
                'shipping_phone': '+91 98201 44829',
                'shipping_address_line1': addr1.address_line1,
                'shipping_city': addr1.city,
                'shipping_state': addr1.state,
                'shipping_pincode': addr1.pincode,
                'subtotal': Decimal('1299.00'),
                'delivery_charge': Decimal('0.00'),
                'gst_amount': Decimal('198.15'),
                'total_amount': Decimal('1299.00'),
                'payment_method': Order.PAY_UPI,
                'payment_status': Order.PAY_STATUS_PAID,
                'order_status': Order.STATUS_PACKED,
                'delivery_pin': '7215',
                'courier_name': 'Ekart Logistics',
                'tracking_number': 'EK-772910',
                'estimated_delivery_text': 'Thursday by 4:00 PM',
                'current_location': 'Bhiwandi Central Fulfillment Hub',
            }
        )
        if ord2_created:
            OrderItem.objects.create(
                order=ord2,
                product=bumper_case,
                product_name=bumper_case.name,
                brand=bumper_case.brand,
                model_number=bumper_case.model_number,
                warranty_info=bumper_case.warranty_info,
                image_url=bumper_case.display_image,
                price=bumper_case.price,
                mrp=bumper_case.mrp,
                quantity=1,
                line_total=bumper_case.price
            )

        # Order 3: Past Delivered Order (#TM-2024-55198)
        ord3, ord3_created = Order.objects.get_or_create(
            order_number='TM-2024-55198',
            defaults={
                'user': customer_user,
                'shipping_name': 'Rahul Sharma',
                'shipping_phone': '+91 98201 44829',
                'shipping_address_line1': addr1.address_line1,
                'shipping_city': addr1.city,
                'shipping_state': addr1.state,
                'shipping_pincode': addr1.pincode,
                'subtotal': Decimal('8495.00'),
                'delivery_charge': Decimal('0.00'),
                'gst_amount': Decimal('1295.85'),
                'total_amount': Decimal('8495.00'),
                'payment_method': Order.PAY_CARD,
                'payment_status': Order.PAY_STATUS_PAID,
                'order_status': Order.STATUS_DELIVERED,
                'delivery_pin': '1092',
                'courier_name': 'Bluedart Express',
                'tracking_number': '8401923481',
                'estimated_delivery_text': 'Delivered on 18 Dec 2024',
                'current_location': 'Prabhadevi, Mumbai (Delivered)',
            }
        )
        if ord3_created:
            OrderItem.objects.create(
                order=ord3,
                product=mouse,
                product_name=mouse.name,
                brand=mouse.brand,
                model_number=mouse.model_number,
                warranty_info=mouse.warranty_info,
                image_url=mouse.display_image,
                price=mouse.price,
                mrp=mouse.mrp,
                quantity=1,
                line_total=mouse.price
            )

        self.stdout.write(self.style.SUCCESS("✓ Active & Past orders seeded matching reference design."))
        self.stdout.write(self.style.SUCCESS("All initial database seeding completed successfully!"))
