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
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
import logging

logger = logging.getLogger(__name__)

def fetch_weather_news(location=None):
    cache_key = f'weather_news_articles_{location or "global"}'
    articles = cache.get(cache_key)
    if articles is not None:
        return articles

    all_articles = []
    keywords = ['weather', 'rain', 'storm', 'climate', 'temperature', 'forecast', 'monsoon', 'cyclone']

    # Build query
    query = f"weather AND ({' OR '.join(keywords)})"
    if location:
        query += f" AND {location}"

    # Fetch latest headlines
    try:
        url_headlines = (
            "https://newsapi.org/v2/top-headlines?"
            f"q={query}&"
            "language=en&"
            f"apiKey={settings.NEWS_API_KEY}"
        )
        response_headlines = requests.get(url_headlines, timeout=10)
        response_headlines.raise_for_status()
        data_headlines = response_headlines.json()
        headlines = [
            a for a in data_headlines.get('articles', [])[:5]
            if any(k in (str(a.get('title') or '').lower() + str(a.get('description') or '').lower()) for k in keywords)
        ]
        all_articles.extend(headlines)
    except Exception as e:
        logger.error(f"News API headlines request failed: {e}")

    # Fetch older news
    try:
        url_old = (
            "https://newsapi.org/v2/everything?"
            f"q={query}&"
            "language=en&"
            "sortBy=publishedAt&"
            "pageSize=10&"
            f"apiKey={settings.NEWS_API_KEY}"
        )
        response_old = requests.get(url_old, timeout=10)
        response_old.raise_for_status()
        data_old = response_old.json()
        old_news = [
            a for a in data_old.get('articles', [])[:10]
            if any(k in (str(a.get('title') or '').lower() + str(a.get('description') or '').lower()) for k in keywords)
        ]
        # Remove duplicates by URL
        seen_urls = set(a['url'] for a in all_articles)
        for article in old_news:
            if article['url'] not in seen_urls:
                all_articles.append(article)
    except Exception as e:
        logger.error(f"News API old news request failed: {e}")

    cache.set(cache_key, all_articles, 3600)
    return all_articles

def index(request):
    if request.user.is_authenticated:
        return redirect('userdashboard')
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
            cache.set(cache_key, timezone.now(), 300)
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            messages.error(request, 'Failed to send your message. Please try again later.')
    return render(request, 'contact.html')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! Please log in.')
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
    if request.user.is_authenticated:
        return redirect('userdashboard')
    if request.method == 'POST':
        form = DualLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            messages.success(request, "Login successful!")
            return redirect('userdashboard')
        else:
            messages.error(request, "Invalid credentials. Please try again.")

            logger.info(f"User {user.username} logged in from {request.META.get('REMOTE_ADDR')}")
            messages.success(request, "Login successful!")
            next_url = request.GET.get('next', 'userdashboard')
            return redirect(next_url)

    else:
        form = DualLoginForm()
    return render(request, 'registration/login.html', {'form': form})

def about(request):
    team_members = [
        {'name': 'John Doe', 'role': 'Founder'},
        {'name': 'Jane Smith', 'role': 'Developer'},
    ]
    return render(request, 'about.html', {'team_members': team_members})

def donate(request):
    return render(request, 'donate.html')

@login_required
def userdashboard(request):
    weather_data = None
    forecast_data = None
    location = None

    # Try to get location from POST (if user searched or used geolocation)
    if request.method == "POST":
        use_location = request.POST.get("use_location")
        try:
            if use_location:
                lat = request.POST.get("lat")
                lon = request.POST.get("lon")
                if lat and lon:
                    weather_data, forecast_data = get_weather_and_forecast_by_coords(lat, lon)
                    # Use city or country from weather_data for news
                    location = weather_data.get('city') if weather_data else None
            else:
                city = request.POST.get("city")
                if city:
                    weather_data, forecast_data = get_weather_and_forecast_by_city(city)
                    location = city
            if weather_data and 'error' in weather_data:
                messages.error(request, weather_data['error'])
                weather_data = None
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            messages.error(request, "An error occurred while fetching weather data.")
    else:
        # Optionally, use user's profile location or a default
        location = None

    news_articles = fetch_weather_news(location)
    return render(request, "userdashboard.html", {
        "weather_data": weather_data,
        "forecast_data": forecast_data,
        "news_articles": news_articles,
    })

def my_profile(request):
    return render(request, 'myprofile.html')

def get_weather_for_city(city_name):
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
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={settings.WEATHER_API_KEY}&q={lat},{lon}&days=5&aqi=no&alerts=no"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data['current']
        location = data['location']
        forecast_days = data['forecast']['forecastday']
        print("Forecast days returned (coords):", len(forecast_days))  # <-- Add this line
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
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={settings.WEATHER_API_KEY}&q={city_name}&days=5&aqi=no&alerts=no"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data['current']
        location = data['location']
        forecast_days = data['forecast']['forecastday']
        print("Forecast days returned (city):", len(forecast_days))  # <-- Add this line
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
def weather_by_coords(request):
    lat = request.GET.get('lat')
    
    lon = request.GET.get('lon')
    if not lat or not lon:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)
    try:
        weather_data, forecast_data = get_weather_and_forecast_by_coords(lat, lon)
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
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

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



class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('my_profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Password successfully changed!")
        return response

