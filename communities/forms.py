from django import forms
from .models import Community, CommunityImage, CalendarEvent

class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = ['title', 'date', 'description', 'is_public']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class CommunityForm(forms.ModelForm):
    gallery_images = MultipleFileField(required=False)

    class Meta:
        model = Community
        fields = ['name', 'description', 'image_url']

    def clean_gallery_images(self):
        files = self.files.getlist('gallery_images')
        if len(files) > 5:
            raise forms.ValidationError("You can only upload up to 5 gallery images.")
        
        for img in files:
            if img.size > 1024 * 1024: # 1MB
                raise forms.ValidationError(f"Image file too large (limit 1MB): {img.name}")
        
        return files
