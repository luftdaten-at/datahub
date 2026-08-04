"""Single validation path for external land and heat profile artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from jsonschema import Draft202012Validator

from .models import DatasetImport, Municipality, MunicipalityHeatProfile, MunicipalityLandProfile
from .services import invalidate_profile_cache_for_slugs

ALLOWED_QUALITY_FLAGS = {
    "insufficient_clear_pixels",
    "no_rural_reference",
    "high_relief",
    "weak_regression",
    "substituted_date",
    "population_suppressed",
}

SCHEMA_FILES = {
    "heat": "heat_profiles.v1.schema.json",
    "land": "land_profiles.v1.schema.json",
}


@dataclass
class ImportResult:
    dataset_import: DatasetImport | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    profiles_in_file: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _schema_path(module: str) -> Path:
    filename = SCHEMA_FILES[module]
    return Path(__file__).resolve().parent / "schemas" / filename


def _load_schema(module: str) -> dict:
    with open(_schema_path(module), encoding="utf-8") as fh:
        return json.load(fh)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse_generated_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.utc)
    return dt


def _format_version_ok(version: str) -> bool:
    if not version:
        return False
    if version.startswith("2."):
        return False
    return version.startswith("1.")


def _validate_schema(document: dict, module: str) -> list[str]:
    schema = _load_schema(module)
    validator = Draft202012Validator(schema)
    return [e.message for e in validator.iter_errors(document)]


def _municipality_map() -> dict[str, Municipality]:
    return {m.slug: m for m in Municipality.objects.all()}


def _validate_quality_flags(flags: list | None, slug: str) -> list[str]:
    errors = []
    if flags is None:
        errors.append(f"{slug}: quality_flags is required")
        return errors
    for flag in flags:
        if flag not in ALLOWED_QUALITY_FLAGS:
            errors.append(f"{slug}: unknown quality_flag {flag!r}")
    return errors


def _validate_heat_profile(profile: dict, municipality: Municipality | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    slug = profile.get("municipality_slug", "?")

    errors.extend(_validate_quality_flags(profile.get("quality_flags"), slug))

    if municipality is None:
        errors.append(f"{slug}: unknown municipality_slug")
        return errors, warnings
    if not municipality.is_analysable:
        errors.append(f"{slug}: municipality is unresolved or has no boundary")

    lst_mean = profile.get("lst_mean")
    lst_p10 = profile.get("lst_p10")
    lst_p90 = profile.get("lst_p90")
    lst_max = profile.get("lst_max")

    if lst_mean is not None and not (-20 <= lst_mean <= 70):
        errors.append(f"{slug}: lst_mean out of range ({lst_mean})")
    clear_fraction = profile.get("clear_fraction")
    if clear_fraction is not None and not (0 <= clear_fraction <= 1):
        errors.append(f"{slug}: clear_fraction out of range ({clear_fraction})")
    suhi_day = profile.get("suhi_day")
    if suhi_day is not None and not (-10 <= suhi_day <= 20):
        errors.append(f"{slug}: suhi_day out of range ({suhi_day})")

    ordered = [v for v in (lst_p10, lst_mean, lst_p90, lst_max) if v is not None]
    if len(ordered) >= 2:
        if lst_p10 is not None and lst_mean is not None and lst_p10 > lst_mean:
            errors.append(f"{slug}: lst_p10 ({lst_p10}) > lst_mean ({lst_mean})")
        if lst_mean is not None and lst_p90 is not None and lst_mean > lst_p90:
            errors.append(f"{slug}: lst_mean ({lst_mean}) > lst_p90 ({lst_p90})")
        if lst_p90 is not None and lst_max is not None and lst_p90 > lst_max:
            errors.append(f"{slug}: lst_p90 ({lst_p90}) > lst_max ({lst_max})")

    pop_hot = profile.get("pop_in_hotspots")
    pop_total = profile.get("pop_total")
    if pop_hot is not None and pop_total is not None and pop_hot > pop_total:
        errors.append(f"{slug}: pop_in_hotspots ({pop_hot}) > pop_total ({pop_total})")

    has_coeff = profile.get("dlst_per_10pct_tcd") is not None or profile.get(
        "dlst_per_10pct_imd"
    ) is not None
    regression_n = profile.get("regression_n")
    if has_coeff and (regression_n is None or regression_n <= 0):
        errors.append(f"{slug}: regression_n must be > 0 when coefficients are provided")

    if municipality and lst_mean is not None:
        try:
            previous = MunicipalityHeatProfile.objects.get(municipality=municipality)
            if previous.lst_mean is not None:
                delta = abs(previous.lst_mean - lst_mean)
                if delta > settings.CONTEXT_IMPORT_MAX_LST_DELTA_K:
                    warnings.append(
                        f"{slug}: lst_mean deviates by {delta:.1f} K from previous import"
                    )
        except MunicipalityHeatProfile.DoesNotExist:
            pass

    return errors, warnings


def _validate_land_profile(profile: dict, municipality: Municipality | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    slug = profile.get("municipality_slug", "?")

    errors.extend(_validate_quality_flags(profile.get("quality_flags"), slug))

    if municipality is None:
        errors.append(f"{slug}: unknown municipality_slug")
        return errors, warnings
    if not municipality.is_analysable:
        errors.append(f"{slug}: municipality is unresolved or has no boundary")

    for field_name in ("imperviousness_pct", "tree_cover_pct"):
        value = profile.get(field_name)
        if value is not None and not (0 <= value <= 100):
            errors.append(f"{slug}: {field_name} out of range ({value})")

    return errors, warnings


def _reference_date_from_document(document: dict, module: str) -> date | None:
    if module == "heat":
        raw = document.get("reference_date_primary")
        if raw:
            return parse_date(raw)
        profiles = document.get("profiles") or []
        if profiles:
            return parse_date(profiles[0].get("reference_date"))
    if module == "land":
        year = document.get("reference_year_primary")
        if year:
            return date(int(year), 1, 1)
    return None


def _build_validation_report(
    *,
    module: str,
    document: dict,
    errors: list[str],
    warnings: list[str],
    counts: dict[str, int],
) -> dict:
    return {
        "checked_at": timezone.now().isoformat().replace("+00:00", "Z"),
        "schema_version": document.get("format_version"),
        "module": module,
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
        "profiles": document.get("profiles", []),
    }


def load_and_validate(
    raw: bytes,
    *,
    module: str,
    filename: str,
    source_path: str = "",
    user=None,
    persist: bool = True,
) -> ImportResult:
    """Validate artifact and optionally create a pending DatasetImport."""
    result = ImportResult()
    digest = _sha256(raw)

    if module not in SCHEMA_FILES:
        result.errors.append(f"Unknown module {module!r}")
        return result

    existing = DatasetImport.objects.filter(module=module, source_sha256=digest).first()
    if existing and existing.status == DatasetImport.STATUS_ACCEPTED:
        result.dataset_import = existing
        result.warnings.append("Identical payload already accepted (idempotent).")
        return result

    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"Invalid JSON: {exc}")
        return result

    if document.get("module") != module:
        result.errors.append(
            f"module mismatch: expected {module!r}, got {document.get('module')!r}"
        )

    format_version = document.get("format_version", "")
    if not _format_version_ok(format_version):
        result.errors.append(f"Unsupported format_version: {format_version!r}")

    result.errors.extend(_validate_schema(document, module))
    if result.errors:
        if persist:
            result.dataset_import = _create_import_record(
                module=module,
                document=document,
                filename=filename,
                source_path=source_path,
                digest=digest,
                user=user,
                status=DatasetImport.STATUS_REJECTED,
                validation_report=_build_validation_report(
                    module=module,
                    document=document,
                    errors=result.errors,
                    warnings=result.warnings,
                    counts={"profiles_in_file": len(document.get("profiles") or [])},
                ),
            )
        return result

    municipalities = _municipality_map()
    profiles = document.get("profiles") or []
    result.profiles_in_file = len(profiles)
    counts = {
        "profiles_in_file": len(profiles),
        "slugs_unknown": 0,
        "slugs_unmatched": 0,
        "out_of_range": 0,
        "inconsistent": 0,
        "delta_exceeded": 0,
    }

    analysable_count = sum(1 for m in municipalities.values() if m.is_analysable)

    for profile in profiles:
        slug = profile.get("municipality_slug", "")
        municipality = municipalities.get(slug)
        if municipality is None:
            counts["slugs_unknown"] += 1
            result.errors.append(f"{slug or '?'}: unknown municipality_slug")
            continue
        if not municipality.is_analysable:
            counts["slugs_unmatched"] += 1

        if module == "heat":
            p_errors, p_warnings = _validate_heat_profile(profile, municipality)
        else:
            p_errors, p_warnings = _validate_land_profile(profile, municipality)

        for w in p_warnings:
            if "deviates" in w:
                counts["delta_exceeded"] += 1
        result.errors.extend(p_errors)
        result.warnings.extend(p_warnings)

    if analysable_count and profiles:
        delivered = len(
            {
                p.get("municipality_slug")
                for p in profiles
                if p.get("municipality_slug") in municipalities
                and municipalities[p.get("municipality_slug")].is_analysable
            }
        )
        coverage = delivered / analysable_count
        if coverage < settings.CONTEXT_IMPORT_MIN_COVERAGE:
            result.warnings.append(
                f"Coverage {coverage:.0%} below minimum "
                f"{settings.CONTEXT_IMPORT_MIN_COVERAGE:.0%}"
            )

    validation_report = _build_validation_report(
        module=module,
        document=document,
        errors=result.errors,
        warnings=result.warnings,
        counts=counts,
    )

    status = (
        DatasetImport.STATUS_REJECTED
        if result.errors
        else DatasetImport.STATUS_PENDING
    )

    if persist:
        result.dataset_import = _create_import_record(
            module=module,
            document=document,
            filename=filename,
            source_path=source_path,
            digest=digest,
            user=user,
            status=status,
            validation_report=validation_report,
            profiles_flagged=sum(
                1 for p in profiles if p.get("quality_flags")
            ),
        )
    else:
        result.dataset_import = None

    return result


def _create_import_record(
    *,
    module: str,
    document: dict,
    filename: str,
    source_path: str,
    digest: str,
    user,
    status: str,
    validation_report: dict,
    profiles_flagged: int = 0,
) -> DatasetImport:
    profiles = document.get("profiles") or []
    manifest = document.get("manifest") or {}
    return DatasetImport.objects.create(
        module=module,
        format_version=document.get("format_version", ""),
        producer=document.get("producer", ""),
        producer_version=document.get("producer_version", ""),
        reference_date=_reference_date_from_document(document, module),
        source_filename=filename,
        source_sha256=digest,
        source_path=source_path,
        generated_utc=_parse_generated_utc(document.get("generated_utc")),
        manifest=manifest,
        validation_report=validation_report,
        status=status,
        profiles_in_file=len(profiles),
        profiles_flagged=profiles_flagged,
        uploaded_by=user,
    )


def _upsert_heat_profile(municipality: Municipality, profile: dict, producer_version: str) -> None:
    acquisition = profile.get("acquisition_utc")
    acquisition_dt = _parse_generated_utc(acquisition)
    if acquisition_dt is None:
        raise ValueError(f"{profile.get('municipality_slug')}: invalid acquisition_utc")

    ref_date = parse_date(profile.get("reference_date"))
    if ref_date is None:
        raise ValueError(f"{profile.get('municipality_slug')}: invalid reference_date")

    defaults = {
        "reference_date": ref_date,
        "acquisition_utc": acquisition_dt,
        "sensor": profile.get("sensor", ""),
        "stac_item_id": profile.get("stac_item_id", ""),
        "clear_fraction": profile.get("clear_fraction", 0),
        "lst_mean": profile.get("lst_mean"),
        "lst_p10": profile.get("lst_p10"),
        "lst_p90": profile.get("lst_p90"),
        "lst_max": profile.get("lst_max"),
        "suhi_day": profile.get("suhi_day"),
        "suhi_night": profile.get("suhi_night"),
        "dlst_per_10pct_tcd": profile.get("dlst_per_10pct_tcd"),
        "dlst_per_10pct_imd": profile.get("dlst_per_10pct_imd"),
        "regression_r2": profile.get("regression_r2"),
        "regression_n": profile.get("regression_n"),
        "pop_in_hotspots": profile.get("pop_in_hotspots"),
        "pop_total": profile.get("pop_total"),
        "lst_by_landuse": profile.get("lst_by_landuse") or {},
        "quality_flags": profile.get("quality_flags") or [],
        "producer_version": producer_version,
    }
    MunicipalityHeatProfile.objects.update_or_create(
        municipality=municipality,
        defaults=defaults,
    )


def _upsert_land_profile(municipality: Municipality, profile: dict, producer_version: str) -> None:
    defaults = {
        "reference_year": int(profile["reference_year"]),
        "imperviousness_pct": profile.get("imperviousness_pct"),
        "imperviousness_change_pp": profile.get("imperviousness_change_pp"),
        "tree_cover_pct": profile.get("tree_cover_pct"),
        "landuse_shares": profile.get("landuse_shares") or {},
        "data_source": profile.get("data_source", ""),
        "quality_flags": profile.get("quality_flags") or [],
        "producer_version": producer_version,
    }
    MunicipalityLandProfile.objects.update_or_create(
        municipality=municipality,
        defaults=defaults,
    )


@transaction.atomic
def accept(dataset_import: DatasetImport) -> ImportResult:
    """Write a validated pending import into profile tables."""
    result = ImportResult(dataset_import=dataset_import)

    if dataset_import.status == DatasetImport.STATUS_ACCEPTED:
        result.warnings.append("Import already accepted.")
        return result
    if dataset_import.status == DatasetImport.STATUS_REJECTED:
        result.errors.append("Cannot accept a rejected import.")
        return result

    report = dataset_import.validation_report or {}
    if report.get("errors"):
        result.errors.extend(report["errors"])
        return result

    profiles = report.get("profiles") or []
    municipalities = _municipality_map()
    producer_version = dataset_import.producer_version or ""
    written_slugs: list[str] = []
    written = 0

    try:
        for profile in profiles:
            slug = profile.get("municipality_slug")
            municipality = municipalities.get(slug)
            if municipality is None or not municipality.is_analysable:
                continue
            if dataset_import.module == "heat":
                _upsert_heat_profile(municipality, profile, producer_version)
            elif dataset_import.module == "land":
                _upsert_land_profile(municipality, profile, producer_version)
            else:
                result.errors.append(f"Unknown module {dataset_import.module!r}")
                raise ValueError("invalid module")
            written += 1
            written_slugs.append(slug)
    except Exception as exc:
        result.errors.append(str(exc))
        raise

    dataset_import.status = DatasetImport.STATUS_ACCEPTED
    dataset_import.profiles_written = written
    dataset_import.accepted_at = timezone.now()
    dataset_import.save(
        update_fields=["status", "profiles_written", "accepted_at"]
    )
    invalidate_profile_cache_for_slugs(written_slugs)
    return result
