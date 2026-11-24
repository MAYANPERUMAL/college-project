from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.conf import settings
import re


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using either their:
    - Username (case-insensitive)
    - Email address (case-insensitive)
    - Registered 10-digit mobile number
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or not password:
            return None

        clean_username = str(username).strip()
        clean_password = str(password).strip()

        # Clean potential mobile digits
        digits = re.sub(r'\D', '', clean_username)
        if len(digits) > 10 and (digits.startswith('91') or digits.startswith('0')):
            digits = digits[-10:]

        user = UserModel.objects.filter(
            Q(username__iexact=clean_username) | Q(email__iexact=clean_username) | Q(phone=clean_username)
        ).first()

        # If not found directly and looks like a 10-digit mobile number, check formatted phones
        if not user and len(digits) == 10:
            user = UserModel.objects.filter(
                Q(phone__endswith=digits) | Q(phone__icontains=digits)
            ).first()
            if not user:
                for candidate in UserModel.objects.exclude(phone__isnull=True).exclude(phone=''):
                    cand_digits = re.sub(r'\D', '', str(candidate.phone))
                    if cand_digits.endswith(digits):
                        user = candidate
                        break

        # If not found directly, check name variants (e.g. "MAYAN PERUMAL" or "mayan_perumal")
        if not user:
            no_spaces = clean_username.replace(' ', '')
            with_underscore = clean_username.replace(' ', '_')
            user = UserModel.objects.filter(
                Q(username__iexact=no_spaces) |
                Q(username__iexact=with_underscore) |
                Q(first_name__iexact=clean_username) |
                Q(last_name__iexact=clean_username) |
                Q(store_name__iexact=clean_username)
            ).first()

            if not user and len(clean_username.split()) >= 2:
                parts = clean_username.split(None, 1)
                user = UserModel.objects.filter(
                    first_name__iexact=parts[0],
                    last_name__iexact=parts[1]
                ).first()

        if not user:
            return None

        # Standard hashed password check
        if user.check_password(password) or user.check_password(clean_password):
            if self.user_can_authenticate(user):
                return user

        # In DEBUG mode: support standard test passwords (customer123, mmm, admin123)
        if settings.DEBUG and self.user_can_authenticate(user):
            valid_role_pwds = {
                'CUSTOMER': {'customer123', 'mmm'},
                'ADMIN': {'admin123', 'mmm', 'admin'},
                'SELLER': {'seller123', 'admin123'},
                'DELIVERY': {'delivery123', 'admin123'},
            }
            allowed = valid_role_pwds.get(user.role, set())
            if clean_password in allowed or clean_password.lower() in allowed:
                user.set_password(clean_password)
                user.save(update_fields=['password'])
                return user

        return None
