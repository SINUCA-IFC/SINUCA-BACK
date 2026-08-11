from django.db import models

from core.models.country import Country
from core.models.link import Link


class Schedule(models.Model):

    class CATEGORY(models.IntegerChoices):
        POST = 1, 'Postagem'
        DISCUSSION = 2, 'Debate'
        COOP = 3, 'Mesa de cooperação'
        APRE = 4, 'Apresentação cultural'

    category = models.IntegerField(choices=CATEGORY.choices)

    title = models.CharField(max_length=100)

    startDate = models.DateTimeField()
    endDate = models.DateTimeField()

    location = models.CharField(max_length=100, blank=True, null=True)

    description = models.TextField()

    class TIPO(models.IntegerChoices):
        DANCA = 1, 'Dança Típica'
        COMIDA = 2, 'Comida Típica'

    tipo = models.IntegerField(choices=TIPO.choices, blank=True, null=True)


    country = models.ManyToManyField(
        Country,
        related_name='schedule_country',
    )

    docs = models.ManyToManyField(
        Link,
        related_name='schedule_docs',
        blank=True,
    )

    def __str__(self):
        return self.title
