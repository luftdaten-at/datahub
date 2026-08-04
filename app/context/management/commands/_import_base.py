from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from context.imports import accept, load_and_validate
from context.models import DatasetImport


class BaseImportCommand(BaseCommand):
    module: str = ""

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to JSON artifact.")
        parser.add_argument(
            "--expect-tiles",
            default=None,
            help="Optional PMTiles path to verify (heat imports only).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate only; do not persist or accept.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Accept despite warnings (e.g. low coverage).",
        )
        parser.add_argument(
            "--pending-only",
            action="store_true",
            help="Validate and leave as pending; do not auto-accept.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")

        raw = path.read_bytes()
        result = load_and_validate(
            raw,
            module=self.module,
            filename=path.name,
            source_path=str(path.resolve()),
            persist=not options["dry_run"],
        )

        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(f"WARN  {warning}"))
        for error in result.errors:
            self.stdout.write(self.style.ERROR(f"ERROR {error}"))

        if options.get("expect_tiles"):
            tiles_path = Path(options["expect_tiles"])
            if tiles_path.is_file():
                self.stdout.write(self.style.SUCCESS(f"Tiles file found: {tiles_path}"))
            else:
                result.warnings.append(f"Tiles file missing: {tiles_path}")
                self.stdout.write(
                    self.style.WARNING(f"WARN  Tiles file missing: {tiles_path}")
                )

        if not result.ok:
            imp = result.dataset_import
            suffix = f" (DatasetImport #{imp.pk})" if imp else ""
            raise CommandError(f"{len(result.errors)} error(s) — nothing accepted.{suffix}")

        if result.warnings and not options["force"]:
            raise CommandError("Warnings present. Re-run with --force to accept.")

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Validation OK — {result.profiles_in_file} profile(s) would be imported."
                )
            )
            return

        if options["pending_only"]:
            imp = result.dataset_import
            self.stdout.write(
                self.style.SUCCESS(
                    f"Validated — DatasetImport #{imp.pk} pending confirmation."
                )
            )
            return

        if result.dataset_import and result.dataset_import.status == DatasetImport.STATUS_ACCEPTED:
            self.stdout.write(
                self.style.SUCCESS("Identical payload already accepted (idempotent).")
            )
            return

        accepted = accept(result.dataset_import)
        if not accepted.ok:
            raise CommandError("; ".join(accepted.errors))
        self.stdout.write(
            self.style.SUCCESS(
                f"{accepted.dataset_import.profiles_written} profile(s) accepted."
            )
        )
