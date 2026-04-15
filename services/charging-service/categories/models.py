from django.db import models


class ChargingCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'charging_categories'
        verbose_name_plural = 'Charging Categories'

    def __str__(self):
        return self.name
