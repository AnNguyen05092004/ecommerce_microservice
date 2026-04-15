from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Wearable",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("brand", models.CharField(max_length=100)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("description", models.TextField(blank=True, default="")),
                ("image", models.CharField(blank=True, default="", max_length=500)),
                ("stock", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("available", "Available"),
                            ("unavailable", "Unavailable"),
                        ],
                        default="available",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="wearables",
                        to="categories.wearablecategory",
                    ),
                ),
            ],
            options={
                "db_table": "wearables",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="WearableSpec",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cpu", models.CharField(blank=True, default="", max_length=100)),
                ("ram", models.CharField(blank=True, default="", max_length=50)),
                ("storage", models.CharField(blank=True, default="", max_length=100)),
                ("gpu", models.CharField(blank=True, default="", max_length=100)),
                (
                    "screen_size",
                    models.CharField(blank=True, default="", max_length=20),
                ),
                ("os", models.CharField(blank=True, default="", max_length=50)),
                (
                    "wearable",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specs",
                        to="wearables.wearable",
                    ),
                ),
            ],
            options={
                "db_table": "wearable_specs",
            },
        ),
    ]
