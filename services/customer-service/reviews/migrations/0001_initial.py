from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Review",
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
                ("customer_id", models.IntegerField()),
                ("customer_name", models.CharField(default="", max_length=255)),
                ("product_id", models.IntegerField()),
                (
                    "product_type",
                    models.CharField(
                        choices=[("computer", "Computer"), ("mobile", "Mobile")],
                        max_length=10,
                    ),
                ),
                ("rating", models.IntegerField()),
                ("comment", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "reviews",
                "ordering": ["-created_at"],
                "unique_together": {("customer_id", "product_id", "product_type")},
            },
        ),
    ]
