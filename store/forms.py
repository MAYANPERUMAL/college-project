import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Product, Category, Address, Order, PaymentSetting

User = get_user_model()


class CustomerRegisterForm(UserCreationForm):
    ROLE_CHOICES = [
        (User.ROLE_CUSTOMER, 'Customer'),
        (User.ROLE_SELLER, 'Seller'),
    ]

    account_type = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial=User.ROLE_CUSTOMER,
        required=False,
        widget=forms.HiddenInput()
    )
    store_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'e.g. Apex Digital Electronics Store'
        }),
        help_text="Required if registering as a Seller."
    )
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Last Name'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Email Address'
    }))
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': '10-digit Mobile Number (e.g. 9876543210)'
    }), help_text="A 6-digit OTP will be sent to verify your mobile number.")
    gst_number = forms.CharField(max_length=25, required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Optional GSTIN (e.g. 27AAACH8291Q1ZT)'
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('account_type', 'store_name', 'username', 'first_name', 'last_name', 'email', 'phone', 'gst_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if 'class' not in field.widget.attrs and not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs['class'] = 'form-control'
        if 'password1' in self.fields:
            self.fields['password1'].help_text = ''
        if 'password2' in self.fields:
            self.fields['password2'].help_text = ''
            self.fields['password2'].required = False

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if not p2 and p1:
            return p1
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match. Please enter the same password in both fields.")
        return p2 or p1

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone', '')
        digits = re.sub(r'\D', '', str(raw_phone))
        if len(digits) > 10 and (digits.startswith('91') or digits.startswith('0')):
            digits = digits[-10:]
        if len(digits) != 10:
            raise forms.ValidationError("Please enter a valid 10-digit mobile number.")
        if User.objects.filter(phone=digits).exists():
            raise forms.ValidationError("This mobile number is already registered. Please sign in or use another number.")
        return digits

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered. Please sign in or use another email.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data.get('account_type') or User.ROLE_CUSTOMER
        if user.role == User.ROLE_SELLER:
            user.store_name = self.cleaned_data.get('store_name') or f"{user.first_name or user.username}'s Store"
        user.first_name = self.cleaned_data.get('first_name', '').strip()
        user.last_name = self.cleaned_data.get('last_name', '').strip()
        user.email = self.cleaned_data.get('email', '').strip().lower()
        user.phone = self.cleaned_data.get('phone', '').strip()
        user.is_verified = True
        if commit:
            user.save()
        return user


class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username or Email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password'
    }))


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center fw-bold fs-2 letter-spacing-lg',
            'placeholder': '• • • • • •',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'autofocus': 'autofocus',
            'style': 'letter-spacing: 0.5rem;'
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp', '').strip()
        if not otp.isdigit() or len(otp) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit numeric OTP.")
        return otp


class OTPLoginForm(forms.Form):
    identifier = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Registered Mobile Number or Email'
        }),
        help_text="We will send a 6-digit OTP code to verify your identity."
    )



