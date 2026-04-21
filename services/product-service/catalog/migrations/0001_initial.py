from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
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
                ("name", models.CharField(max_length=120, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Product",
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
                (
                    "product_type",
                    models.CharField(
                        choices=[
                            ("computer", "Laptop"),
                            ("mobile", "Dien thoai"),
                            ("clothes", "Quan ao"),
                            ("tablet", "Tablet"),
                            ("audio", "Audio"),
                            ("wearable", "Wearable"),
                            ("component", "Linh kien"),
                            ("peripheral", "Phu kien PC"),
                            ("monitor", "Man hinh"),
                            ("accessory", "Phu kien dien thoai"),
                            ("charging", "Sac va pin"),
                            ("book", "Sach"),
                        ],
                        max_length=32,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("brand", models.CharField(blank=True, max_length=120)),
                ("price", models.DecimalField(decimal_places=2, max_digits=14)),
                ("stock", models.IntegerField(default=0)),
                ("image", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products",
                        to="catalog.category",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
