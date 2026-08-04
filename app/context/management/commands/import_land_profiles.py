from context.management.commands._import_base import BaseImportCommand


class Command(BaseImportCommand):
    help = "Validate and import externally pre-computed Copernicus land profiles."
    module = "land"
