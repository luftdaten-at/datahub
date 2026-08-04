from django.core.management.base import BaseCommand

from context.peer_groups import build_peer_groups


class Command(BaseCommand):
    help = "Build peer groups from imported land profiles and assign municipalities."

    def handle(self, *args, **options):
        counts = build_peer_groups()
        self.stdout.write(self.style.SUCCESS(f"Peer groups assigned: {counts}"))
