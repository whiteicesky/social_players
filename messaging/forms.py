from django import forms

from .models import DirectMessage


class DirectMessageForm(forms.ModelForm):
    class Meta:
        model = DirectMessage
        fields = ['content', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2}),
            'image': forms.ClearableFileInput(attrs={'class': 'file-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content', '')
        image = cleaned_data.get('image')
        if not content and not image:
            raise forms.ValidationError("Message text or photo is required.")
        return cleaned_data
