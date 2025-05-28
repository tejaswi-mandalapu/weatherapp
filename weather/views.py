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
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .utils import get_weather_by_coords  # Your weather API helper function
from .forms import CustomUserCreationForm, DualLoginForm
import logging

# Set up logging
logger = logging.getLogger(__name__)

def weather_by_coords(request):
    """API endpoint for fetching weather by coordinates"""
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if not lat or not lon:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)
    
    try:
        weather_data, forecast_data = get_weather_and_forecast_by_coords(lat, lon)
        if weather_data and 'error' in weather_data:
            return JsonResponse({'error': weather_data['error']}, status=400)
        # Combine current and forecast for JS
        response = dict(weather_data)
        response['forecast'] = []
        if forecast_data:
            for day in forecast_data:
                response['forecast'].append({
                    'date': day['date'],
                    'icon': day['icon'],
                    'temp': day['max_temp'],  # or avg_temp if you want
                    'description': day['condition'],
                    'temp_min': day['min_temp'],
                    'temp_max': day['max_temp'],
                })
        return JsonResponse(response)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def fetch_weather_news():
    """
    Fetch weather news from NewsAPI with caching
    Returns: List of articles or empty list if error occurs
    """
    cache_key = 'weather_news_articles'
    articles = cache.get(cache_key)
    if articles is not None:
        return articles

    try:
        # Use a more specific query for weather news
        url = (
            "https://newsapi.org/v2/everything?"
            "q=weather OR climate OR rainfall OR storm OR cyclone OR monsoon OR temperature "
            "AND (title:weather OR title:climate OR title:rain OR title:storm OR title:cyclone OR title:monsoon OR title:temperature)"
            "&language=en"
            "&sortBy=publishedAt"
            f"&apiKey={settings.NEWS_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Filter articles to only those with 'weather' in title or description
        articles = [
            article for article in data.get('articles', [])[:8]
            if 'weather' in (article.get('title', '').lower() + article.get('description', '').lower())
        ]
        cache.set(cache_key, articles, 3600)  # Cache for 1 hour
        return articles
    except requests.exceptions.RequestException as e:
        logger.error(f"News API request failed: {e}")
        return []
    except (ValueError, KeyError) as e:
        logger.error(f"Error parsing news data: {e}")
        return []

def index(request):
    """
    Main view for weather search and news display
    """
    weather_data = None
    news_articles = fetch_weather_news()
    
    if request.method == 'POST':
        city_name = request.POST.get('city', '').strip()
        if city_name:
            weather_data = get_weather_for_city(city_name)
            if 'error' in weather_data:
                messages.error(request, weather_data['error'])
                weather_data = None
    
    return render(request, 'index.html', {
        'weather_data': weather_data,
        'news_articles': news_articles
    })

def contact(request):
    """
    Handle contact form submissions with rate limiting
    """
    # Rate limiting check
    if request.method == 'POST':
        ip_address = request.META.get('REMOTE_ADDR')
        cache_key = f'contact_submission_{ip_address}'
        last_submission = cache.get(cache_key)
        
        if last_submission and (timezone.now() - last_submission) < timedelta(minutes=5):
            messages.error(request, 'Please wait 5 minutes before submitting another message.')
            return redirect('contact')
        
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not all([name, email, message]):
            messages.error(request, 'Please fill all fields.')
            return redirect('contact')
            
        try:
            send_mail(
                f'Contact Form Submission from {name}',
                f"From: {name} <{email}>\n\n{message}",
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            cache.set(cache_key, timezone.now(), 300)  # 5 minutes
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            messages.error(request, 'Failed to send your message. Please try again later.')
    
    return render(request, 'contact.html')

def signup(request):
    """
    Handle user registration with form validation
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
            
            # Optional: Send welcome email
            try:
                send_mail(
                    'Welcome to WeatherApp',
                    'Thank you for registering with WeatherApp!',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Welcome email failed: {e}")
            
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def user_login(request):
    """
    Handle user authentication with improved security
    """
    if request.user.is_authenticated:
        return redirect('userdashboard')
        
    if request.method == 'POST':
        form = DualLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Log login activity
            logger.info(f"User {user.username} logged in from {request.META.get('REMOTE_ADDR')}")
            messages.success(request, "Login successful!")
            
            next_url = request.GET.get('next', 'userdashboard')
            return redirect(next_url)
    else:
        form = DualLoginForm()
        
    return render(request, 'registration/login.html', {'form': form})

def about(request):
    """About page view with team information"""
    team_members = [
        {'name': 'John Doe', 'role': 'Founder'},
        {'name': 'Jane Smith', 'role': 'Developer'},
    ]
    return render(request, 'about.html', {'team_members': team_members})

def donate(request):
    """Donation page view with payment options"""
    return render(request, 'donate.html')

@login_required
def userdashboard(request):
    """
    User dashboard with weather, forecast, and news
    """
    weather_data = None
    forecast_data = None
    news_articles = fetch_weather_news()
    
    if request.method == "POST":
        use_location = request.POST.get("use_location")
        try:
            if use_location:
                lat = request.POST.get("lat")
                lon = request.POST.get("lon")
                if lat and lon:
                    weather_data, forecast_data = get_weather_and_forecast_by_coords(lat, lon)
            else:
                city = request.POST.get("city")
                if city:
                    weather_data, forecast_data = get_weather_and_forecast_by_city(city)
                    
            if weather_data and 'error' in weather_data:
                messages.error(request, weather_data['error'])
                weather_data = None
                
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            messages.error(request, "An error occurred while fetching weather data.")
    
    return render(request, "userdashboard.html", {
        "weather_data": weather_data,
        "forecast_data": forecast_data,
        "news_articles": news_articles,
    })

def get_weather_for_city(city_name):
    """
    Get current weather for a city with improved error handling
    """
    try:
        weather_url = f"http://api.weatherapi.com/v1/current.json?key={settings.WEATHER_API_KEY}&q={city_name}"
        response = requests.get(weather_url, timeout=10)
        response.raise_for_status()
        weather_json = response.json()
        
        return {
            'city': city_name,
            'temperature': weather_json['current']['temp_c'],
            'description': weather_json['current']['condition']['text'],
            'icon': weather_json['current']['condition']['icon'],
            'humidity': weather_json['current']['humidity'],
            'wind_speed': weather_json['current']['wind_kph'],
            'feels_like': weather_json['current']['feelslike_c'],
            'last_updated': weather_json['current']['last_updated']
        }
    except requests.exceptions.Timeout:
        return {'error': 'Request timed out. Please try again.'}
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather API request failed for {city_name}: {e}")
        return {'error': f"Could not fetch weather for {city_name}. Please try again."}
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing weather data for {city_name}: {e}")
        return {'error': "Invalid weather data received. Please try another city."}

def get_weather_and_forecast_by_coords(lat, lon):
    """
    Get weather and forecast by coordinates with better error handling
    """
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={settings.WEATHER_API_KEY}&q={lat},{lon}&days=5&aqi=no&alerts=no"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data['current']
        location = data['location']
        forecast_days = data['forecast']['forecastday']

        weather_data = {
            'city': f"{location['name']}, {location['country']}",
            'temperature': current['temp_c'],
            'description': current['condition']['text'],
            'icon': current['condition']['icon'],
            'humidity': current['humidity'],
            'wind_speed': current['wind_kph'],
            'feels_like': current['feelslike_c'],
            'visibility': current.get('vis_km', ''), 
            'last_updated': current['last_updated']
        }
        
        forecast_data = []
        for day in forecast_days:
            forecast_data.append({
                'date': day['date'],
                'min_temp': day['day']['mintemp_c'],
                'max_temp': day['day']['maxtemp_c'],
                'condition': day['day']['condition']['text'],
                'icon': day['day']['condition']['icon'],
                'sunrise': day['astro']['sunrise'],
                'sunset': day['astro']['sunset']
            })
            
        return weather_data, forecast_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Forecast API request failed for coords {lat},{lon}: {e}")
        return {'error': "Weather service unavailable. Please try again later."}, None
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing forecast data: {e}")
        return {'error': "Invalid weather data received."}, None

def get_weather_and_forecast_by_city(city_name):
    """
    Get weather and forecast by city name with better error handling
    """
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={settings.WEATHER_API_KEY}&q={city_name}&days=5&aqi=no&alerts=no"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        current = data['current']
        location = data['location']
        forecast_days = data['forecast']['forecastday']

        weather_data = {
            'city': f"{location['name']}, {location['country']}",
            'temperature': current['temp_c'],
            'description': current['condition']['text'],
            'icon': current['condition']['icon'],
            'humidity': current['humidity'],
            'wind_speed': current['wind_kph'],
            'feels_like': current['feelslike_c'],
            'visibility': current.get('vis_km', ''), 
            'last_updated': current['last_updated']
        }
        
        forecast_data = []
        for day in forecast_days:
            forecast_data.append({
                'date': day['date'],
                'min_temp': day['day']['mintemp_c'],
                'max_temp': day['day']['maxtemp_c'],
                'condition': day['day']['condition']['text'],
                'icon': day['day']['condition']['icon'],
                'sunrise': day['astro']['sunrise'],
                'sunset': day['astro']['sunset']
            })
            
        return weather_data, forecast_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Forecast API request failed for {city_name}: {e}")
        return {'error': f"Could not fetch weather for {city_name}. Please try again."}, None
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing forecast data for {city_name}: {e}")
        return {'error': "Invalid weather data received."}, None

@require_GET
def weather_by_city(request):
    city = request.GET.get('city')
    if not city:
        return JsonResponse({'error': 'Missing city'}, status=400)
    weather_data, forecast_data = get_weather_and_forecast_by_city(city)
    if weather_data and 'error' in weather_data:
        return JsonResponse({'error': weather_data['error']}, status=400)
    response = dict(weather_data)
    response['forecast'] = []
    if forecast_data:
        for day in forecast_data:
            response['forecast'].append({
                'date': day['date'],
                'icon': day['icon'],
                'temp': day['max_temp'],
                'description': day['condition'],
                'temp_min': day['min_temp'],
                'temp_max': day['max_temp'],
            })
    return JsonResponse(response)