from django.db import models


class Schedule(models.Model):

    class CATEGORY(models.IntegerChoices):
        POST = 1, 'Postagem'
        DISCUSSION = 2, 'Debate'
        COOP = 3, 'Mesa de cooperação'

    category = models.IntegerField(choices=CATEGORY.choices)

    title = models.CharField(max_length=100)

    startDate = models.DateTimeField()
    endDate = models.DateTimeField()

    location = models.CharField(max_length=100, blank=True, null=True)

    description = models.TextField()

    def __str__(self):
        return self.title
