from django.contrib.auth import get_user_model
from django.db.models import Q
from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ImproperlyConfigured

class EmailOrPhoneBackend(BaseBackend):
    """
    Custom authentication backend that allows login with either email or phone number
    """
    
    def authenticate(self, request, identifier=None, password=None, **kwargs):
        try:
            User = get_user_model()
            
            # Properly closed parentheses
            user = User.objects.get(
                Q(email=identifier) | 
                Q(phone=identifier)
            )
            
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            return None
        except Exception as e:
            raise ImproperlyConfigured(f"Authentication error: {str(e)}")

    def get_user(self, user_id):
        try:
            User = get_user_model()
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None