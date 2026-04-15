from django.db import models


class WearableCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'wearable_categories'
        verbose_name_plural = 'Wearable Categories'

    def __str__(self):
        return self.name
