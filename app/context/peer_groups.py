"""Assign municipalities to peer groups based on land profile structure."""

from __future__ import annotations

from django.db import transaction

from .models import MunicipalityLandProfile, PeerGroup

PEER_GROUP_DEFINITIONS = [
    {
        "key": "low_impervious",
        "label_de": "Gering versiegelt",
        "label_en": "Low imperviousness",
        "description_de": "Versiegelungsgrad unter 25 %",
        "description_en": "Imperviousness below 25%",
        "min_impervious": None,
        "max_impervious": 25.0,
    },
    {
        "key": "medium_impervious",
        "label_de": "Mittel versiegelt",
        "label_en": "Medium imperviousness",
        "description_de": "Versiegelungsgrad 25–45 %",
        "description_en": "Imperviousness 25–45%",
        "min_impervious": 25.0,
        "max_impervious": 45.0,
    },
    {
        "key": "high_impervious",
        "label_de": "Stark versiegelt",
        "label_en": "High imperviousness",
        "description_de": "Versiegelungsgrad über 45 %",
        "description_en": "Imperviousness above 45%",
        "min_impervious": 45.0,
        "max_impervious": None,
    },
]


def _peer_group_for_imperviousness(value: float | None) -> str | None:
    if value is None:
        return None
    for definition in PEER_GROUP_DEFINITIONS:
        min_v = definition["min_impervious"]
        max_v = definition["max_impervious"]
        if min_v is not None and value < min_v:
            continue
        if max_v is not None and value >= max_v:
            continue
        return definition["key"]
    return PEER_GROUP_DEFINITIONS[-1]["key"]


@transaction.atomic
def build_peer_groups() -> dict[str, int]:
    """Create/update peer groups and assign land profiles."""
    groups: dict[str, PeerGroup] = {}
    for definition in PEER_GROUP_DEFINITIONS:
        group, _ = PeerGroup.objects.update_or_create(
            key=definition["key"],
            defaults={
                "label_de": definition["label_de"],
                "label_en": definition["label_en"],
                "description_de": definition["description_de"],
                "description_en": definition["description_en"],
            },
        )
        groups[definition["key"]] = group

    counts = {d["key"]: 0 for d in PEER_GROUP_DEFINITIONS}
    unassigned = 0

    for profile in MunicipalityLandProfile.objects.select_related("municipality"):
        key = _peer_group_for_imperviousness(profile.imperviousness_pct)
        if key is None:
            profile.peer_group = None
            profile.save(update_fields=["peer_group"])
            unassigned += 1
            continue
        profile.peer_group = groups[key]
        profile.save(update_fields=["peer_group"])
        counts[key] += 1

    counts["unassigned"] = unassigned
    return counts
