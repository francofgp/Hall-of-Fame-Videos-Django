from .models import Video
from django import forms


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = ["url"]  # los otros campos lo sacamos con la API
        #fields = ["title", "url", "youtube_id"]
        # CUSTOMIZATION PARA los labels
        labels = {"url": "YouTube URL"}


class SearchForm(forms.Form):
    search_term = forms.CharField(
        max_length=255, label="Search for Videos")
