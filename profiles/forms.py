from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    avatar = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'file-input'}))

    class Meta:
        model = Profile
        fields = ['display_name', 'bio', 'avatar']
