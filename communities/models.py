from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver

class Community(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    
    # We could use an ImageField, but for now we'll allow a URL for simplicity
    image_url = models.URLField(max_length=500, blank=True, help_text="A URL for the community banner image")
    
    # Who "owns" or manages this community
    manager = models.ForeignKey(User, related_name='managed_communities', on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class CommunityImage(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='community_gallery/')
    
    def __str__(self):
        return f"Gallery image for {self.community.name}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
