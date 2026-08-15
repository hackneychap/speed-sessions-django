from django.contrib import admin
from .models import Community, CommunityGroupVDOT

class CommunityGroupVDOTInline(admin.TabularInline):
    model = CommunityGroupVDOT
    extra = 3

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    inlines = [CommunityGroupVDOTInline]
