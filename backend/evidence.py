import os
from pathlib import Path
from uuid import uuid4

from web3 import Web3

from .domain import EvidenceIntegrity, SupplyChainStage


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class EvidenceValidationError(ValueError):
    pass


class EvidenceStore:
    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root or os.environ.get("ORIGINCHAIN_UPLOAD_DIR", Path(__file__).with_name("uploads")))

    def validate(self, filename: str, content_type: str, data: bytes) -> str:
        extension = Path(filename or "").suffix.lower()
        expected_type = ALLOWED_TYPES.get(extension)
        if not expected_type or content_type != expected_type:
            raise EvidenceValidationError("Only PDF, PNG, JPG and JPEG evidence files are accepted")
        if not data:
            raise EvidenceValidationError("Evidence file is empty")
        if len(data) > MAX_UPLOAD_BYTES:
            raise EvidenceValidationError("Evidence file exceeds the 5 MiB limit")
        signatures = {
            ".pdf": data.startswith(b"%PDF-"),
            ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
            ".jpg": data.startswith(b"\xff\xd8\xff"),
            ".jpeg": data.startswith(b"\xff\xd8\xff"),
        }
        if not signatures[extension]:
            raise EvidenceValidationError("File contents do not match the declared file type")
        return extension

    def save(self, stage: SupplyChainStage, filename: str, content_type: str, data: bytes) -> tuple[str, str]:
        extension = self.validate(filename, content_type, data)
        stage_dir = self.root / stage.value.lower()
        stage_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid4().hex}{extension}"
        destination = (stage_dir / stored_name).resolve()
        if stage_dir.resolve() not in destination.parents:
            raise EvidenceValidationError("Unsafe evidence path")
        destination.write_bytes(data)
        relative_name = destination.relative_to(self.root.resolve()).as_posix()
        return relative_name, Web3.to_hex(Web3.keccak(data))

    def integrity(self, stored_filename: str, expected_hash: str) -> EvidenceIntegrity:
        candidate = (self.root / stored_filename).resolve()
        root = self.root.resolve()
        if root not in candidate.parents:
            return EvidenceIntegrity.FILE_MISSING
        if not candidate.is_file():
            return EvidenceIntegrity.FILE_MISSING
        current = Web3.to_hex(Web3.keccak(candidate.read_bytes()))
        return EvidenceIntegrity.VERIFIED if current.lower() == expected_hash.lower() else EvidenceIntegrity.MISMATCH

    def clear_demo_files(self) -> int:
        if not self.root.exists():
            return 0
        removed = 0
        for candidate in self.root.rglob("*"):
            if candidate.is_file() and self.root.resolve() in candidate.resolve().parents:
                candidate.unlink()
                removed += 1
        return removed

    def delete(self, stored_filename: str) -> None:
        candidate = (self.root / stored_filename).resolve()
        if self.root.resolve() in candidate.parents and candidate.is_file():
            candidate.unlink()
