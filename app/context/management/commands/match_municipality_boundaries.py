from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from context.boundaries import load_boundaries_from_gpkg, match_all_municipalities


class Command(BaseCommand):
    help = (
        "Match municipality slugs to Statistik Austria GKZ and load boundary "
        "polygons from a GeoPackage (Gebietsstand must match the file year)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--boundaries",
            required=True,
            help="Path to gemeinden GeoPackage, e.g. /data/in/gemeinden_2026.gpkg",
        )
        parser.add_argument("--layer", default=None, help="Optional layer name.")
        parser.add_argument(
            "--gkz-field",
            default="gkz",
            help="GeoPackage attribute for Gemeindekennziffer.",
        )
        parser.add_argument(
            "--name-field",
            default="name",
            help="GeoPackage attribute for municipality name.",
        )

    def handle(self, *args, **options):
        path = Path(options["boundaries"])
        if not path.is_file():
            raise CommandError(f"Boundary file not found: {path}")

        self.stdout.write(f"Loading boundaries from {path} …")
        boundaries = load_boundaries_from_gpkg(
            str(path),
            layer_name=options["layer"],
            gkz_field=options["gkz_field"],
            name_field=options["name_field"],
        )
        if not boundaries:
            raise CommandError("No boundary features loaded from GeoPackage.")

        self.stdout.write(f"Loaded {len(boundaries)} boundary features.")
        counts = match_all_municipalities(boundaries)
        self.stdout.write(
            self.style.SUCCESS(
                "Matching complete: "
                f"PIP={counts['matched_pip']}, "
                f"name={counts['matched_name']}, "
                f"unresolved={counts['unresolved']}, "
                f"skipped (manual)={counts['skipped']}"
            )
        )
        if counts["unresolved"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{counts['unresolved']} municipalities need manual review in Admin."
                )
            )
