from django.db import migrations


def backfill(apps, schema_editor):
    Community = apps.get_model("communities", "Community")
    CommunityGroupVDOT = apps.get_model("communities", "CommunityGroupVDOT")
    for c in Community.objects.all():
        for position, field in enumerate(["vdot_group_a", "vdot_group_b", "vdot_group_c"], start=1):
            value = getattr(c, field, None)
            CommunityGroupVDOT.objects.get_or_create(community=c, position=position, defaults={"display_name": f"Group {chr(64 + position)}", "default_vdot": value})


def reverse_backfill(apps, schema_editor):
    CommunityGroupVDOT = apps.get_model("communities", "CommunityGroupVDOT")
    CommunityGroupVDOT.objects.filter(position__lte=3).delete()


class Migration(migrations.Migration):

    dependencies = [("communities", "0011_communitygroupvdot")]

    operations = [migrations.RunPython(backfill, reverse_backfill)]