class ProductForm(forms.ModelForm):
    seller = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.ROLE_SELLER),
        required=False,
        empty_label="TechMart Retail (Direct Store Inventory)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    warranty_info = forms.CharField(
        max_length=150,
        required=False,
        initial="Official 1-Year Pan-India Warranty",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-Year Official Brand Warranty'})
    )

    def clean_warranty_info(self):
        val = (self.cleaned_data.get('warranty_info') or '').strip()
        return val or "Official 1-Year Pan-India Warranty"

    class Meta:
        model = Product
        fields = [
            'seller', 'category', 'brand', 'name', 'model_number', 'price', 'mrp',
            'stock', 'specs', 'description', 'image', 'image_url',
            'warranty_info', 'is_featured', 'is_deal', 'deal_tag'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apple, Sony, Samsung'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Product Name'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MRXN3HN/A'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Selling Price in ₹'}),
            'mrp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'MRP in ₹'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Available Stock Units'}),
            'specs': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Bullet points / key technical specifications (one per line)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Detailed product description and warranty terms'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'warranty_info': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-Year Official Brand Warranty'}),
            'deal_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Republic Day Fest Deal'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_deal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'icon_name', 'description', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'icon_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material symbol icon name (e.g. devices, laptop, headphones)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'full_name', 'phone', 'address_line1', 'address_line2',
            'landmark', 'city', 'state', 'pincode', 'address_type', 'is_default'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit mobile number'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat, House no., Building, Company'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area, Colony, Street, Sector'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nearby Landmark (optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City / District'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN code', 'maxlength': '6'}),
            'address_type': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_status', 'payment_status', 'courier_name', 'tracking_number', 'estimated_delivery_text', 'current_location']
        widgets = {
            'order_status': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'courier_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'estimated_delivery_text': forms.TextInput(attrs={'class': 'form-control'}),
            'current_location': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PaymentSettingForm(forms.ModelForm):
    class Meta:
        model = PaymentSetting
        fields = [
            'upi_id', 'merchant_name', 'qr_image', 'upi_note',
            'enable_upi', 'enable_card', 'enable_netbanking', 'enable_cod',
            'cod_max_limit',
            'bank_name', 'account_number', 'ifsc_code', 'account_holder_name'
        ]
        widgets = {
            'upi_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. mayanperumal123@oksbi'}),
            'merchant_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tech Mart'}),
            'qr_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'upi_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tech Mart Order'}),
            'enable_upi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_card': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_netbanking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_cod': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cod_max_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '100'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. State Bank of India'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 30981273918'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SBIN0001234'}),
            'account_holder_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TechMart Electronics Pvt Ltd'}),
        }


class SellerProductForm(forms.ModelForm):
    warranty_info = forms.CharField(
        max_length=150,
        required=False,
        initial="Official 1-Year Pan-India Warranty",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-Year Official Brand Warranty'})
    )

    def clean_warranty_info(self):
        val = (self.cleaned_data.get('warranty_info') or '').strip()
        return val or "Official 1-Year Pan-India Warranty"

    class Meta:
        model = Product
        fields = [
            'category', 'brand', 'name', 'model_number', 'price', 'mrp',
            'stock', 'specs', 'description', 'image', 'image_url',
            'warranty_info', 'is_featured', 'is_deal', 'deal_tag', 'is_active'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Apple, Sony, Samsung'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Product Name'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MRXN3HN/A'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Selling Price in ₹', 'min': '0'}),
            'mrp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'MRP in ₹', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Available Stock Units', 'min': '0'}),
            'specs': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Bullet points / key technical specifications (one per line)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Detailed product description and warranty terms'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'warranty_info': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1-Year Official Brand Warranty'}),
            'deal_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Special Fest Deal'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_deal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'theme_preference', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}),
            'theme_preference': forms.Select(attrs={'class': 'form-select theme-preference-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ProfilePasswordChangeForm(forms.Form):
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'}),
        required=True,
        label="Current Password"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'}),
        required=True,
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'}),
        required=True,
        label="Confirm New Password"
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        curr = cleaned_data.get('current_password')
        new = cleaned_data.get('new_password')
        conf = cleaned_data.get('confirm_password')
        if curr and not self.user.check_password(curr):
            self.add_error('current_password', 'Current password is incorrect.')
        if new and conf and new != conf:
            self.add_error('confirm_password', 'New passwords do not match.')
        return cleaned_data


class SellerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['store_name', 'seller_bio', 'first_name', 'last_name', 'email', 'phone', 'gst_number', 'theme_preference', 'profile_image']
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Alpha Electronics Store'}),
            'seller_bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief store overview, dispatch policy, or seller description'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Store Business Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Registered Mobile Number'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GSTIN Number (e.g. 27AAACH8291Q1ZT)'}),
            'theme_preference': forms.Select(attrs={'class': 'form-select theme-preference-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class DeliveryPartnerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'vehicle_type', 'vehicle_number', 'current_city', 'is_available', 'theme_preference', 'profile_image']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Motorcycle, Scooter, Electric EV, Van'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TN-38-BH-9821'}),
            'current_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Coimbatore'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'theme_preference': forms.Select(attrs={'class': 'form-select theme-preference-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AdminAssignPartnerForm(forms.Form):
    delivery_partner = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.ROLE_DELIVERY, is_active=True),
        required=True,
        empty_label="-- Select Available Delivery Partner --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    delivery_notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional delivery instruction for partner'})
    )
