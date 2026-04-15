from django.db import models


class ComputerCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'computer_categories'
        verbose_name_plural = 'Computer Categories'

    def __str__(self):
        return self.name
