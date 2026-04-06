from django import forms
from .models import Order, MerchItem, MerchImage

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'customer_email', 'shipping_address']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
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

class MerchItemForm(forms.ModelForm):
    images = MultipleFileField(required=False)

    class Meta:
        model = MerchItem
        fields = ['name', 'description', 'price', 'available_sizes', 'available_colors']

    def clean_images(self):
        # In Django, if allow_multiple_selected is True, 
        # the field will receive a list of files in the clean method.
        # But we also have self.files.getlist('images')
        files = self.files.getlist('images')
        if len(files) > 5:
            raise forms.ValidationError("You can only upload up to 5 images.")
        
        for img in files:
            if img.size > 1024 * 1024: # 1MB
                raise forms.ValidationError(f"Image file too large (limit 1MB): {img.name}")
        
        return files
