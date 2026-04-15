from django.db import models


class MonitorCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'monitor_categories'
        verbose_name_plural = 'Monitor Categories'

    def __str__(self):
        return self.name
