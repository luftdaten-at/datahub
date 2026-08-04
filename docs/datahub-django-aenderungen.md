# Notwendige Änderungen im Datahub (Django)

**Implementierungsspezifikation für Modul 3 (Copernicus Land) und Modul 6 (Oberflächentemperatur)**

| | |
|---|---|
| Repository | `luftdaten-at/datahub`, Branch `main` |
| Stack | Django 4.2, Python 3.12 (Alpine), PostGIS 18-3.6, Bootstrap 5.3, Gunicorn |
| Status | Entwurf zur Diskussion |
| Betroffene Apps | neu: `context` — geändert: `municipalities`, `api`, `main` |

---

## Inhalt

1. [Befund aus dem bestehenden Code](#1-befund-aus-dem-bestehenden-code)
2. [Datenübernahme aus externer Vorberechnung](#2-datenübernahme-aus-externer-vorberechnung)
3. [Neue App `context`](#3-neue-app-context)
4. [Der eigentliche Knackpunkt: Slug ↔ Gemeindekennziffer](#4-der-eigentliche-knackpunkt-slug--gemeindekennziffer)
5. [Änderungen an bestehenden Dateien](#5-änderungen-an-bestehenden-dateien)
6. [`municipalities/views.py` im Detail](#6-municipalitiesviewspy-im-detail)
7. [Templates](#7-templates)
8. [API-Erweiterung](#8-api-erweiterung)
9. [Management Commands](#9-management-commands)
10. [Kachelauslieferung und nginx](#10-kachelauslieferung-und-nginx)
11. [Django-Admin](#11-django-admin)
12. [Tests](#12-tests)
13. [Migrationen und Deployment-Reihenfolge](#13-migrationen-und-deployment-reihenfolge)
14. [Vorarbeiten, die ohnehin fällig sind](#14-vorarbeiten-die-ohnehin-fällig-sind)
15. [Reihenfolge und Aufwand](#15-reihenfolge-und-aufwand)

---

## 1. Befund aus dem bestehenden Code

Vier Feststellungen aus dem Repo bestimmen die Architektur der Erweiterung.

### 1.1 Es gibt kein lokales Gemeindemodell

`municipalities/models.py` enthält ausschließlich `FavoriteMunicipality` mit einem `municipality_slug` als freiem `CharField`. Sämtliche Gemeindedaten werden zur Laufzeit per HTTP von `api.luftdaten.at` geholt (`/city/all`, `/city/current`). Es existiert weder eine Gemeindetabelle noch eine Gemeindegeometrie in der Datenbank.

**Konsequenz:** Für Zonal Statistics, Peer-Gruppen und Kartenausschnitte braucht es zwingend ein lokales `Municipality`-Modell mit Grenzgeometrie. Das ist keine Nebensache der Erweiterung, sondern deren Fundament — und die Stelle, an der der meiste unerwartete Aufwand liegt (siehe [Abschnitt 4](#4-der-eigentliche-knackpunkt-slug--gemeindekennziffer)).

### 1.2 PostGIS und GeoDjango sind bereits aktiv

Erfreulicher Befund:

- `django.contrib.gis` steht in `INSTALLED_APPS`
- `DATABASES.default.ENGINE` ist `django.contrib.gis.db.backends.postgis`
- `docker-compose.yml` nutzt `postgis/postgis:18-3.6`
- Das `Dockerfile` installiert `gdal`, `gdal-dev`, `geos`, `geos-dev`, `proj`, `proj-dev`

Geometriefelder, räumliche Indizes und Point-in-Polygon-Abfragen sind also ohne Infrastrukturänderung nutzbar. Der Vorschlag aus dem Modul-3-Papier, PostGIS zu vermeiden, ist damit hinfällig — es ist schon da.

### 1.3 Der App-Container ist Alpine-basiert

`FROM python:3.12-alpine`. Für `rasterio`, `rioxarray`, `odc-stac`, `scikit-learn` und `exactextract` gibt es auf musl keine manylinux-Wheels; alles würde aus dem Quellcode gebaut.

**Konsequenz:** Das ist kein Problem, weil die Rasterverarbeitung ohnehin extern stattfindet (siehe [Abschnitt 2](#2-datenübernahme-aus-externer-vorberechnung)). Der Punkt bleibt hier stehen als Begründung dafür, warum diese Trennung auch technisch die richtige ist und nicht nachträglich aufgeweicht werden sollte — der Wunsch, „nur schnell einen kleinen Rasterzugriff" in die App zu holen, kommt erfahrungsgemäß irgendwann auf.

Die einzige neue Abhängigkeit auf Django-Seite ist `jsonschema` für die Formatprüfung.

### 1.4 Statische Assets sind vendored, kein CDN

`app/static/js/` enthält `leaflet.js`, `chart.umd.js`, `plotly-2.27.0.min.js`, `leaflet.markercluster.js` lokal. Templates binden sie über `{% static %}` mit `integrity`-Hashes ein.

**Konsequenz:** `pmtiles` und das zugehörige Leaflet-Plugin müssen ebenfalls vendored werden. Kein `unpkg`-Import.

### 1.5 Nebenbefund: Cache-Konfiguration fehlt

In `main/settings.py` gibt es keinen `CACHES`-Block. Django fällt damit auf `LocMemCache` zurück — prozesslokal. Unter Gunicorn mit mehreren Workern hat jeder Worker seinen eigenen Cache, `cache.delete(CITY_ALL_CACHE_KEY)` in `MunicipalityAdminLocationUpdateView` invalidiert also nur einen von n Workern.

Für die neuen Module ist das unkritisch (sie lesen aus der Datenbank), für die bestehenden GeoSphere-Proxies aber schon. Ein Redis-Backend wäre ohnehin fällig.

---

## 2. Datenübernahme aus externer Vorberechnung

Die Raster- und Zonalstatistik-Auswertung findet **außerhalb des Datahub** statt — in einer eigenen Arbeitsumgebung, auf einem Rechenknoten oder bei einem Projektpartner. Der Datahub kennt diese Verarbeitung nicht und enthält keinerlei Geo-Verarbeitungsbibliotheken.

```
┌────────────────────────────┐        ┌───────────────────────────┐
│  externe Vorberechnung     │        │  Datahub (Django, Alpine) │
│  (nicht Teil dieses Repos) │        │                           │
│                            │  JSON  │  Import-Command validiert │
│  STAC, LST, Sharpening,    │───────▶│  und schreibt nach        │
│  Zonal Statistics,         │ PMTiles│  PostGIS                  │
│  PMTiles-Rendering         │        │                           │
└────────────────────────────┘        │  nginx liefert PMTiles    │
                                      └───────────────────────────┘
```

**Regel:** Der Datahub bekommt keine einzige Rasterbibliothek. Er nimmt fertige Artefakte entgegen, prüft sie streng und persistiert sie.

Damit ändert sich der Charakter der Schnittstelle grundlegend: Was vorher ein interner Verarbeitungsschritt gewesen wäre, ist jetzt ein **Vertrag mit einem externen Erzeuger**. Das Format muss versioniert, dokumentiert und maschinell prüfbar sein, und der Import muss davon ausgehen, dass die eingehende Datei fehlerhaft sein kann.

### 2.1 Übergabeformat

Zwei Artefakttypen, beide versioniert:

| Datei | Inhalt | Turnus |
|---|---|---|
| `land_profiles_<version>.json` | Copernicus-Land-Indikatoren je Gemeinde (Modul 3) | bei neuem CLMS-Release |
| `heat_profiles_<date>.json` | LST-Indikatoren je Gemeinde (Modul 6) | jährlich |
| `lst_<date>.pmtiles` | gerenderte Temperaturkarte | jährlich, zusammen mit den Heat-Profilen |

Aufbau der JSON-Dateien — Kopf mit Metadaten, dann eine flache Liste je Gemeinde:

```json
{
  "format_version": "1.0",
  "module": "heat",
  "generated_utc": "2026-09-15T08:12:44Z",
  "producer": "luftdaten-at/heat-pipeline",
  "producer_version": "1.0.0",
  "reference_date_primary": "2026-06-29",
  "manifest": {
    "stac_items": ["LC09_L2SP_190027_20260629_02_T1"],
    "s2_items": ["S2B_MSIL2A_20260628T100029_N0511_R122_T33UWP"],
    "lapse_rate_k_per_m": -0.0081,
    "sharpening_method": "tsharp_ndvi",
    "validation": {
      "landsat_vs_s3_bias_k": 1.9,
      "lst_vs_tawes_offset_k": 12.4,
      "lst_vs_tawes_r2": 0.61
    }
  },
  "profiles": [
    {
      "municipality_slug": "graz",
      "reference_date": "2026-06-29",
      "acquisition_utc": "2026-06-29T09:47:12Z",
      "sensor": "LANDSAT_9",
      "stac_item_id": "LC09_L2SP_190027_20260629_02_T1",
      "clear_fraction": 0.993,
      "lst_mean": 38.4,
      "lst_p10": 30.1,
      "lst_p90": 46.7,
      "lst_max": 54.2,
      "suhi_day": 4.8,
      "suhi_night": 3.1,
      "dlst_per_10pct_tcd": -2.4,
      "dlst_per_10pct_imd": 1.9,
      "regression_r2": 0.58,
      "regression_n": 41822,
      "pop_in_hotspots": 31240,
      "pop_total": 294630,
      "lst_by_landuse": {
        "water": 27.9,
        "forest": 31.2,
        "green_urban": 34.0,
        "residential_low": 39.1,
        "industrial": 47.6
      },
      "quality_flags": []
    }
  ]
}
```

**Verbindliche Konventionen**

- Schlüssel ist ausschließlich `municipality_slug`, identisch mit dem Slug aus `api.luftdaten.at`. Keine internen IDs, keine Namen.
- Alle Temperaturen in °C, alle Differenzen in K, alle Anteile in Prozent (0–100), niemals als Bruchteil.
- Fehlende Werte werden als `null` übergeben, **nicht** als `0`, `-999` oder ausgelassener Schlüssel.
- `quality_flags` ist immer vorhanden, notfalls als leere Liste. Die zulässigen Werte sind in [Abschnitt 2.2](#22-json-schema-im-repository) festgelegt.
- Gemeinden ohne auswertbares Ergebnis werden mit gesetztem Flag übergeben, nicht weggelassen — der Datahub muss unterscheiden können zwischen „nicht auswertbar" und „nicht geliefert".

### 2.2 JSON Schema im Repository

Das Format wird als JSON Schema im Datahub versioniert, damit beide Seiten dieselbe Referenz haben:

```
app/context/schemas/
├── heat_profiles.v1.schema.json
├── land_profiles.v1.schema.json
└── README.md          # Änderungspolitik, Kontakt
```

Das Schema definiert Pflichtfelder, Typen, Wertebereiche und die Enumeration der zulässigen `quality_flags`:

```json
{
  "quality_flags": {
    "type": "array",
    "items": {
      "enum": [
        "insufficient_clear_pixels",
        "no_rural_reference",
        "high_relief",
        "weak_regression",
        "substituted_date",
        "population_suppressed"
      ]
    }
  }
}
```

Ein unbekannter Flag-Wert führt zum Abbruch des Imports. Andernfalls würde das Frontend ihn stillschweigend ignorieren und eine Kennzahl anzeigen, die der Erzeuger als unbrauchbar markiert hat.

**Änderungspolitik:** `format_version` folgt Semantic Versioning. Der Datahub akzeptiert alle `1.x`-Versionen, lehnt `2.x` ab, bis das entsprechende Schema ergänzt wurde. Zusätzliche, dem Schema unbekannte Felder werden ignoriert, nicht abgelehnt — so kann der Erzeuger Felder ergänzen, ohne den Import zu brechen.

### 2.3 Drei Wege der Übergabe

Nach steigendem Automatisierungsgrad:

**(a) Dateiablage und Management Command — der Standardweg.**

Die Datei wird auf den Server kopiert (scp, rsync, Objektspeicher-Sync) und eingelesen:

```bash
./manage import_heat_profiles --file /data/in/heat_profiles_2026-06-29.json --dry-run
./manage import_heat_profiles --file /data/in/heat_profiles_2026-06-29.json
```

Kein zusätzlicher Code, keine offene Schnittstelle, volle Kontrolle. Für einen jährlichen Lauf völlig ausreichend und die empfohlene Variante.

**(b) Authentifizierter Upload-Endpunkt — für Automatisierung.**

Wenn die externe Berechnung selbst pushen soll:

```
POST /api/v1/context/imports/
Authorization: Bearer <CONTEXT_IMPORT_API_KEY>
Content-Type: multipart/form-data
```

Der Endpunkt legt die Datei in einer **Quarantäne** ab (`CONTEXT_IMPORT_INBOX`), validiert sie gegen das Schema und schreibt **nicht** direkt in die Datenbank. Er gibt einen Bericht zurück und legt einen `DatasetImport`-Datensatz mit Status `pending` an. Die tatsächliche Übernahme erfolgt durch eine bestätigende Aktion im Admin oder durch den Command mit `--accept <import-id>`.

Diese Trennung ist bewusst: Ein automatisierter Push darf nicht ohne menschliche Bestätigung die Zahlen ändern, die anschließend in Gemeinderatssitzungen zitiert werden.

Der Schlüssel folgt dem bestehenden Muster von `LUFTDATEN_ADMIN_API_KEY` in `settings.py`. Ist er nicht gesetzt, ist der Endpunkt deaktiviert und antwortet mit HTTP 503 — analog zum Verhalten der bestehenden City-Admin-Funktion.

**(c) Upload-Formular im Django-Admin — für gelegentliche manuelle Einspielung.**

Eine Seite unter `/backend/context/datasetimport/upload/` mit Dateifeld, die denselben Validierungs- und Quarantänepfad nutzt wie (b). Praktisch, wenn jemand ohne Serverzugang eine korrigierte Datei einspielen soll. Zugriff nur für Superuser.

Alle drei Wege laufen über **dieselbe** Funktion `context.imports.load_and_validate()`. Es gibt keinen zweiten Validierungspfad.

### 2.4 Warum die Validierung hier strenger sein muss

Bei einer intern erzeugten Datei kann man dem Produzenten vertrauen. Bei extern vorberechneten Daten nicht — nicht aus Misstrauen, sondern weil niemand mitbekommt, wenn sich auf der anderen Seite eine Einheit, ein Vorzeichen oder eine Klassenbenennung ändert.

Der Import prüft deshalb in dieser Reihenfolge und bricht bei der ersten Verletzung ab:

1. **Schema** — Pflichtfelder, Typen, Enumerationen
2. **Wertebereiche** — `lst_mean` zwischen −20 und 70, `clear_fraction` zwischen 0 und 1, `suhi_day` zwischen −10 und 20, Prozentwerte zwischen 0 und 100
3. **Referentielle Integrität** — jeder `municipality_slug` existiert lokal und hat `match_method != "unresolved"`
4. **Konsistenz** — `lst_p10 ≤ lst_mean ≤ lst_p90 ≤ lst_max`; `pop_in_hotspots ≤ pop_total`; `regression_n > 0`, wenn ein Koeffizient geliefert wird
5. **Plausibilität gegen den Vorlauf** — weicht `lst_mean` einer Gemeinde um mehr als 15 K vom letzten Import ab, wird der Import angehalten und der Fall gemeldet
6. **Vollständigkeit** — liefert die Datei für weniger als 50 % der auswertbaren Gemeinden Werte, wird gewarnt und eine Bestätigung mit `--force` verlangt

Prüfung 5 ist die wichtigste. Sie fängt genau die Fehlerklasse ab, die sonst unbemerkt durchgeht: eine Verwechslung von Kelvin und Celsius, ein vertauschtes Vorzeichen bei der Lapse Rate, ein falsch skaliertes Landsat-Band.

Der Validierungsbericht wird im `DatasetImport`-Datensatz gespeichert und ist im Admin einsehbar — auch bei erfolgreichem Import, damit Warnungen nachvollziehbar bleiben.

### 2.5 Kacheldatei

Die PMTiles-Datei wird nicht über die JSON-Schnittstelle transportiert (Größenordnung ein bis drei Gigabyte), sondern separat ins Kachel-Volume gelegt. Der Import-Command prüft lediglich, ob die im Manifest referenzierte Datei am erwarteten Ort vorhanden und lesbar ist:

```bash
./manage import_heat_profiles \
    --file /data/in/heat_profiles_2026-06-29.json \
    --expect-tiles /data/tiles/lst_2026-06-29.pmtiles
```

Fehlt sie, wird der Import nicht abgebrochen — die Kennzahlen sind auch ohne Karte nutzbar —, aber das Heat-Modul rendert dann ohne Kartenlayer und der Zustand steht im Importbericht.

## 3. Neue App `context`

```bash
docker compose exec app python manage.py startapp context
```

### 3.1 Verzeichnisstruktur

```
app/context/
├── __init__.py
├── apps.py
├── admin.py
├── models.py
├── migrations/
├── schemas/
│   ├── heat_profiles.v1.schema.json    # Vertrag mit dem externen Erzeuger
│   ├── land_profiles.v1.schema.json
│   └── README.md                       # Änderungspolitik, Kontakt
├── imports.py           # load_and_validate(), einziger Validierungspfad
├── management/
│   └── commands/
│       ├── sync_municipalities.py
│       ├── match_municipality_boundaries.py
│       ├── import_land_profiles.py
│       ├── import_heat_profiles.py
│       └── build_peer_groups.py
├── services.py          # Lesezugriffe für Views, gecacht
├── selectors.py         # Peer-Gruppen-Abfragen
└── tests/
    ├── test_models.py
    ├── test_imports.py
    ├── test_schema.py
    ├── test_matching.py
    └── fixtures/
        ├── heat_profiles_valid.json
        ├── heat_profiles_bad_units.json
        └── heat_profiles_unknown_flag.json
```

### 3.2 Modelle

`app/context/models.py`:

```python
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Municipality(models.Model):
    """Lokaler Spiegel der Gemeinden aus api.luftdaten.at, angereichert
    um Verwaltungsgrenze und Kennziffer."""

    slug = models.SlugField(max_length=128, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    country_code = models.CharField(max_length=2, default="AT")

    # Gemeindekennziffer der Statistik Austria (5-stellig)
    gkz = models.CharField(max_length=5, null=True, blank=True, db_index=True)

    centroid = gis_models.PointField(srid=4326, null=True, blank=True)
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)

    area_km2 = models.FloatField(null=True, blank=True)
    elevation_mean_m = models.FloatField(null=True, blank=True)
    elevation_range_m = models.FloatField(null=True, blank=True)
    population = models.IntegerField(null=True, blank=True)

    MATCH_AUTO = "auto"
    MATCH_MANUAL = "manual"
    MATCH_UNRESOLVED = "unresolved"
    MATCH_CHOICES = [
        (MATCH_AUTO, "Automatisch zugeordnet"),
        (MATCH_MANUAL, "Manuell bestätigt"),
        (MATCH_UNRESOLVED, "Offen"),
    ]
    match_method = models.CharField(
        max_length=16, choices=MATCH_CHOICES, default=MATCH_UNRESOLVED
    )
    match_confidence = models.FloatField(null=True, blank=True)

    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "municipalities"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @property
    def is_analysable(self):
        return self.boundary is not None and self.match_method != self.MATCH_UNRESOLVED


class PeerGroup(models.Model):
    """Cluster strukturell ähnlicher Gemeinden für faire Vergleiche."""

    key = models.SlugField(max_length=64, unique=True)
    label_de = models.CharField(max_length=120)
    label_en = models.CharField(max_length=120)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    def __str__(self):
        return self.label_de


class MunicipalityLandProfile(models.Model):
    """Modul 3 — statische Copernicus-Land-Indikatoren."""

    municipality = models.OneToOneField(
        Municipality, on_delete=models.CASCADE, related_name="land_profile"
    )
    peer_group = models.ForeignKey(
        PeerGroup, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members",
    )

    reference_year = models.PositiveSmallIntegerField()

    imperviousness_pct = models.FloatField(null=True)       # HRL IMD
    imperviousness_change_pp = models.FloatField(null=True)  # 2018 -> 2021
    tree_cover_pct = models.FloatField(null=True)            # HRL TCD
    landuse_shares = models.JSONField(default=dict)          # Urban Atlas / CLC+

    data_source = models.CharField(max_length=32)            # urban_atlas | clc_plus
    quality_flags = models.JSONField(default=list)
    imported_at = models.DateTimeField(auto_now=True)
    producer_version = models.CharField(max_length=32)


class MunicipalityHeatProfile(models.Model):
    """Modul 6 — LST-Indikatoren für einen Referenztag."""

    municipality = models.OneToOneField(
        Municipality, on_delete=models.CASCADE, related_name="heat_profile"
    )

    reference_date = models.DateField(db_index=True)
    acquisition_utc = models.DateTimeField()
    sensor = models.CharField(max_length=32)
    stac_item_id = models.CharField(max_length=160)
    clear_fraction = models.FloatField()

    lst_mean = models.FloatField(null=True)
    lst_p10 = models.FloatField(null=True)
    lst_p90 = models.FloatField(null=True)
    lst_max = models.FloatField(null=True)

    suhi_day = models.FloatField(null=True)
    suhi_night = models.FloatField(null=True)

    dlst_per_10pct_tcd = models.FloatField(null=True)
    dlst_per_10pct_imd = models.FloatField(null=True)
    regression_r2 = models.FloatField(null=True)
    regression_n = models.IntegerField(null=True)

    pop_in_hotspots = models.IntegerField(null=True)
    pop_total = models.IntegerField(null=True)

    lst_by_landuse = models.JSONField(default=dict)
    quality_flags = models.JSONField(default=list)

    imported_at = models.DateTimeField(auto_now=True)
    producer_version = models.CharField(max_length=32)

    class Meta:
        indexes = [models.Index(fields=["reference_date"])]


class DatasetImport(models.Model):
    """Protokoll einer Datenübernahme aus externer Vorberechnung."""

    STATUS_PENDING = "pending"       # validiert, wartet auf Bestätigung
    STATUS_ACCEPTED = "accepted"     # in die Profiltabellen übernommen
    STATUS_REJECTED = "rejected"     # Validierung fehlgeschlagen oder verworfen
    STATUS_CHOICES = [
        (STATUS_PENDING, "Wartet auf Bestätigung"),
        (STATUS_ACCEPTED, "Übernommen"),
        (STATUS_REJECTED, "Abgelehnt"),
    ]

    module = models.CharField(max_length=16)            # land | heat
    format_version = models.CharField(max_length=16)
    producer = models.CharField(max_length=120, blank=True)
    producer_version = models.CharField(max_length=32, blank=True)
    reference_date = models.DateField(null=True, blank=True)

    source_filename = models.CharField(max_length=255)
    source_sha256 = models.CharField(max_length=64, db_index=True)
    generated_utc = models.DateTimeField(null=True, blank=True)

    manifest = models.JSONField(default=dict)
    validation_report = models.JSONField(default=dict)

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    profiles_in_file = models.IntegerField(default=0)
    profiles_written = models.IntegerField(default=0)
    profiles_flagged = models.IntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="context_imports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "source_sha256"],
                name="context_import_unique_payload",
            ),
        ]

    def __str__(self):
        return f"{self.module} {self.reference_date or ''} ({self.status})"
```

### 3.3 Bewusste Entwurfsentscheidungen

- **`OneToOneField` statt Verlaufstabelle.** Es wird immer nur der aktuelle Referenztag angezeigt. Historische Übernahmen stehen im `DatasetImport`-Protokoll. Falls später ein Mehrjahresvergleich dazukommt, wird daraus ein `ForeignKey` mit `unique_together` auf `(municipality, reference_date)` — das ist eine überschaubare Migration.
- **`JSONField` für `landuse_shares` und `lst_by_landuse`.** Die Klassenanzahl unterscheidet sich zwischen Urban Atlas (19 Klassen) und CLC+. Eine normalisierte Tabelle wäre hier nur Ballast.
- **`quality_flags` als Liste.** Die Views entscheiden anhand dieser Flags, welche Kennzahlen sie ausblenden. Die Logik dazu gehört in `services.py`, nicht ins Template.
- **Kein Rasterfeld.** PostGIS Raster wird nicht verwendet. Rasterdaten liegen ausschließlich als PMTiles im Dateisystem.
- **`source_sha256` mit Unique-Constraint.** Verhindert, dass dieselbe Datei versehentlich zweimal übernommen wird, und macht im Nachhinein prüfbar, welche exakte Datei hinter den angezeigten Zahlen steht.
- **Zweistufiger Import (`pending` → `accepted`).** Extern erzeugte Daten werden erst validiert und protokolliert, dann übernommen. Das kostet einen zusätzlichen Handgriff und verhindert, dass ein fehlerhafter Lauf ohne Zwischenschritt live geht.

---

## 4. Der eigentliche Knackpunkt: Slug ↔ Gemeindekennziffer

Dieser Abschnitt beschreibt den Arbeitsschritt, der erfahrungsgemäß unterschätzt wird.

### 4.1 Das Problem

`/city/all` liefert laut `_normalize_cities_from_api` in `municipalities/views.py` nur:

```json
{"id": ..., "name": "Wien", "slug": "wien",
 "country": {"name": "Austria", "slug": "austria"},
 "location": {"latitude": 48.21, "longitude": 16.37}}
```

Keine Gemeindekennziffer, kein NUTS-Code, keine Grenze. Die Verwaltungsgrenzen der Statistik Austria sind dagegen über die 5-stellige GKZ geschlüsselt. Ohne belastbare Zuordnung `slug → GKZ` gibt es keine Zonal Statistics.

Erschwerend:

- Gleichnamige Gemeinden (Neustift, Sankt Georgen, Weißenbach kommen mehrfach vor)
- Schreibvarianten: `St.` / `Sankt`, `a. d.` / `an der`, Umlaut-Transliteration im Slug
- Wien ist eine Gemeinde, wird aber möglicherweise mit Bezirken geführt
- Gemeindezusammenlegungen — die steirische Strukturreform 2015 hat Kennziffern verändert; der Gebietsstand des verwendeten Grenzdatensatzes muss dokumentiert sein
- Der Punkt aus `/city/all` ist redaktionell gepflegt (es gibt sogar eine Admin-Oberfläche dafür) und kann außerhalb der tatsächlichen Gemeindegrenze liegen

### 4.2 Verfahren

Dreistufig, mit Konfidenzbewertung:

**Stufe 1 — Punkt in Polygon.** Zentroid aus `/city/all` gegen die Gemeindepolygone. Treffer eindeutig → `match_confidence = 1.0`.

**Stufe 2 — Namensabgleich.** Für die Fälle ohne Polygontreffer: normalisierter Name (Kleinschreibung, Umlaute aufgelöst, `Sankt` → `st`, Interpunktion entfernt) gegen den Gemeindenamen. Bei genau einem Treffer und einer Distanz zum Polygonzentroid unter 5 km → `match_confidence = 0.8`.

**Stufe 3 — Manuelle Nachkontrolle.** Alles Übrige landet mit `match_method = "unresolved"` in einer Admin-Liste. Realistische Größenordnung: einige Dutzend Fälle bei rund 2.000 Gemeinden.

Wichtig: **Automatisch zugeordnete Gemeinden mit `match_confidence < 1.0` werden nicht stillschweigend als korrekt behandelt.** Sie werden in der Admin-Liste zur Bestätigung angezeigt und erst durch die Bestätigung auf `match_method = "manual"` gesetzt.

```python
# app/context/management/commands/match_municipality_boundaries.py (Auszug)

for city in cities:
    pt = Point(city["longitude"], city["latitude"], srid=4326)
    hits = Boundary.objects.filter(geom__contains=pt)

    if hits.count() == 1:
        assign(city, hits.first(), method=Municipality.MATCH_AUTO, confidence=1.0)
        continue

    candidates = Boundary.objects.filter(name_normalized=normalize(city["name"]))
    if candidates.count() == 1 and candidates.first().geom.centroid.distance(pt) < 0.05:
        assign(city, candidates.first(), method=Municipality.MATCH_AUTO, confidence=0.8)
        continue

    mark_unresolved(city, candidates=list(candidates[:5]))
```

### 4.3 Empfehlung mit Blick nach vorn

Mittelfristig sollte `api.luftdaten.at` das GKZ-Feld selbst führen — die Gemeinde ist dort ohnehin ein redaktionell gepflegtes Objekt mit Admin-Endpunkt (`POST /city/admin`). Ein zusätzliches optionales Feld `gkz` in der City-Ressource würde diesen gesamten Matching-Schritt dauerhaft überflüssig machen. Bis dahin bleibt die Zuordnungstabelle im Datahub die Quelle der Wahrheit, und der Matching-Command ist idempotent, damit neue Gemeinden nachlaufen können.

---

## 5. Änderungen an bestehenden Dateien

| Datei | Änderung | Aufwand |
|---|---|---|
| `app/main/settings.py` | `context.apps.ContextConfig` in `INSTALLED_APPS`; neue Konstanten; `CACHES` auf Redis | klein |
| `app/main/urls.py` | keine Änderung nötig — `context` hat keine eigenen URLs | — |
| `app/municipalities/views.py` | `municipality_detail_view` um Profile erweitern; Stationsliste auf Bounding Box filtern | mittel |
| `app/municipalities/urls.py` | keine Änderung | — |
| `app/templates/municipalities/detail.html` | Aufteilung in Partials, Tab-Struktur, neue Blöcke | groß |
| `app/templates/municipalities/list.html` | Peer-Gruppen-Filter, Sortierung nach Indikatoren | mittel |
| `app/api/urls/v1.py` | neue Routen für Gemeindeindikatoren | klein |
| `app/api/serializers/` | neue Datei `context.py` | klein |
| `app/static/js/` | `pmtiles.js`, `leaflet-pmtiles.js` vendoren | klein |
| `app/locale/de/LC_MESSAGES/django.po` | neue Übersetzungen | klein |
| `requirements.in` | `jsonschema` und `django-redis` ergänzen — **keine Geo-Pakete** | klein |
| `nginx/nginx.conf` | `location /tiles/` mit Range-Support | klein |
| `docker-compose.yml` / `.prod.yml` | Redis, Tiles-Volume, Inbox-Volume | klein |
| `Dockerfile` | **unverändert** | — |

### 5.1 Neue Settings-Konstanten

Anzuhängen an `app/main/settings.py`, im Stil der bestehenden GeoSphere-Konstanten:

```python
# --- Kontextmodule (Copernicus Land, Oberflächentemperatur) -----------------

# Ablage für extern vorberechnete Artefakte (Quarantäne vor der Übernahme).
CONTEXT_IMPORT_INBOX = env("CONTEXT_IMPORT_INBOX", default="/data/in")

# Verzeichnis der ausgelieferten Kacheldateien (nur lesend).
CONTEXT_TILES_DIR = env("CONTEXT_TILES_DIR", default="/data/tiles")

# Öffentlicher Pfad, unter dem nginx die PMTiles ausliefert.
CONTEXT_TILES_URL = env("CONTEXT_TILES_URL", default="/tiles/")

# Bearer-Token für den Upload-Endpunkt. Leer = Endpunkt deaktiviert (HTTP 503),
# analog zum Verhalten von LUFTDATEN_ADMIN_API_KEY.
CONTEXT_IMPORT_API_KEY = env("CONTEXT_IMPORT_API_KEY", default="")

# Akzeptierte Formatversionen der eingehenden Artefakte.
CONTEXT_ACCEPTED_FORMAT_VERSIONS = ["1.0", "1.1"]

# Schwellen der Importprüfung.
CONTEXT_IMPORT_MAX_LST_DELTA_K = 15.0      # Abweichung zum Vorimport
CONTEXT_IMPORT_MIN_COVERAGE = 0.50         # Anteil gelieferter Gemeinden

# Referenztag der aktuell ausgelieferten LST-Auswertung.
CONTEXT_HEAT_REFERENCE_DATE = env("CONTEXT_HEAT_REFERENCE_DATE", default="2026-06-29")

# Feste Farbskala der LST-Karte (°C). Bewusst nicht je Gemeinde gestreckt.
CONTEXT_LST_SCALE_MIN = 20.0
CONTEXT_LST_SCALE_MAX = 55.0

# Mindestqualität, ab der Kennzahlen angezeigt werden.
CONTEXT_MIN_CLEAR_FRACTION = 0.95
CONTEXT_MIN_REGRESSION_R2 = 0.30

CONTEXT_PROFILE_CACHE_TTL = 3600
```

Und der fehlende Cache-Block:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/1"),
    }
}
```

---

## 6. `municipalities/views.py` im Detail

### 6.1 Detailansicht erweitern

Die bestehende `municipality_detail_view` bleibt in ihrer Struktur erhalten. Ergänzt wird ein Lookup auf die lokalen Profile, der **nie** dazu führen darf, dass die Seite bricht, wenn kein Profil existiert.

```python
from context.services import get_municipality_context


def municipality_detail_view(request, pk):
    municipality_slug = str(pk).strip()

    # ... bestehender Block: /city/current abrufen, municipality_info bauen ...

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = FavoriteMunicipality.objects.filter(
            user=request.user, municipality_slug=municipality_slug
        ).exists()

    # NEU: lokale Kontextdaten, tolerant gegenüber fehlenden Profilen
    ctx = get_municipality_context(municipality_slug)

    return render(
        request,
        "municipalities/detail.html",
        {
            "municipality": municipality_info,
            "municipality_slug": municipality_slug,
            "is_favorite": is_favorite,
            "land_profile": ctx.land,       # None, wenn nicht vorhanden
            "heat_profile": ctx.heat,       # None, wenn nicht vorhanden
            "peer_group": ctx.peer_group,
            "boundary_geojson": ctx.boundary_geojson,
            "bbox": ctx.bbox,
            "tiles_url": ctx.tiles_url,
            "heat_visible": ctx.heat_visible,
        },
    )
```

### 6.2 `context/services.py`

Die gesamte Logik, welche Kennzahl bei welchem Flag ausgeblendet wird, gehört hierher — nicht ins Template und nicht in die View.

```python
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache

from .models import Municipality


@dataclass
class MunicipalityContext:
    land: object | None = None
    heat: object | None = None
    peer_group: object | None = None
    boundary_geojson: str | None = None
    bbox: list | None = None
    tiles_url: str | None = None
    heat_visible: bool = False


def get_municipality_context(slug: str) -> MunicipalityContext:
    cache_key = f"context_profile_{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        m = (
            Municipality.objects
            .select_related("land_profile", "land_profile__peer_group", "heat_profile")
            .get(slug=slug)
        )
    except Municipality.DoesNotExist:
        return MunicipalityContext()

    heat = getattr(m, "heat_profile", None)
    heat_visible = bool(
        heat
        and heat.clear_fraction >= settings.CONTEXT_MIN_CLEAR_FRACTION
        and "insufficient_clear_pixels" not in heat.quality_flags
    )

    ctx = MunicipalityContext(
        land=getattr(m, "land_profile", None),
        heat=heat if heat_visible else None,
        peer_group=getattr(getattr(m, "land_profile", None), "peer_group", None),
        boundary_geojson=m.boundary.geojson if m.boundary else None,
        bbox=list(m.boundary.extent) if m.boundary else None,
        tiles_url=settings.CONTEXT_TILES_URL,
        heat_visible=heat_visible,
    )
    cache.set(cache_key, ctx, settings.CONTEXT_PROFILE_CACHE_TTL)
    return ctx
```

**Wichtig zur Ausblendlogik:** Ein `weak_regression`-Flag darf nicht das ganze Heat-Modul verstecken, sondern nur den Regressionskoeffizienten. Entsprechend liefert `services.py` zusätzlich eine Methode `visible_metrics(heat)`, die je Kennzahl `True`/`False` zurückgibt. Das Template fragt diese ab statt selbst Flags zu interpretieren.

### 6.3 Stationsfilterung — Fehlerbehebung

Aktuell lädt `detail.html` über `${api_url}/station/current/all` **alle** österreichischen Stationen und rendert sie in die Gemeindekarte. Das ist sowohl inhaltlich falsch als auch unnötig teuer.

Mit vorhandener Grenzgeometrie lässt sich clientseitig auf die Bounding Box filtern:

```javascript
const BBOX = {{ bbox|safe }};   // [minx, miny, maxx, maxy], null wenn keine Grenze

function inBbox(lat, lon) {
    if (!BBOX) return true;     // Fallback: bisheriges Verhalten
    return lon >= BBOX[0] && lon <= BBOX[2] && lat >= BBOX[1] && lat <= BBOX[3];
}
```

Sauberer wäre ein serverseitiger Filter über `api.luftdaten.at` (`/station/all?city_slug=...`). Falls dieser Endpunkt ergänzt werden kann, sollte er dem Bounding-Box-Filter vorgezogen werden.

Zusätzlich ersetzt `map.fitBounds()` auf die Grenzgeometrie das hartcodierte `setView(..., 13)`.

---

## 7. Templates

### 7.1 `detail.html` muss aufgeteilt werden

Die Datei hat aktuell 298 Zeilen, davon rund 180 Zeilen inline JavaScript im `{% block content %}`. Mit vier zusätzlichen Diagrammen, einer Swipe-Karte und einem Kachel-Layer wird sie unwartbar. Vor der Erweiterung deshalb aufteilen:

```
app/templates/municipalities/
├── detail.html                     # Gerüst, Tab-Navigation
└── partials/
    ├── _header.html                # Name, Favoriten-Button, Kennzahl-Header
    ├── _tab_current.html           # bestehende 1h-Mittelwerte
    ├── _tab_history.html           # Modul 1: Verlauf, Tagesgang
    ├── _tab_environment.html       # Modul 3: Versiegelung, Baumkronen, Flächennutzung
    ├── _tab_heat.html              # Modul 6: LST
    ├── _tab_stations.html          # Stationsliste
    ├── _tab_data.html              # Export, Lizenz, Methodik
    ├── _map_legend.html            # bestehende Legende
    └── _quality_note.html          # Flags, Hinweise
```

Das JavaScript wandert nach `app/static/js/municipality-detail.js` und `municipality-heat.js`, eingebunden über `{% block extra_js %}` — dieser Block existiert bereits in `_base.html` (Zeile 140).

Parameter werden über `json_script` übergeben, nicht per String-Interpolation ins JS:

```django
{{ heat_config|json_script:"heat-config" }}
```

```javascript
const cfg = JSON.parse(document.getElementById("heat-config").textContent);
```

### 7.2 Neuer Tab „Hitze"

`_tab_heat.html` in Kurzform:

```django
{% load i18n %}

{% if heat_visible %}
<div class="row">
  <div class="col-12">
    <p class="text-muted small">
      {% blocktrans with d=heat.reference_date t=heat.acquisition_local s=heat.sensor %}
      Aufnahme vom {{ d }}, {{ t }} Uhr, {{ s }}.
      {% endblocktrans %}
    </p>
  </div>
</div>

{% include "municipalities/partials/_heat_swipe_map.html" %}

<div class="row mt-4">
  {% if metrics.suhi_day %}
    {% include "municipalities/partials/_metric_card.html" with
       label=_("Wärmeinsel tagsüber") value=heat.suhi_day unit="K" %}
  {% endif %}
  {% if metrics.suhi_night %}
    {% include "municipalities/partials/_metric_card.html" with
       label=_("Wärmeinsel nachts") value=heat.suhi_night unit="K" %}
  {% endif %}
  {% include "municipalities/partials/_metric_card.html" with
     label=_("Temperaturspreizung") value=heat.lst_range unit="K" %}
</div>

{% if metrics.cooling_regression %}
<div class="row mt-4">
  <div class="col-lg-6"><canvas id="heat-tcd-scatter"></canvas></div>
  <div class="col-lg-6"><canvas id="heat-landuse-bars"></canvas></div>
</div>
{% endif %}

{% include "municipalities/partials/_heat_disclaimer.html" %}

{% else %}
<div class="alert alert-light border">
  {% trans "Für diese Gemeinde liegt keine auswertbare Satellitenaufnahme vor." %}
</div>
{% endif %}
```

### 7.3 Die Methodik-Box ist nicht optional

`_heat_disclaimer.html` ist ausgeklappt darzustellen, nicht in ein Accordion versteckt. Sie enthält die drei Kernaussagen: Oberflächentemperatur ist nicht Lufttemperatur, die Aufnahme stammt vom Vormittag, ein einzelner Tag ist eine Momentaufnahme. Ohne diesen Kontext ist die Karte irreführend.

### 7.4 Internationalisierung

Der bestehende Absatz „Es gibt {{ municipality.station_count }} Citizen Science Stationen …" in `detail.html` ist hartcodiert deutsch und nicht in `{% trans %}` gefasst. Das gehört im Zuge der Umstrukturierung mit erledigt. Anschließend:

```bash
docker compose exec app python manage.py makemessages -l de
docker compose exec app python manage.py compilemessages
```

---

## 8. API-Erweiterung

Die Indikatoren sollen unter CC BY 4.0 offen abrufbar sein. Einbindung nach dem bestehenden Muster in `api/urls/v1.py`.

### 8.1 Serializer

Neue Datei `app/api/serializers/context.py`:

```python
from rest_framework import serializers

from context.models import MunicipalityHeatProfile, MunicipalityLandProfile


class MunicipalityLandProfileSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="municipality.slug", read_only=True)
    name = serializers.CharField(source="municipality.name", read_only=True)
    peer_group = serializers.CharField(source="peer_group.key", read_only=True)

    class Meta:
        model = MunicipalityLandProfile
        fields = [
            "slug", "name", "peer_group", "reference_year",
            "imperviousness_pct", "imperviousness_change_pp",
            "tree_cover_pct", "landuse_shares",
            "data_source", "quality_flags",
        ]


class MunicipalityHeatProfileSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="municipality.slug", read_only=True)
    name = serializers.CharField(source="municipality.name", read_only=True)

    class Meta:
        model = MunicipalityHeatProfile
        fields = [
            "slug", "name", "reference_date", "acquisition_utc", "sensor",
            "stac_item_id", "clear_fraction",
            "lst_mean", "lst_p10", "lst_p90", "lst_max",
            "suhi_day", "suhi_night",
            "dlst_per_10pct_tcd", "dlst_per_10pct_imd",
            "regression_r2", "regression_n",
            "pop_in_hotspots", "pop_total",
            "lst_by_landuse", "quality_flags",
        ]
```

### 8.2 Routen

| Pfad | Rückgabe |
|---|---|
| `GET /api/v1/municipalities/{slug}/land/` | Copernicus-Land-Indikatoren |
| `GET /api/v1/municipalities/{slug}/heat/` | LST-Indikatoren |
| `GET /api/v1/municipalities/heat/?format=csv` | alle Gemeinden als CSV |
| `GET /api/v1/municipalities/{slug}/boundary/` | Grenze als GeoJSON |

Zusätzlich, nur für die Datenübernahme und nicht öffentlich:

| Pfad | Zweck | Auth |
|---|---|---|
| `POST /api/v1/context/imports/` | Artefakt hochladen, validieren, in Quarantäne legen | Bearer `CONTEXT_IMPORT_API_KEY` |
| `GET /api/v1/context/imports/{id}/` | Validierungsbericht abrufen | Bearer |

Der Upload-Endpunkt übernimmt **nicht** direkt in die Profiltabellen — er legt einen `DatasetImport` im Status `pending` an und antwortet mit dem Bericht. Die Bestätigung erfolgt separat über Admin oder `accept_import`. Ohne gesetzten Schlüssel antworten beide Routen mit HTTP 503, analog zum Verhalten der bestehenden City-Admin-Funktion.

Beide Routen werden über `@extend_schema(exclude=True)` aus dem öffentlichen Schema ausgenommen.

`drf_spectacular` ist bereits konfiguriert; mit `@extend_schema` dokumentieren sich die Endpunkte automatisch unter `/api/v1/docs/`.

**Lizenzhinweis im Response.** Jede Antwort trägt ein `attribution`-Feld mit den Pflichtangaben (Copernicus, USGS, GeoSphere, Statistik Austria). Bei den Copernicus-Land-Produkten verlangt die Lizenz ausdrücklich die Kennzeichnung, dass die Daten abgeleitet wurden — ein reiner Quellenverweis genügt nicht.

---

## 9. Management Commands

| Command | Zweck | Turnus |
|---|---|---|
| `sync_municipalities` | `/city/all` in die lokale `Municipality`-Tabelle spiegeln | täglich (Cron) |
| `match_municipality_boundaries` | Slug ↔ GKZ zuordnen, Grenzen laden | einmalig, dann bei neuen Gemeinden |
| `import_land_profiles` | `land_profiles_*.json` prüfen und übernehmen | bei neuem CLMS-Release |
| `import_heat_profiles` | `heat_profiles_*.json` prüfen und übernehmen | jährlich |
| `list_imports` | offene und vergangene Übernahmen anzeigen | bei Bedarf |
| `accept_import` | wartende Übernahme bestätigen | nach Prüfung |
| `build_peer_groups` | Clustering, Zuordnung der Gemeinden | nach `import_land_profiles` |

### 9.1 Gemeinsame Import-Logik

Alle Wege aus [Abschnitt 2.3](#23-drei-wege-der-übergabe) rufen dieselbe Funktion auf. Es gibt keinen zweiten Validierungspfad — weder für den Upload-Endpunkt noch für das Admin-Formular.

```python
# app/context/imports.py

@dataclass
class ImportResult:
    dataset_import: DatasetImport
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_and_validate(
    raw: bytes,
    *,
    module: str,
    filename: str,
    user=None,
) -> ImportResult:
    """Prüft ein Artefakt und legt einen DatasetImport im Status
    'pending' an. Schreibt nichts in die Profiltabellen."""


def accept(dataset_import: DatasetImport) -> ImportResult:
    """Übernimmt einen validierten DatasetImport in die Profiltabellen.
    Transaktional, idempotent, invalidiert den Cache."""
```

### 9.2 Anforderungen an den Import

- **Idempotent.** Zweimaliges Übernehmen derselben Datei ist wirkungslos; der Unique-Constraint auf `(module, source_sha256)` verhindert Dubletten.
- **Transaktional.** `@transaction.atomic` über die gesamte Übernahme. Ein Fehler bei Gemeinde 1.700 darf keinen Mischzustand aus 1.699 neuen und 394 alten Werten hinterlassen.
- **`--dry-run`.** Validiert und gibt den vollständigen Bericht aus, ohne zu schreiben.
- **Vollständige Prüfkette** nach [Abschnitt 2.4](#24-warum-die-validierung-hier-strenger-sein-muss), inklusive Vergleich gegen den vorangegangenen Import.
- **Cache-Invalidierung** der betroffenen `context_profile_*`-Keys nach erfolgreicher Übernahme.
- **`DatasetImport`-Eintrag** mit Manifest, Prüfsumme und vollständigem Validierungsbericht — auch bei Ablehnung, damit nachvollziehbar bleibt, warum eine Lieferung nicht angekommen ist.

```python
class Command(BaseCommand):
    help = "Prüft und übernimmt extern vorberechnete Heat-Profile."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
        parser.add_argument("--expect-tiles", default=None)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true",
                            help="Übernimmt trotz Warnungen (z. B. geringe Abdeckung).")

    def handle(self, *args, **options):
        path = Path(options["file"])
        result = load_and_validate(
            path.read_bytes(), module="heat", filename=path.name
        )

        for w in result.warnings:
            self.stdout.write(self.style.WARNING(f"WARN  {w}"))
        for e in result.errors:
            self.stdout.write(self.style.ERROR(f"ERROR {e}"))

        if not result.ok:
            raise CommandError(
                f"{len(result.errors)} Fehler — nichts übernommen. "
                f"Bericht: DatasetImport #{result.dataset_import.pk}"
            )

        if result.warnings and not options["force"]:
            raise CommandError("Warnungen vorhanden. Mit --force übernehmen.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"{result.dataset_import.profiles_in_file} Profile würden übernommen."
            ))
            return

        accepted = accept(result.dataset_import)
        self.stdout.write(self.style.SUCCESS(
            f"{accepted.dataset_import.profiles_written} Profile übernommen."
        ))
```

### 9.3 Berichtsformat

Der Validierungsbericht wird strukturiert abgelegt, nicht als Freitext — er soll im Admin filterbar und maschinell auswertbar sein:

```json
{
  "checked_at": "2026-09-15T09:02:11Z",
  "schema_version": "1.0",
  "counts": {
    "profiles_in_file": 1847,
    "slugs_unknown": 3,
    "slugs_unmatched": 12,
    "out_of_range": 0,
    "inconsistent": 1,
    "delta_exceeded": 2
  },
  "errors": [
    "graz: lst_p90 (46.7) < lst_mean (48.1)"
  ],
  "warnings": [
    "wien: lst_mean weicht um 16.2 K vom Import 2025-07-14 ab",
    "3 unbekannte Slugs übersprungen: sankt-georgen-x, ..."
  ]
}
```

## 10. Kachelauslieferung und nginx

### 10.1 PMTiles gehören nicht in `staticfiles`

Die Kacheldatei liegt im Bereich von ein bis drei Gigabyte. Sie durch `collectstatic` zu schleusen und ins Image zu packen wäre falsch. Stattdessen ein eigenes Volume.

`docker-compose.prod.yml`:

```yaml
  app:
    volumes:
      - tiles_volume:/data/tiles:ro
  nginx:
    volumes:
      - tiles_volume:/home/app/web/tiles:ro

volumes:
  tiles_volume:
  inbox_volume:
```

Die Kacheldatei wird zusammen mit den JSON-Artefakten von außen bereitgestellt — per `scp`/`rsync` in das Volume oder durch Sync aus einem Objektspeicher. Der Datahub erzeugt sie nicht und verändert sie nicht; er liest sie nur.

Der Import-Command prüft über `--expect-tiles` lediglich Vorhandensein und Lesbarkeit der im Manifest referenzierten Datei und vermerkt das Ergebnis im Bericht. Fehlt die Datei, bleiben die Kennzahlen nutzbar, das Kartenmodul rendert ohne Layer.

**Aufbewahrung:** Alte Kacheldateien werden nicht automatisch gelöscht. Da der Dateiname den Referenztag enthält, können mehrere Jahrgänge nebeneinander liegen; welcher ausgeliefert wird, steuert `CONTEXT_HEAT_REFERENCE_DATE`. Das erlaubt einen Rollback auf den Vorjahresstand ohne erneute Datenübernahme.

### 10.2 nginx-Konfiguration

PMTiles funktioniert über HTTP-Range-Requests. nginx unterstützt diese für statische Dateien von Haus aus; wichtig sind lediglich CORS-Header und ein deaktiviertes Gzip (Range-Requests auf komprimierte Antworten funktionieren nicht zuverlässig).

Ergänzung in `nginx/nginx.conf`:

```nginx
    location /tiles/ {
        alias /home/app/web/tiles/;

        add_header Access-Control-Allow-Origin  "*";
        add_header Access-Control-Allow-Headers "Range";
        add_header Access-Control-Expose-Headers "Content-Range, Content-Length";

        gzip off;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
```

Der Dateiname enthält den Referenztag (`lst_2026-06-29.pmtiles`), sodass `immutable` unproblematisch ist — ein neuer Lauf erzeugt einen neuen Namen.

### 10.3 Clientseitige Einbindung

```bash
# vendoren, nicht per CDN einbinden
curl -o app/static/js/pmtiles.js https://.../pmtiles@3/dist/pmtiles.js
curl -o app/static/js/leaflet-pmtiles.js https://.../protomaps-leaflet/dist/...
```

```javascript
const p = new pmtiles.PMTiles(`${cfg.tilesUrl}lst_${cfg.referenceDate}.pmtiles`);
const layer = pmtiles.leafletRasterLayer(p, { opacity: 0.8, maxZoom: 16 });
```

---

## 11. Django-Admin

`app/context/admin.py`:

```python
@admin.register(Municipality)
class MunicipalityAdmin(gis_admin.GISModelAdmin):
    list_display = ("name", "slug", "gkz", "match_method",
                    "match_confidence", "has_boundary")
    list_filter = ("match_method", "country_code")
    search_fields = ("name", "slug", "gkz")
    actions = ["confirm_match"]

    @admin.display(boolean=True)
    def has_boundary(self, obj):
        return obj.boundary is not None

    @admin.action(description="Zuordnung als manuell bestätigt markieren")
    def confirm_match(self, request, queryset):
        queryset.update(match_method=Municipality.MATCH_MANUAL)
```

Die `confirm_match`-Aktion ist der Arbeitsplatz für die Nachkontrolle aus [Abschnitt 4](#4-der-eigentliche-knackpunkt-slug--gemeindekennziffer). Der Standardfilter der Liste sollte auf `match_method = unresolved` stehen.

Die Profilmodelle werden **schreibgeschützt** registriert (`has_add_permission` und `has_change_permission` liefern `False`). Sie werden ausschließlich über den Import befüllt; manuelle Änderungen im Admin würden die Nachvollziehbarkeit zerstören, die das `DatasetImport`-Protokoll herstellen soll.

### 11.1 Übernahmen verwalten

`DatasetImport` ist der Arbeitsplatz für die Datenübernahme:

```python
@admin.register(DatasetImport)
class DatasetImportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "module", "reference_date", "status",
                    "profiles_in_file", "profiles_written", "error_count")
    list_filter = ("module", "status")
    readonly_fields = ("source_sha256", "manifest", "validation_report",
                       "profiles_in_file", "profiles_written", "accepted_at")
    actions = ["accept_selected", "reject_selected"]
    change_list_template = "admin/context/datasetimport/change_list.html"

    @admin.display(description="Fehler")
    def error_count(self, obj):
        return len(obj.validation_report.get("errors", []))

    @admin.action(description="Ausgewählte Übernahmen bestätigen")
    def accept_selected(self, request, queryset):
        for imp in queryset.filter(status=DatasetImport.STATUS_PENDING):
            result = accept(imp)
            level = messages.SUCCESS if result.ok else messages.ERROR
            self.message_user(request, str(imp), level=level)
```

Das überschriebene `change_list_template` bindet das Upload-Formular aus [Abschnitt 2.3 (c)](#23-drei-wege-der-übergabe) ein — ein einzelnes Dateifeld über der Liste, das denselben Validierungspfad nutzt.

Der Validierungsbericht wird als formatiertes JSON im Detailformular angezeigt, damit Warnungen vor der Bestätigung tatsächlich gelesen werden können.

`auditlog` ist im Projekt bereits aktiv — `Municipality` und `DatasetImport` sollten dort registriert werden, damit manuelle Zuordnungskorrekturen und Bestätigungen protokolliert sind.

---

## 12. Tests

Das Projekt hat mit `municipalities/tests.py` (323 Zeilen) bereits eine ordentliche Testbasis. Neue Tests im gleichen Stil:

| Test | Prüft |
|---|---|
| `test_matching_point_in_polygon` | eindeutiger Polygontreffer → `confidence 1.0` |
| `test_matching_ambiguous_name` | gleichnamige Gemeinden → `unresolved` |
| `test_schema_valid_fixture` | Beispieldatei validiert gegen das Schema |
| `test_schema_rejects_unknown_flag` | unbekannter `quality_flag` bricht ab |
| `test_schema_ignores_extra_fields` | unbekanntes Zusatzfeld bricht **nicht** ab |
| `test_import_rejects_format_version` | `format_version: 2.0` wird abgelehnt |
| `test_import_rejects_out_of_range` | `lst_mean = 200` bricht ab |
| `test_import_rejects_inconsistent` | `lst_p90 < lst_mean` bricht ab |
| `test_import_warns_on_large_delta` | 16 K Abweichung zum Vorimport erzeugt Warnung |
| `test_import_requires_force_on_warning` | Warnung ohne `--force` schreibt nichts |
| `test_import_idempotent` | zweite Übernahme derselben Datei ändert nichts |
| `test_import_rollback_on_error` | Abbruch hinterlässt keinen Teilzustand |
| `test_import_pending_then_accept` | Upload schreibt erst bei Bestätigung |
| `test_upload_endpoint_without_key` | HTTP 503, wenn Schlüssel nicht gesetzt |
| `test_detail_view_without_profile` | Seite rendert ohne Profil, HTTP 200 |
| `test_detail_view_hides_flagged_metric` | `weak_regression` blendet nur den Koeffizienten aus |
| `test_detail_view_low_clear_fraction` | Heat-Tab wird nicht gerendert |
| `test_api_heat_endpoint` | Schema und Lizenzfeld |
| `test_bbox_filter` | Stationen außerhalb der Box fehlen |

Für die Geometrietests reichen synthetische Polygone in den Fixtures; echte Gemeindegrenzen gehören nicht ins Repository.

Die drei Fixture-Dateien unter `context/tests/fixtures/` sind gleichzeitig **die ausführbare Dokumentation des Übergabeformats**. Wer extern Daten erzeugt, kann sie als Vorlage nehmen, und jede Änderung am Format wird durch einen fehlschlagenden Test sichtbar. Sie sollten daher klein bleiben — drei bis fünf Gemeinden genügen.

---

## 13. Migrationen und Deployment-Reihenfolge

```bash
# 1 – Modelle anlegen
docker compose exec app python manage.py makemigrations context
docker compose exec app python manage.py migrate

# 2 – Gemeinden spiegeln
./manage sync_municipalities

# 3 – Grenzen zuordnen (Grenzdatensatz muss vorliegen)
./manage match_municipality_boundaries --boundaries /data/in/gemeinden_2026.gpkg
#    -> danach im Admin die unresolved-Fälle abarbeiten

# 4 – extern vorberechnete Artefakte bereitstellen
#    (erfolgt außerhalb des Datahub – scp, rsync oder Objektspeicher-Sync)
scp land_profiles_v1.json   server:/data/in/
scp heat_profiles_2026-06-29.json server:/data/in/
scp lst_2026-06-29.pmtiles  server:/data/tiles/

# 5 – Artefakte prüfen und übernehmen
./manage import_land_profiles --file /data/in/land_profiles_v1.json --dry-run
./manage import_land_profiles --file /data/in/land_profiles_v1.json
./manage build_peer_groups

./manage import_heat_profiles --file /data/in/heat_profiles_2026-06-29.json \
        --expect-tiles /data/tiles/lst_2026-06-29.pmtiles --dry-run
./manage import_heat_profiles --file /data/in/heat_profiles_2026-06-29.json \
        --expect-tiles /data/tiles/lst_2026-06-29.pmtiles

# 6 – Referenztag scharfschalten
#    CONTEXT_HEAT_REFERENCE_DATE=2026-06-29 in .env setzen, dann
docker compose -f docker-compose.prod.yml up -d app

# 7 – Übersetzungen und statische Dateien
./manage makemessages -l de && ./manage compilemessages
./manage collectstatic --noinput
```

Schritt 3 ist die einzige Stelle mit nennenswertem manuellem Aufwand. Sie fällt einmalig an und danach nur noch bei Gemeindeneuanlagen.

Schritt 6 ist bewusst getrennt: Die Daten liegen nach Schritt 5 bereits in der Datenbank, werden aber erst angezeigt, wenn der Referenztag umgestellt ist. So lässt sich ein Import in Ruhe im Admin prüfen, bevor er öffentlich sichtbar wird, und im Fehlerfall genügt das Zurücksetzen einer Umgebungsvariablen.

---

## 14. Vorarbeiten, die ohnehin fällig sind

Diese Punkte sind unabhängig von den neuen Modulen sinnvoll und erleichtern deren Umsetzung erheblich:

| Punkt | Datei | Begründung |
|---|---|---|
| Absatz „Es gibt … Stationen" in `{% trans %}` fassen | `detail.html` | hartcodiertes Deutsch bricht die englische Version |
| `value.dimension in "PM1.0,PM2.5,PM10.0"` ersetzen | `detail.html` | Substring-Test statt Listen-Test; ein Dimensionsname `PM1.0,PM2.5` würde durchfallen |
| Inline-JS nach `static/js/` auslagern | `detail.html` | Voraussetzung für die Tab-Struktur |
| `CACHES` konfigurieren | `settings.py` | `LocMemCache` ist pro Gunicorn-Worker; Invalidierung greift derzeit nur teilweise |
| Stationsabruf auf die Gemeinde begrenzen | `detail.html` | lädt aktuell alle Stationen Österreichs in jede Gemeindekarte |
| `fitBounds` statt `setView(..., 13)` | `detail.html` | fester Zoom passt weder für Wien noch für eine Streusiedlung |

Der vierte Punkt betrifft auch die bestehenden GeoSphere-Proxies und sollte unabhängig priorisiert werden.

---

## 15. Reihenfolge und Aufwand

| Phase | Inhalt | Aufwand | Ergebnis |
|---|---|---|---|
| 0 | Vorarbeiten aus Abschnitt 14 | 1–2 Tage | saubere Basis, sofort sichtbare Verbesserungen |
| 1 | App `context`, Modelle, `sync_municipalities` | 2–3 Tage | Gemeindetabelle lokal |
| 2 | Grenzen-Matching inkl. Admin und Nachkontrolle | 3–5 Tage | **kritischer Pfad** |
| 3 | Schema, `imports.py`, Import-Commands, `DatasetImport`-Admin | 3–4 Tage | Übernahmeweg steht, unabhängig vom Inhalt |
| 4 | Template-Umbau, Tab-Struktur, Tab „Umfeld" (Modul 3) | 3–4 Tage | Modul 3 sichtbar |
| 5 | PMTiles-Auslieferung, Tab „Hitze" (Modul 6) | 3–4 Tage | Modul 6 sichtbar |
| 6 | API-Endpunkte, CSV-Export | 1–2 Tage | offene Daten |
| 7 | Upload-Endpunkt und Admin-Formular | 2 Tage | optional, nur bei Automatisierungsbedarf |

Der Umfang auf Django-Seite ist durch die externe Vorberechnung deutlich kleiner geworden — realistisch zwei bis drei Wochen statt mehrerer Monate. Was bleibt, ist Datenmodellierung, Validierung und Darstellung.

**Der kritische Pfad ist Phase 2, nicht die Satellitenauswertung.** Ohne verlässliche Zuordnung von Gemeinde-Slug zu Verwaltungsgrenze kann die externe Berechnung ihre Ergebnisse gar nicht sinnvoll schlüsseln, und die Fehlerquellen dort (Namensvarianten, Gemeindezusammenlegungen, Gebietsstand) sind unspektakulär, aber zeitaufwendig.

Zwei Dinge sollten früh geklärt werden, weil sie den Zeitplan spürbar beeinflussen:

1. **`gkz`-Feld in `api.luftdaten.at`.** Nimmt die City-Ressource eine Gemeindekennziffer auf, verkürzt sich Phase 2 von mehreren Tagen auf einen.
2. **Schema vor der Berechnung abstimmen.** Phase 3 sollte *vor* dem ersten externen Lauf abgeschlossen sein. Wenn das Schema erst existiert, nachdem die Daten schon erzeugt wurden, wird entweder das Schema an eine zufällige Ausgabe angepasst oder der Lauf muss wiederholt werden. Die Fixture-Dateien aus [Abschnitt 12](#12-tests) sind dafür das geeignete Übergabeartefakt an die berechnende Seite.
