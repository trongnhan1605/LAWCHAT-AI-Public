from __future__ import annotations

import hashlib
from pathlib import Path


class DocumentIdentityService:
    def compute_content_sha256(self, storage_path: str | None) -> str | None:
        if not storage_path:
            return None
        path = Path(storage_path)
        if not path.exists() or not path.is_file():
            return None

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def build_source_identity(self, *, source_reference: str | None, storage_path: str | None, content_sha256: str | None) -> str | None:
        if content_sha256:
            return f"sha256:{content_sha256}"
        if source_reference and source_reference.strip():
            return f"source:{source_reference.strip()}"
        if storage_path and storage_path.strip():
            return f"path:{Path(storage_path).name.lower()}"
        return None


document_identity_service = DocumentIdentityService()
