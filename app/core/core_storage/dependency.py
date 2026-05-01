"""FastAPI dependency for storage injection."""

from typing import Annotated

from app.core.core_storage.base import StorageClient
from app.core.core_storage.factory import get_storage_client
from fastapi import Depends

StorageDep = Annotated[StorageClient, Depends(get_storage_client)]
