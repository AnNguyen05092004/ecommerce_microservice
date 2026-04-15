from django.db import models


class PeripheralCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'peripheral_categories'
        verbose_name_plural = 'Peripheral Categories'

    def __str__(self):
        return self.name
