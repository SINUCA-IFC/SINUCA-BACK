from django.db import models

from uploader.models import Image


class Country(models.Model):
    name = models.CharField(max_length=50)
    political_name = models.CharField(max_length=100)

    flag = models.ForeignKey(
        Image,
        related_name='country_flag',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )

    def __str__(self):
        return self.name
