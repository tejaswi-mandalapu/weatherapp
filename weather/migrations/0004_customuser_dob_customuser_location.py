# Generated by Django 4.2.1 on 2025-05-26 19:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('weather', '0003_recentsearch_weatherblog_remove_customuser_dob_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='customuser',
            name='location',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
