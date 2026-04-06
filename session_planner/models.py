from django.db import models
from django.contrib.auth.models import User
from communities.models import Community

class Session(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True)
    
    # Association with Community
    community = models.ForeignKey(Community, related_name='sessions', on_delete=models.CASCADE, null=True, blank=True)
    
    # Who created this session
    creator = models.ForeignKey(User, related_name='created_sessions', on_delete=models.SET_NULL, null=True)
    
    # Store the base raw structure as JSON
    # This includes the item_types, reps, distances, intensities, rests, block_multipliers
    structure_json = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} - {self.date}"

class SessionGroup(models.Model):
    session = models.ForeignKey(Session, related_name='groups', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    vdot = models.FloatField()
    
    # Optional override of the structure for this specific group
    # If null, it should use the session's structure_json
    structure_json = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} (VDOT: {self.vdot})"
    
    def get_structure(self):
        return self.structure_json if self.structure_json else self.session.structure_json

class TrainingBlock(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_distance = models.CharField(max_length=50)
    created_by = models.ForeignKey(User, related_name='training_blocks', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class BlockSessionTemplate(models.Model):
    block = models.ForeignKey(TrainingBlock, related_name='templates', on_delete=models.CASCADE)
    week_number = models.IntegerField()
    title = models.CharField(max_length=200)
    structure_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (Week {self.week_number})"
