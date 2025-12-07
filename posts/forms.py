from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['topic'].initial = Post.TOPIC_NON_GAME

    class Meta:
        model = Post
        fields = ['content', 'topic', 'image']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
            'topic': forms.Select(attrs={'class': 'topic-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'file-input'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'file-input'}),
        }
