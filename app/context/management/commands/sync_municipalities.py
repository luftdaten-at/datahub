from django.core.management.base import BaseCommand

from context.sync import sync_municipalities_from_api


class Command(BaseCommand):
    help = "Mirror api.luftdaten.at /city/all into context.Municipality."

    def handle(self, *args, **options):
        created, updated, error = sync_municipalities_from_api()
        if error:
            raise SystemExit(f"sync failed: {error}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced municipalities: {created} created, {updated} updated."
            )
        )
