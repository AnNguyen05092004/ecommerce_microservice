from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='product_type',
            field=models.CharField(
                choices=[
                    ('computer', 'Computer'),
                    ('mobile', 'Mobile'),
                    ('clothes', 'Clothes'),
                ],
                max_length=10,
            ),
        ),
    ]
