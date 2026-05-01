# Architektur-Regeln für neue Services

Dieses Verzeichnis ist der gemeinsame Ort für unabhängige Service-Pakete.
Das Ziel ist eine wiederholbare Architektur für neue Services mit klarer Schichtentrennung, hoher Testbarkeit und stabilen Abhängigkeiten.

## 1. Minimaler Paketaufbau

Jeder neue Service sollte eine eigene Subdomain unter `app/services/<service_name>/` erhalten.
Die empfohlene Basisstruktur lautet:

```
<service_name>/
├── api/
│   ├── __init__.py
│   ├── router.py
│   ├── dependencies.py
│   ├── errors.py
│   └── ...
├── application/
│   ├── __init__.py
│   ├── ports/
│   ├── use_case.py
│   └── ...
├── domain/
│   ├── __init__.py
│   ├── entities/
│   ├── value_objects/
│   ├── exceptions.py
│   └── ...
├── infrastructure/
│   ├── __init__.py
│   ├── providers.py
│   ├── adapters.py
│   └── ...
├── repositories/         # optionale Persistenz-Adapter / Gateway-Implementierungen
├── models/               # gemeinsame Datenmodelle / ORM-Modelle / Domain-DTOs
├── errors/               # Service-spezifische Fehlerlogik und überschreibbare Fehlertexte
├── messages/             # Lokalisierte Texte, Fehlermeldungen, Validierungsnachrichten
├── config/
│   ├── __init__.py
│   └── ...
├── schemas/
│   ├── request/
│   ├── response/
│   └── ...
├── utils/                # Hilfsfunktionen und Utility-Code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke_imports_test.py
└── README.md
```

### 1.1 Weitere häufige Ordner

Ein Service benötigt nicht immer alle Ordner, aber diese zusätzlichen Strukturen sind in vielen Services sinnvoll:

- `repositories/`
  - Persistenz-Layer oder Gateway-Adapter, die von `application/ports` konsumiert werden.
  - Kann auch als Teil von `infrastructure/` organisiert sein, wenn der Service bereits eine klare `infrastructure/`-Struktur nutzt.
- `models/`
  - Gemeinsame Datenmodelle, Domain-DTOs oder ORM-Modelle.
  - Sollte nicht mit Pydantic-Schemas verwechselt werden; `schemas/` bleibt die API-Transportschicht.
- `errors/`
  - Service-spezifische Fehler, Fehler-Handler, Statuscodes oder Mapping-Logik.
  - API-spezifische HTTP-Mappings gehören weiterhin in `api/errors.py`.
- `messages/`
  - Lokalisierte Nachrichten, Validierungs-Texte oder Fehlerbotschaften.
  - Kann als reine Ressource dienen ohne Geschäftslogik.
- `utils/`
  - Hilfsfunktionen, die nicht direkt zur Domain oder zu Infrastruktur-Ports gehören.

### 1.2 Vollständige Ordnerübersicht

Die folgende Liste beschreibt alle typischen Verzeichnisse, die ein Service enthalten kann. Nicht alle sind zwingend erforderlich, aber sie helfen bei klarer Trennung und Wartbarkeit.

- `api/`
  - HTTP-Router, Endpunkt-Logik, Request-Validation und Response-Mapping.
  - Bindet `application`-Use Cases über Dependency Injection ein.
- `application/`
  - Use Cases, Orchestrierung und Ports.
  - Trennt Geschäftslogik von Infrastruktur und Präsentation.
- `domain/`
  - Reine Business-Logik, Entities, Value Objects und Domain-Fehler.
- `infrastructure/`
  - Konkrete Adapter und Implementierungen für externe Systeme.
  - Kann auch Infrastruktur-Helpers, Persistenzadapter und externe APIs enthalten.
- `repositories/`
  - Datenzugriffs-Implementierungen und Repository-Gateways.
  - Kann auch unter `infrastructure/` liegen, wenn sich der Service stark auf Persistenz konzentriert.
- `models/`
  - Wiederverwendbare Datenklassen und gemeinsame Objektmodelle.
  - ORM- oder Domain-Modelle, die nicht direkt als API-Schemas dienen.
- `schemas/`
  - Transportmodelle für Request/Response-Objekte.
  - Pydantic-Modelle für API-Verträge und Validierung.
- `errors/`
  - Fehlerklassen, Ausnahmeverarbeitung und konfigurierbare Fehlertexte.
- `messages/`
  - Lokalisierte Strings, Validierungsnachrichten oder Audit-Nachrichten.
  - Eignet sich für externe Texte, die getrennt von Code verwaltet werden.
- `config/`
  - Service-spezifische Settings und Konfigurationsmodelle.
- `tests/`
  - Unit-, Integration- und evtl. e2e-Tests.
  - `smoke_imports_test.py` prüft die Importierbarkeit des Pakets.
- `README.md`
  - Service-spezifische Dokumentation und Architektur-Regeln.

## 2. Schichtregeln

