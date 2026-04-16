from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
        ('requests', '0004_quoterequest_broker'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='review',
            name='broker_quote',
        ),
        migrations.AddField(
            model_name='review',
            name='quote_request',
            field=models.OneToOneField(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='requests.quoterequest'
            ),
        ),
    ]
