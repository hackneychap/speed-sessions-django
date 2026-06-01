import requests
from datetime import datetime, timedelta
import zoneinfo
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from communities.models import Community

class Command(BaseCommand):
    help = 'Checks OpenActive track APIs for configured communities and sends an email to managers regarding track status.'

    def handle(self, *args, **options):
        today = datetime.now()

        # Get communities that have track API configured
        communities = Community.objects.exclude(
            track_api_link__exact=''
        ).exclude(
            track_training_day__isnull=True
        )

        for community in communities:
            self.stdout.write(f"Checking community: {community.name}")

            # Find the date of the next occurrence of their training day
            days_until_training = (community.track_training_day - today.weekday()) % 7
            if days_until_training == 0:
                # If today IS the day, are we looking at today or next week?
                # Usually we run this the morning of, so if it's 0 we keep it 0 to check today.
                # However, to match the original script behaviour, if it is 0 it checks next week.
                # Since the requirement is "Then in the morning of the day it checks the api to see if they are going to be open at that time."
                # We should check TODAY if today is the day.
                # So if days_until_training == 0, we leave it as 0.
                pass

            target_date_obj = today + timedelta(days=days_until_training)
            target_date = target_date_obj.strftime("%Y-%m-%d")

            url = community.track_api_link
            track_sessions = {}
            page_count = 0

            self.stdout.write(f"  Fetching schedule for target date ({target_date})...")

            while url:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        break
                except requests.RequestException:
                    self.stdout.write(self.style.WARNING(f"  Failed to fetch from URL: {url}"))
                    break

                feed_data = response.json()
                items = feed_data.get("items", [])
                if not items:
                    break

                page_count += 1

                for item in items:
                    if item.get("state") == "deleted":
                        continue

                    data = item.get("data", {})
                    start_date = data.get("startDate", "")

                    if target_date in start_date:
                        locations_list = data.get("beta:sportsActivityLocation", [])
                        if locations_list:
                            raw_name = locations_list[0].get("name", "")
                            keyword = community.track_location_keyword or ""
                            if keyword.lower() in str(raw_name).lower() or not keyword:
                                item_id = item.get("id")
                                track_sessions[item_id] = item

                url = feed_data.get("next")

                # Safety break to prevent infinite loops on broken RPDE feeds
                if page_count > 100:
                    self.stdout.write(self.style.WARNING("  Reached 100 pages, stopping pagination to prevent infinite loop."))
                    break

            track_sessions_list = list(track_sessions.values())
            self.stdout.write(f"  Found {len(track_sessions_list)} sessions matching target date and location keyword.")

            # Now we look for a match on the specific time
            is_open = False
            found_time_formatted = "??:??"

            if community.track_training_time:
                target_time_str = community.track_training_time.strftime("%H:%M")

                for session in track_sessions_list:
                    data = session.get("data", {})
                    start_time_raw = data.get("startDate", "")

                    try:
                        dt_utc = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
                        uk_zone = zoneinfo.ZoneInfo("Europe/London")
                        dt_uk_local = dt_utc.astimezone(uk_zone)
                        time_formatted = dt_uk_local.strftime("%H:%M")

                        if time_formatted == target_time_str:
                            is_open = True
                            found_time_formatted = time_formatted
                            break
                    except Exception:
                        continue
            else:
                # If they didn't specify a time, we just check if there's ANY session that day
                if track_sessions_list:
                    is_open = True

            # Email managers
            manager_emails = [m.email for m in community.managers.all() if m.email]

            if manager_emails:
                day_name = community.get_track_training_day_display()
                time_str = community.track_training_time.strftime("%H:%M") if community.track_training_time else "any time"

                if is_open:
                    subject = f"✅ Track Open Confirmed: {community.name} Training Today"
                    message = (
                        f"Good news!\n\n"
                        f"We found a scheduled track session matching your criteria for {day_name} at {time_str}.\n"
                        f"The track should be open for {community.name}'s training session.\n\n"
                        f"Date: {target_date}\n"
                        f"Location Keyword: {community.track_location_keyword}\n"
                    )
                else:
                    subject = f"⚠️ Track Might Be Closed: {community.name} Training Today"
                    message = (
                        f"Warning!\n\n"
                        f"We checked the schedule for {day_name} at {time_str}, but could not find a matching session.\n"
                        f"The track might be closed for {community.name}'s training session. Please check with the venue manually.\n\n"
                        f"Date: {target_date}\n"
                        f"Location Keyword: {community.track_location_keyword}\n"
                    )

                self.stdout.write(f"  Sending email to managers: {', '.join(manager_emails)}")

                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Speed Sessions <noreply@speedsessions.com>')

                send_mail(
                    subject,
                    message,
                    from_email,
                    manager_emails,
                    fail_silently=False,
                )
            else:
                self.stdout.write(self.style.WARNING(f"  No manager emails found for community {community.name}"))

        self.stdout.write(self.style.SUCCESS("Finished checking all configured communities."))
