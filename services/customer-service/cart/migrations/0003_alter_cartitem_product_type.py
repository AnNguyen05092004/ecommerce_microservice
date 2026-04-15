from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0002_alter_cartitem_product_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cartitem",
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
