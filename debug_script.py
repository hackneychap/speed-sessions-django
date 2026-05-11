import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'speed_sessions.settings')
django.setup()
from django.contrib.auth.models import User
from communities.models import Community
from session_planner.models import TrainingBlock

# Let's inspect the database state
for user in User.objects.all():
    managed = user.managed_communities_set.all()
    if managed:
        print(f"User {user.username} manages: {[c.name for c in managed]}")

for block in TrainingBlock.objects.all():
    print(f"Block: '{block.title}', Tradeable: {block.is_tradeable}, Community: {block.community.name if block.community else 'None'}")
