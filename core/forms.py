from django import forms

from core.models import Country, Gang
from uploader.models import Image


class SignupProfileForm(forms.Form):
    """Campos do cadastro original, salvos dentro do fluxo do allauth."""

    name = forms.CharField(max_length=255, required=False)
    matriculation = forms.CharField(max_length=10, required=False)
    foto = forms.ModelChoiceField(queryset=Image.objects.all(), required=False)
    gang = forms.ModelChoiceField(queryset=Gang.objects.all(), required=False)
    country = forms.ModelChoiceField(queryset=Country.objects.all(), required=False)

    def signup(self, request, user):
        for field in ('name', 'matriculation', 'foto', 'gang', 'country'):
            setattr(user, field, self.cleaned_data.get(field))
        user.save()
