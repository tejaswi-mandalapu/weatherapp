from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

def fetch_weather_news():
    """
    Fetch weather news from NewsAPI
    Returns: List of articles or empty list if error occurs
    """
    from django.core.cache import cache
    API_KEY = settings.NEWS_API_KEY  # Store your key in settings.py
    cache_key = 'weather_news_articles'
    articles = cache.get(cache_key)
    if articles is not None:
        return articles

    url = f"https://newsapi.org/v2/everything?q=weather&language=en&sortBy=publishedAt&apiKey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        articles = data.get('articles', [])[:4]
        cache.set(cache_key, articles, 3600)  # Cache for 1 hour
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather news: {e}")
        return []
    except ValueError as e:
        print(f"Error parsing JSON response: {e}")
        return []

def index(request):
    """
    Main view for weather search and news display
    """
    weather_data = None
    news_articles = []
    
    # Only fetch news if not already in context (could be cached)
    if 'news_articles' not in request.GET:
        news_articles = fetch_weather_news()
    
    if request.method == 'POST':
        city_name = request.POST.get('city', '').strip()
        if city_name:
            try:
                # Fetch weather data
                weather_url = f"http://api.weatherapi.com/v1/current.json?key={settings.WEATHER_API_KEY}&q={city_name}"
                response = requests.get(weather_url)
                response.raise_for_status()
                weather_json = response.json()
                
                weather_data = {
                    'city': city_name,
                    'temperature': weather_json['current']['temp_c'],
                    'description': weather_json['current']['condition']['text'],
                    'icon': weather_json['current']['condition']['icon'],
                    'humidity': weather_json['current']['humidity'],
                    'wind_speed': weather_json['current']['wind_kph'],
                    'feels_like': weather_json['current']['feelslike_c']
                }
                
            except requests.exceptions.RequestException as e:
                print(f"Weather API request failed: {e}")
                messages.error(request, f"Could not fetch weather for {city_name}. Please try again.")
            except (KeyError, ValueError) as e:
                print(f"Error parsing weather data: {e}")
                messages.error(request, "Invalid weather data received. Please try another city.")
    
    return render(request, 'index.html', {
        'weather_data': weather_data,
        'news_articles': news_articles
    })

def contact(request):
    """
    Handle contact form submissions
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        if name and email and message:
            try:
                send_mail(
                    f'Contact Form Submission from {name}',
                    message,
                    email,
                    [settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, 'Your message has been sent successfully!')
                return redirect('contact')
            except Exception as e:
                print(f"Error sending email: {e}")
                messages.error(request, 'Failed to send your message. Please try again later.')
        else:
            messages.error(request, 'Please fill all fields.')
    
    return render(request, 'contact.html')

def signup(request):
    """
    Handle user registration
    """
    from .forms import CustomUserCreationForm
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Save user to database
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')  # Redirect to login page
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {
        'form': form,
        'title': 'Register'
    })

def user_login(request):
    """
    Handle user authentication (email or phone)
    """
    from .forms import DualLoginForm
    if request.method == 'POST':
        form = DualLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('userdashboard')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
    else:
        form = DualLoginForm()
    return render(request, 'registration/login.html', {'form': form, 'title': 'Login'})

def about(request):
    """About page view"""
    return render(request, 'about.html')

def donate(request):
    """Donation page view"""
    return render(request, 'donate.html')

@login_required
def userdashboard(request):
    """
    User dashboard view with weather search functionality
    """
    weather_data = None
    news_articles = fetch_weather_news()
    
    if request.method == 'POST':
        city_name = request.POST.get('city', '').strip()
        if city_name:
            try:
                # Fetch weather data
                weather_url = f"http://api.weatherapi.com/v1/current.json?key={settings.WEATHER_API_KEY}&q={city_name}"
                response = requests.get(weather_url)
                response.raise_for_status()
                weather_json = response.json()
                
                weather_data = {
                    'city': city_name,
                    'temperature': weather_json['current']['temp_c'],
                    'description': weather_json['current']['condition']['text'],
                    'icon': weather_json['current']['condition']['icon'],
                    'humidity': weather_json['current']['humidity'],
                    'wind_speed': weather_json['current']['wind_kph'],
                    'feels_like': weather_json['current']['feelslike_c']
                }
                
            except requests.exceptions.RequestException as e:
                print(f"Weather API request failed: {e}")
                messages.error(request, f"Could not fetch weather for {city_name}. Please try again.")
            except (KeyError, ValueError) as e:
                print(f"Error parsing weather data: {e}")
                messages.error(request, "Invalid weather data received. Please try another city.")
    
    return render(request, 'userdashboard.html', {
        'weather_data': weather_data,
        'news_articles': news_articles
    })