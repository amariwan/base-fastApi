# FastAPI Profiling Middleware

Diese Middleware aktiviert On-Demand-Profiling mit `pyinstrument`.

## Zweck
- Analyse von langsamen Requests im lokalen Betrieb.
- Sichtbar machen von CPU-Zeit und blockierenden Abschnitten in einem Request.

## Aktivierung
Profiling ist standardmaessig aus (`PROFILING_ENABLED=false`).

In `.env` oder Shell aktivieren:

```bash
PROFILING_ENABLED=true
```

Die Middleware wird nur registriert, wenn `PROFILING_ENABLED=true` gesetzt ist.

## Nutzung
Profiling wird pro Request ueber Query-Parameter aktiviert:
- `profile` (beliebiger nicht-leerer Wert) aktiviert Profiling.
- `profile_format` bestimmt das Ausgabeformat:
  - `html`
  - `speedscope`
- Fehlt `profile_format` oder ist der Wert ungueltig, wird `speedscope` verwendet.

### Beispiele

```bash
# HTML Report
curl "http://127.0.0.1:5000/api/health?profile=1&profile_format=html"

# Speedscope Report
curl "http://127.0.0.1:5000/api/health?profile=1&profile_format=speedscope"
```

## Ausgabe
Die Middleware schreibt die letzte Profiling-Ausgabe in feste Dateien unter `backend/app/`:
- `profile.html`
- `profile.speedscope.json`

Hinweise:
- Die Dateien werden bei jedem neuen Profiling-Lauf ueberschrieben.
- Es wird keine Historie oder Rotation gepflegt.

## Auswertung
- `profile.html`: direkt im Browser oeffnen.
- `profile.speedscope.json`: unter <https://www.speedscope.app> laden.

## Laufzeitverhalten
- Funktioniert fuer sync- und async-Handler.
- Profiling findet nur fuer Requests mit Query-Parameter `profile` statt.
- Requests ohne `profile` laufen normal durch.

## Grenzen und Risiken
- Nicht fuer produktiven Dauerbetrieb gedacht (zusaetzlicher Overhead + Dateischreibzugriffe).
- Kein Mehr-Request-Archiv, nur letzter Lauf.
- Bei parallelen Profiling-Requests kann die Ausgabe-Datei ueberschrieben werden.

## Troubleshooting
- Keine Profil-Datei vorhanden:
  - `PROFILING_ENABLED=true` gesetzt?
  - Request wirklich mit `?profile=...` aufgerufen?
- Unerwartetes Format:
  - `profile_format` pruefen (`html` oder `speedscope`).
- Falscher Erwartungspfad:
  - Ausgabe liegt unter `backend/app/profile.*`.
