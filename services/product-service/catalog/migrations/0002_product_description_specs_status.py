from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="product",
            name="specs",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="product",
            name="status",
            field=models.CharField(default="available", max_length=32),
        ),
    ]
