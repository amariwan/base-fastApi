# core_storage

Storage-Modul zur Verwaltung von Binärdaten. Das Modul definiert ein klares Interface und stellt S3-kompatible sowie dateisystembasierte Implementierungen bereit.

## 🏗 Architektur & Kernkomponenten

- **`StorageClient`** (`base.py`): Abstraktes Basis-Interface.
- **`S3StorageClient`** (`s3.py`): Backend für AWS S3 / MinIO. Behandelt Key-Prefixing (`S3_PREFIX`) und Paginierung. Erfordert `boto3` (wird via Lazy Import geladen).
- **`FilesystemStorageClient`** (`filesystem.py`): Lokales Backend für Entwicklung und Tests. Prüft Schreibrechte und speichert unter `{FILESYSTEM_ROOT}/{path}`.
- **`StorageSettings`** (`settings.py`): Pydantic-Settings für die umgebungsbasierte Konfiguration.
- **`StorageDep`** (`dependency.py`): FastAPI Dependency zur direkten Injektion des konfigurierten Clients.
- **Factory** (`factory.py`): `get_storage_client()` wählt und cacht die Implementierung basierend auf der Konfiguration (Singleton-Pattern).

## 🚀 Usage / FastAPI Integration

Die `StorageDep` Dependency ermöglicht eine nahtlose Integration in FastAPI-Routen:

```python
from fastapi import APIRouter, UploadFile, File
from app.core.core_storage import StorageDep

router = APIRouter()

@router.post("/upload")
def upload(storage: StorageDep, file: UploadFile = File(...)):
    data = file.file.read()
    meta = storage.upload_file(data, "some/path.docx", content_type=file.content_type)
    return {"path": meta.path, "size": meta.size_bytes}
```

## ⚙️ Konfiguration (Environment Variables)

Die Steuerung erfolgt über Umgebungsvariablen.

**Allgemein**

- `STORAGE_BACKEND`: `filesystem` oder `s3` (Default: `filesystem`)

**S3 Backend** (Aktiv wenn `STORAGE_BACKEND=s3`)

- `S3_BUCKET`: **Pflichtfeld**. Name des Buckets.
- `S3_ENDPOINT`: Custom Endpoint (z.B. für MinIO).
- `S3_ACCESS_KEY_ID` oder `accessKey` sowie `S3_SECRET_ACCESS_KEY` oder `secretKey`: S3 Credentials.
- `S3_REGION`: S3 Region.
- `S3_SECURE`: `True`/`False` für HTTPS (Default: `True`).
- `S3_ADDRESSING_STYLE`: S3 Addressing Style (z.B. `path` oder `virtual`).
- `S3_PREFIX`: Globaler Prefix für alle Keys in diesem Bucket.

**Filesystem Backend** (Aktiv wenn `STORAGE_BACKEND=filesystem`)

- `FILESYSTEM_ROOT`: Basisverzeichnis für Ablage (Default: `/data`).

## 🛠 API Interface (`StorageClient`)

Alle Implementierungen stellen folgende Methoden bereit:

- `upload_file(file_bytes: bytes, path: str, *, content_type: str = ..., metadata: dict | None = None) -> FileMetadata`
- `download_file(path: str) -> bytes`
- `file_exists(path: str) -> bool`
- `file_size(path: str) -> int`
- `list_files(prefix: str = "") -> list[str]`
- `delete_file(path: str) -> None`
- `generate_presigned_url(path: str, *, expires_in: int = 3600) -> str`
  - _Hinweis: Wird nur vom `S3StorageClient` unterstützt. Der `FilesystemStorageClient` wirft hierbei systembedingt einen `StorageError`._

## ⚠️ Exceptions

- `StorageError`: Allgemeine Basis-Exception des Moduls.
- `StorageFileNotFoundError`: Wird geworfen, wenn eine angeforderte Datei nicht existiert.
- `StorageConfigError`: Wird bei fehlerhafter oder fehlender ENV-Konfiguration geworfen.

## 🔒 Sicherheits- & Systemhinweise

- **Path Validation:** Alle Pfade durchlaufen `normalize_storage_path()`. Leere Pfade, absolute Pfade oder Path-Traversal-Segmente (`..`) werden geblockt.
- **Lazy Loading:** Das Modul importiert `boto3` erst zur Laufzeit. Das Paket muss im Dateisystem-Modus (`STORAGE_BACKEND=filesystem`) nicht installiert sein.
- **Logging:** Der `S3StorageClient` loggt bei der Initialisierung die aktive Bucket/Prefix-Kombination zur leichteren Fehlerdiagnose.

## 🧪 Tests & Erweiterung

**Tests ausführen:**

```bash
cd backend
just test-unit
```

**Neues Backend implementieren:**

1. Neue Klasse anlegen, die von `StorageClient` erbt.
2. Das Enum `StorageBackend` um den neuen Typ erweitern.
3. Factory-Logik in `get_storage_client()` anpassen.
