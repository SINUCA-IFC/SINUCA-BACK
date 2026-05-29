from django.db import models


class Gang(models.Model):
    name = models.CharField(max_length=7)
    CourseChoices = (
        ('INFO', 'Informática para Internet'),
        ('AGRO', 'Agropecuária'),
        ('QUIMI', 'Química'),
    )
    courses = models.CharField(max_length=50, choices=CourseChoices)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'
