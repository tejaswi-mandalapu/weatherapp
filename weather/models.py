from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = 'Custom User'
        verbose_name_plural = 'Custom Users'

class City(models.Model):
    name = models.CharField(max_length=100)
    # add other fields as needed

    def __str__(self):
        return self.name

class WeatherBlog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    source = models.CharField(max_length=100, blank=True)
    published_date = models.DateTimeField()
    weather_reference = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)

    def __str__(self):
        return self.title

class RecentSearch(models.Model):
    city = models.CharField(max_length=100)
    temperature = models.FloatField()
    description = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city} at {self.timestamp}"