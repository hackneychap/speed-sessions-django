from django import forms
from .models import Community, CommunityImage, CalendarEvent, CommunityGroupVDOT

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
    join_code = forms.CharField(min_length=4, max_length=20, required=False, help_text="Custom unique code to join the community")

    class Meta:
        model = Community
        fields = ["name", "description", "image_url", "join_code", "num_groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, 10):
            self.fields[f"display_name_{i}"] = forms.CharField(max_length=50, required=False)
            self.fields[f"default_vdot_{i}"] = forms.FloatField(required=False)
        if self.instance and self.instance.pk:
            for group in self.instance.group_vdots.all():
                self.fields[f"display_name_{group.position}"].initial = group.display_name
                self.fields[f"default_vdot_{group.position}"].initial = group.default_vdot

    def save(self, commit=True):
        community = super().save(commit=commit)
        if commit:
            for i in range(1, community.num_groups + 1):
                CommunityGroupVDOT.objects.update_or_create(
                    community=community,
                    position=i,
                    defaults={
                        "display_name": self.cleaned_data.get(f"display_name_{i}", ""),
                        "default_vdot": self.cleaned_data.get(f"default_vdot_{i}"),
                    },
                )
            CommunityGroupVDOT.objects.filter(
                community=community, position__gt=community.num_groups
            ).delete()
        return community

    def clean_join_code(self):
        join_code = self.cleaned_data.get('join_code')
        if join_code:
            # Check for uniqueness
            qs = Community.objects.filter(join_code__iexact=join_code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This join code is already in use by another community.")
        return join_code

    def clean_gallery_images(self):
        files = self.files.getlist('gallery_images')
        if len(files) > 5:
            raise forms.ValidationError("You can only upload up to 5 gallery images.")
        
        for img in files:
            if img.size > 1024 * 1024: # 1MB
                raise forms.ValidationError(f"Image file too large (limit 1MB): {img.name}")
        
        return files
