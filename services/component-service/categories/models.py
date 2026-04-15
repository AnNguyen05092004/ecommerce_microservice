from django.db import models


class ComponentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'component_categories'
        verbose_name_plural = 'Component Categories'

    def __str__(self):
        return self.name
