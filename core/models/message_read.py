from django.conf import settings
from django.db import models

from .country import Country


class MessageRead(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    # As mensagens posteriores a este ID ainda não foram lidas por este usuário.
    last_read_message_id = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'country'], name='unique_message_read_user_country'),
        ]
