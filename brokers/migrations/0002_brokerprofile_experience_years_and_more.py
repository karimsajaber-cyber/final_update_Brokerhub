from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brokers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='brokerprofile',
            name='experience_years',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='brokerprofile',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to='brokers/avatars/'),
        ),
    ]
