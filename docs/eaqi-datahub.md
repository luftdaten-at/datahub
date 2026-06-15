# Europäischer Luftqualitätsindex (EAQI) im Luftdaten.at Datahub

Dieser Text beschreibt den **Europäischen Luftqualitätsindex (European Air Quality Index, EAQI)** und wie der Luftdaten.at Datahub ihn für die Darstellung von Feinstaubwerten nutzt. Er ist als Quelle für die Veröffentlichung auf [luftdaten.at](https://luftdaten.at) gedacht.

## Was ist der EAQI?

Der Europäische Luftqualitätsindex wurde von der Europäischen Kommission und der Europäischen Umweltagentur (EEA) entwickelt. Er ordnet Luftschadstoffkonzentrationen **sechs Stufen** zu:

| Stufe (EN) | Stufe (DE) |
|------------|------------|
| Good | Gut |
| Fair | Befriedigend |
| Moderate | Mäßig |
| Poor | Schlecht |
| Very poor | Sehr schlecht |
| Extremely poor | Extrem schlecht |

Die EEA hat den Index **2025 überarbeitet**. Die neuen Stufen orientieren sich stärker an den **WHO-Luftqualitätsrichtwerten von 2021** und verwenden für alle zentralen Schadstoffe **stündliche Messwerte** (1-Stunden-Mittelwerte), nicht mehr 24-Stunden-Mittel für Feinstaub.

Offizielle Informationen und Karten:

- [European Air Quality Index (EEA)](https://airindex.eea.europa.eu/)
- [ETC HE Report 2024/17: Revision der EAQI-Stufen (PDF)](https://www.eionet.europa.eu/etcs/etc-he/products/etc-he-products/etc-he-reports/etc-he-report-2024-17-eeas-revision-of-the-european-air-quality-index-bands/)

## Feinstaub-Stufen im Datahub (1-Stunden-Mittelwerte)

Im Datahub werden für **PM2,5**, **PM10** und **PM1** dieselben **Farben** wie im EAQI verwendet. Die Grenzwerte beziehen sich auf Konzentrationen in **µg/m³** (Mikrogramm pro Kubikmeter).

### PM2,5

| Stufe | Konzentration (µg/m³) |
|-------|----------------------|
| Gut | 0 – 5 |
| Befriedigend | 6 – 15 |
| Mäßig | 16 – 50 |
| Schlecht | 51 – 90 |
| Sehr schlecht | 91 – 140 |
| Extrem schlecht | > 140 |

### PM10

| Stufe | Konzentration (µg/m³) |
|-------|----------------------|
| Gut | 0 – 15 |
| Befriedigend | 16 – 45 |
| Mäßig | 46 – 120 |
| Schlecht | 121 – 195 |
| Sehr schlecht | 196 – 270 |
| Extrem schlecht | > 270 |

### PM1

**PM1** ist im offiziellen EAQI **kein eigener Schadstoff**. Citizen-Science-Geräte liefern PM1-Werte dennoch. Im Datahub werden für PM1 **dieselben Stufen wie für PM2,5** angewendet, damit die Farbskala konsistent bleibt.

## Verwendung im Luftdaten.at Datahub

Der EAQI dient im Datahub vor allem der **visuellen Einordnung** — Marker, Kartenfarben, Diagrammbalken und Legenden. Es wird **pro Feinstaubfraktion** eingefärbt, nicht ein kombinierter Gesamtindex über alle Schadstoffe.

### Karte (Startseite)

- Citizen-Science-Stationen werden nach dem **1-Stunden-Mittelwert** der gewählten Fraktion (PM1, PM2,5 oder PM10) eingefärbt.
- Die **Legende** rechts auf der Karte zeigt die EAQI-Stufen mit µg/m³-Bereichen.
- Link in der Legende: *Methode: Europäischer Luftqualitätsindex* → [luftdaten.at/datahub-methodik/](https://luftdaten.at/datahub-methodik/)

### Geosphere-Schadstoffvorhersage (optional)

- Die Modellkarte **24h Schadstoffvorhersage (Geosphere)** nutzt für **PM2,5** und **PM10** dieselben EAQI-Feinstaubstufen.
- **Ozon (O₃)** und **Stickstoffdioxid (NO₂)** haben **eigene** µg/m³-Stufen für diese Modell-Ebene; sie sind vom Feinstaub-EAQI getrennt.

### Stationsdetail

- **48-Stunden-** und **30-Tage-Übersicht:** Feinstaub-Balkendiagramme und AQI-Legende (PM1, PM2,5, PM10) nach EAQI-Farben.
- In der 48-Stunden-Ansicht kann die **relative Luftfeuchtigkeit** zusätzlich als Linie auf den Feinstaub-Diagrammen erscheinen; in der 30-Tage-Ansicht nicht.

### Weitere Seiten

- **Stationenliste** und **Gemeindedetail:** Markerfarben nach EAQI.
- **Workshops:** Diagramme und Farblegende für importierte Messdaten.
- **Dashboard (Favoriten):** PM2,5-Farbindikator bei favorisierten Stationen und Gemeinden.

## Abgrenzung zum offiziellen EAQI

| Offizieller EAQI (EEA) | Datahub |
|------------------------|---------|
| Mehrere Schadstoffe (PM2,5, PM10, O₃, NO₂, SO₂) | Feinstaub (PM1/PM2,5/PM10) für Citizen-Daten; O₃/NO₂ nur in der Geosphere-Schicht |
| Gesamtindex = **schlechtester** Einzelschadstoff | **Kein** kombinierter Worst-Pollutant-Index; Farbe je nach gewählter PM-Fraktion |
| Stündliche Aktualisierung auf EU-Ebene | 1h-Mittel aus Citizen-Science- und API-Daten |

## Technische Quelle im Repository

Die im Datahub verwendeten Schwellenwerte und RGB-Farben sind zentral definiert in:

- `app/main/eaqi_pm.py` — kanonische EAQI-Stufen für PM1, PM2,5 und PM10
- `app/templates/_eaqi_pm_color_steps.html` — JavaScript-Farbdefinitionen für Karten und Diagramme
- `app/main/pm25_colors.py` — PM2,5-Farben für das Dashboard (Python)

Bei Anpassungen an die EEA-Methodik sollten diese Dateien gemeinsam aktualisiert werden.

## Weiterführende Links

- [EEA European Air Quality Index](https://airindex.eea.europa.eu/)
- [Luftdaten.at — Grenzwerte / Methodik](https://luftdaten.at/luftqualitaet/grenzwerte/)
- [Luftdaten.at — Datahub-Methodik](https://luftdaten.at/datahub-methodik/)