### 2.1 `api/`
- Präsentations- und Transport-Schicht.
- Enthält FastAPI-Router, HTTP-Schemas, Dependency Injection und Fehler-Mapping.
- Keine Geschäftslogik, keine Use-Case-Orchestrierung.
- Nur adapterbezogene Logik für HTTP, Schema-Validierung und Antwortformatierung.

### 2.2 `application/`
- Use-Case-Schicht.
- Koordiniert Geschäftsprozesse und verarbeitet Domain-Objekte.
- Definiert Ports/Interfaces in `application/ports/`.
- Abhängig von `domain` und `application.ports`, aber niemals direkt von `infrastructure`.

### 2.3 `domain/`
- Reine Geschäftslogik.
- Enthält Entities, Value Objects, Domain-Regeln und Domain-Fehler.
- Keine HTTP- oder Persistence-Details.
- Keine Abhängigkeit zu externen Frameworks außer reinen Python-Bibliotheken für Geschäftslogik.

### 2.4 `infrastructure/`
- Implementiert Ports und Adapter für externe Systeme.
- Enthält Datenbankzugriff, Dateisystem, externe APIs, Job-Management, Dokumentenkonvertierung etc.
- Muss `application.ports` importieren, jedoch niemals `application` selbst.
- Kein Business Code – nur Implementierung von IO und Schnittstellen.

### 2.5 `schemas/`
- Definiert DTOs für Ein- und Ausgabe.
- Pydantic-Modelle sind nur für Transport, Serialisierung, Validation und API-Kontrakte.
- Domain-Klassen sind keine Schemas und sollten nicht als Transport-Modelle verwendet werden.

### 2.6 `config/`
- Service-spezifische Einstellungen als Pydantic-Modelle.
- Keine Geschäftslogik in den Settings.
- Konfiguration bleibt vom Runtime-Code getrennt.

## 3. Dependency-Inversion und Wiring

- Ports sind in `application/ports/` definiert.
- `infrastructure/providers.py` liefert konkrete Implementierungen.
- API und Tests verwenden Provider / Dependency Injection.
- Die Bindung von konkreten Implementierungen passiert in der Infrastruktur-Schicht.
- Ziel: Use Cases kennen nur Interfaces, nicht konkrete Adapter.

## 4. Fehler-Handling

- Domain- und Application-Fehler gehören in `domain/exceptions.py`.
- API-Adapter mappt Fehler in HTTP-Statuscodes und Response-Formate.
- Vermeide HTTP-spezifische Ausnahmen in Domain-/Application-Code.

## 5. Namenskonventionen

- `router.py` für Hauptroute-Registrierung.
- `dependencies.py` für FastAPI-Abhängigkeiten und Provider-Exporte.
- `providers.py` für Infrastruktur-Instanziierung und Singleton-Logik.
- `use_case.py` / `orchestrator.py` für Geschäftsprozesse.
- `exceptions.py` für service-spezifische Domain-Fehler.

## 6. Testprinzipien

- Schreibe Unit-Tests für Domain und Application.
- Schreibe Integrationstests für API-Flows und Provider-Wiring.
- Nutze `smoke_imports_test.py`, um sicherzustellen, dass das Paket importierbar bleibt.
- Teste Ports mit Stub-/Mock-Implementierungen.
- Halte Tests schichtgetrennt: API-Tests prüfen Transport, Use-Case-Tests prüfen Orchestrierung, Domain-Tests prüfen Regeln.

## 7. Praktische Regeln für neue Services

- Jedes Service-Paket ist eigenständig und sollte nicht direkt intern mit anderen Services verknüpft sein.
- Gemeinsame Funktionalität gehört in `app/shared/`, nicht in ein anderes Service-Paket.
- Legacy- oder kompatible Wrapper können in `api/compat/` erfolgen, wenn nötig.
- `__init__.py` bleibt minimal: Exportiere nur das, was öffentlich von außen gebraucht wird.
- Dokumentiere das Service-Modul in seinem eigenen `README.md`.

## 8. Schritt-für-Schritt: Neuen Service anlegen

1. Erstelle `app/services/<service_name>/`.
2. Lege die Basisschichten an: `api/`, `application/`, `domain/`, `infrastructure/`, `schemas/`, `tests/`.
3. Definiere Ports in `application/ports/`.
4. Implementiere Domain-Modelle und Regeln in `domain/`.
5. Schreibe Use Cases in `application/`.
6. Implementiere Adapter in `infrastructure/` und binde sie über `providers.py`.
7. Erstelle Router, Dependencies und Fehlerbehandlung in `api/`.
8. Lege Tests an: Unit-Tests für Logik, Integrationstests für API.

## 9. Warum diese Regeln?

- Klare Schichten reduzieren Kopplung.
- Ports/Adapter machen Services leicht testbar und austauschbar.
- Jeder Service wird unabhängig deploybar und wartbar.
- Die Architektur bleibt konsistent über alle Services hinweg.
