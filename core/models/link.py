from django.db import models

class Link(models.Model):
    name = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=200)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.url
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
