from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reviews", "0002_alter_review_product_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="review",
            name="product_type",
            field=models.CharField(
                choices=[
                    ("computer", "Computer"),
                    ("mobile", "Mobile"),
                    ("clothes", "Clothes"),
                    ("tablet", "Tablet"),
                    ("audio", "Audio"),
                    ("wearable", "Wearable"),
                    ("component", "Component"),
                    ("peripheral", "Peripheral"),
                    ("monitor", "Monitor"),
                    ("accessory", "Accessory"),
                    ("charging", "Charging"),
                    ("book", "Book"),
                ],
                max_length=10,
            ),
        ),
    ]
