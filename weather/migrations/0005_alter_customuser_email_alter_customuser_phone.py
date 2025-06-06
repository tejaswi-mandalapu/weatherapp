# Generated by Django 4.2.1 on 2025-05-27 18:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weather', '0004_customuser_dob_customuser_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='phone',
            field=models.CharField(blank=True, max_length=15, null=True, unique=True),
        ),
    ]
