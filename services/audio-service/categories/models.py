from django.db import models


class AudioCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'audio_categories'
        verbose_name_plural = 'Audio Categories'

    def __str__(self):
        return self.name
