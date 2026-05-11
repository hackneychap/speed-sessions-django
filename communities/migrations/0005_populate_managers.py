from django.db import migrations

def copy_manager_to_managers(apps, schema_editor):
    Community = apps.get_model('communities', 'Community')
    for community in Community.objects.all():
        if community.manager:
            community.managers.add(community.manager)

def reverse_copy_manager_to_managers(apps, schema_editor):
    Community = apps.get_model('communities', 'Community')
    for community in Community.objects.all():
        # Just grab the first manager if one exists
        manager = community.managers.first()
        if manager:
            community.manager = manager
            community.save()

class Migration(migrations.Migration):

    dependencies = [
        ('communities', '0004_add_managers_field'),
    ]

    operations = [
        migrations.RunPython(copy_manager_to_managers, reverse_copy_manager_to_managers),
    ]
