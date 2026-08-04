"""Read helpers and cache invalidation for municipality context profiles."""

from django.core.cache import cache


def invalidate_profile_cache_for_slugs(slugs: list[str]) -> None:
    for slug in slugs:
        cache.delete(f"context_profile_{slug}")
