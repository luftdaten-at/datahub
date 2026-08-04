from django.core.management.base import BaseCommand

from context.models import DatasetImport


class Command(BaseCommand):
    help = "List pending and recent DatasetImport records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--status",
            default=None,
            choices=[s for s, _ in DatasetImport.STATUS_CHOICES],
            help="Filter by status.",
        )
        parser.add_argument(
            "--module",
            default=None,
            choices=["land", "heat"],
            help="Filter by module.",
        )

    def handle(self, *args, **options):
        qs = DatasetImport.objects.all()
        if options["status"]:
            qs = qs.filter(status=options["status"])
        if options["module"]:
            qs = qs.filter(module=options["module"])

        if not qs.exists():
            self.stdout.write("No imports found.")
            return

        for imp in qs[:50]:
            errors = len((imp.validation_report or {}).get("errors", []))
            warnings = len((imp.validation_report or {}).get("warnings", []))
            self.stdout.write(
                f"#{imp.pk}  {imp.module:5}  {imp.status:8}  "
                f"{imp.reference_date or '-':10}  "
                f"in={imp.profiles_in_file} written={imp.profiles_written}  "
                f"errors={errors} warnings={warnings}  {imp.source_filename}"
            )
