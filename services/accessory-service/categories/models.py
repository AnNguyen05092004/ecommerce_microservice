from django.db import models


class AccessoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'accessory_categories'
        verbose_name_plural = 'Accessory Categories'

    def __str__(self):
        return self.name
