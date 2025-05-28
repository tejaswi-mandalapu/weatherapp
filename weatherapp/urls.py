from django.urls import path, include
from django.contrib.auth import views as auth_views
from weather import views as weather_views
from weather.views import user_login, index

urlpatterns = [
    # Direct login/signup URLs (without accounts/ prefix)
    path('login/', user_login, name='login'),
    path('signup/', weather_views.signup, name='signup'),
    path('', weather_views.index, name='index'),
    path('about/', weather_views.about, name='about'),
    path('contact/', weather_views.contact, name='contact'),
    path('donate/', weather_views.donate, name='donate'),
    path('dashboard/', weather_views.userdashboard, name='userdashboard'),

    # Accounts URLs (for other auth features)
    path('accounts/', include([
        path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
        # Password Reset URLs
        path('password-reset/', auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset.html'
        ), name='password_reset'),
        path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ), name='password_reset_done'),
        path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ), name='password_reset_confirm'),
        path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ), name='password_reset_complete'),
    ])),

    # Main App URLs
    path('', include('weather.urls')),
]