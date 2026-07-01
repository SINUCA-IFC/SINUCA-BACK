from django.db import models

from core.models import Country


class Link(models.Model):
    name = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=200)

    country = models.ManyToManyField(
        Country,
        related_name='link_country',
    )

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.url
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
