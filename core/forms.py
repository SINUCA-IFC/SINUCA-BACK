from django import forms

from core.models import Gang, User
from uploader.models import Image


class SignupProfileForm(forms.Form):
    """Campos do cadastro original, salvos dentro do fluxo do allauth."""

    role = forms.ChoiceField(
        choices=[(User.Role.STUDENT, 'Discente'), (User.Role.ORGANIZER, 'Organizador')], required=False,
    )
    name = forms.CharField(max_length=255, required=False)
    matriculation = forms.CharField(max_length=10, required=False)
    gang = forms.ModelChoiceField(queryset=Gang.objects.all(), required=False)

    def signup(self, request, user):
        for field in ('name', 'matriculation', 'gang'):
            setattr(user, field, self.cleaned_data.get(field))
        user.country = None
        user.role = self.cleaned_data.get('role') or User.Role.STUDENT
        if user.role == User.Role.ORGANIZER:
            user.gang = None
            user.matriculation = ''
        user.save()
        photo = getattr(request, 'registration_photo', None)
        if photo:
            image = Image(file=photo, owner=user, size=photo.size)
            try:
                image.save()
                user.foto = image
                user.save(update_fields=['foto'])
            except Exception:
                if image.file._committed:
                    image.file.delete(save=False)
                raise
