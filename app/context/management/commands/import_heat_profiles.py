from context.management.commands._import_base import BaseImportCommand


class Command(BaseImportCommand):
    help = "Validate and import externally pre-computed LST heat profiles."
    module = "heat"
