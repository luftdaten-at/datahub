"""IANA time zones for interpreting naive datetimes consistently."""

from zoneinfo import ZoneInfo

# Naive timestamps in workshop JSON uploads and naive log line strings use this zone.
NAIVE_LOCAL_TZ = ZoneInfo("Europe/Vienna")
