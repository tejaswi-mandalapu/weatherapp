from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import City, CustomUser, WeatherBlog, RecentSearch
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

class CityForm(forms.ModelForm):
    class Meta:
        model = City
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter city name',
                'class': 'form-control',
                'autocomplete': 'off'
            })
        }
        labels = {
            'name': 'City Name'
        }

class CustomUserCreationForm(UserCreationForm):
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'given-name'})
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'family-name'})
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    
    location = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'address-level2'})
    )
    
    dob = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'autocomplete': 'bday'
        })
    )
    
    phone_number = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        widget=forms.TextInput(attrs={
            'placeholder': '+1234567890',
            'autocomplete': 'tel'
        })
    )
    
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text="Minimum 8 characters with at least one number."
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'location', 'dob', 'phone_number', 'password1', 'password2')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
        
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if CustomUser.objects.filter(phone=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone = self.cleaned_data['phone_number']
        user.location = self.cleaned_data['location']
        user.dob = self.cleaned_data['dob']
        # Generate a unique username from email or phone
        base_username = self.cleaned_data['email'].split('@')[0]
        username = base_username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        if commit:
            user.save()
        return user

User = get_user_model()

class DualLoginForm(forms.Form):
    email = forms.EmailField(required=False)
    phone = forms.CharField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        password = cleaned_data.get('password')

        if not email and not phone:
            raise forms.ValidationError("Please enter either email or phone number.")

        from django.contrib.auth import authenticate
        user = None

        if email:
            user = authenticate(username=email, password=password)
            if not user:
                # Try to get user by email field
                from .models import CustomUser
                try:
                    user_obj = CustomUser.objects.get(email=email)
                    user = authenticate(username=user_obj.username, password=password)
                except CustomUser.DoesNotExist:
                    pass
        elif phone:
            from .models import CustomUser
            try:
                user_obj = CustomUser.objects.get(phone=phone)
                user = authenticate(username=user_obj.username, password=password)
            except CustomUser.DoesNotExist:
                user = None

        if not user:
            raise forms.ValidationError("Invalid login credentials.")

        self.user_cache = user
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)

class WeatherBlogForm(forms.ModelForm):
    class Meta:
        model = WeatherBlog
        fields = ['title', 'content', 'source', 'published_date', 'weather_reference', 'image_url']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter blog title',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Enter blog content',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'source': forms.TextInput(attrs={
                'placeholder': 'Enter source (optional)',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'published_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'weather_reference': forms.TextInput(attrs={
                'placeholder': 'Enter weather reference (optional)',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'image_url': forms.URLInput(attrs={
                'placeholder': 'Enter image URL (optional)',
                'class': 'form-control',
                'autocomplete': 'off'
            })
        }
        labels = {
            'title': 'Blog Title',
            'content': 'Content',
            'source': 'Source',
            'published_date': 'Published Date',
            'weather_reference': 'Weather Reference',
            'image_url': 'Image URL'
        }

class RecentSearchForm(forms.ModelForm):
    class Meta:
        model = RecentSearch
        fields = ['city', 'temperature', 'description']  # Removed 'timestamp'
        widgets = {
            'city': forms.TextInput(attrs={
                'placeholder': 'Enter city name',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'temperature': forms.NumberInput(attrs={
                'placeholder': 'Enter temperature',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            'description': forms.TextInput(attrs={
                'placeholder': 'Enter weather description',
                'class': 'form-control',
                'autocomplete': 'off'
            }),
            # 'timestamp' widget removed
        }
        labels = {
            'city': 'City',
            'temperature': 'Temperature',
            'description': 'Description',
            # 'timestamp': 'Timestamp'  # Remove this line
        }

