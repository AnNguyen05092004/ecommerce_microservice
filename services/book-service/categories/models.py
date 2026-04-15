from django.db import models


class BookCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'book_categories'
        verbose_name_plural = 'Book Categories'

    def __str__(self):
        return self.name
