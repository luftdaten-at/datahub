from django.core.management.base import BaseCommand

from context.imports import accept
from context.models import DatasetImport


class Command(BaseCommand):
    help = "Accept a pending DatasetImport by ID."

    def add_arguments(self, parser):
        parser.add_argument("import_id", type=int, help="DatasetImport primary key.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Accept despite warnings recorded in validation_report.",
        )

    def handle(self, *args, **options):
        try:
            dataset_import = DatasetImport.objects.get(pk=options["import_id"])
        except DatasetImport.DoesNotExist as exc:
            raise SystemExit(f"DatasetImport #{options['import_id']} not found.") from exc

        warnings = (dataset_import.validation_report or {}).get("warnings", [])
        if warnings and not options["force"]:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"WARN  {w}"))
            raise SystemExit("Warnings present. Re-run with --force.")

        result = accept(dataset_import)
        for error in result.errors:
            self.stdout.write(self.style.ERROR(f"ERROR {error}"))
        if not result.ok:
            raise SystemExit("Accept failed.")
        self.stdout.write(
            self.style.SUCCESS(
                f"Accepted DatasetImport #{dataset_import.pk}: "
                f"{dataset_import.profiles_written} profile(s) written."
            )
        )
