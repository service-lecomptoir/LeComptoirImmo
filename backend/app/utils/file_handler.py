"""
Gestion des fichiers uploadés.
Les fichiers sont stockés dans : uploads/{entity_type}/{entity_id}/{uuid}_{filename}
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException, status

# Types MIME autorisés et leurs extensions
ALLOWED_MIME_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 Mo

UPLOAD_DIR = Path("uploads")


def _get_upload_path(entity_type: str, entity_id: str) -> Path:
    path = UPLOAD_DIR / entity_type / entity_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_file(file: UploadFile) -> None:
    """Valide le type MIME et la taille du fichier."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Type de fichier non autorisé : {file.content_type}. "
                   f"Types acceptés : PDF, JPG, PNG, WEBP, DOC, DOCX, XLS, XLSX",
        )


async def save_file(
    file: UploadFile,
    entity_type: str,
    entity_id: str,
) -> tuple[str, int]:
    """
    Sauvegarde le fichier et retourne (file_path relatif, file_size).
    Le nom de fichier est préfixé par un UUID pour éviter les collisions.
    """
    validate_file(file)

    upload_path = _get_upload_path(entity_type, entity_id)
    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename or 'file').name}"
    dest = upload_path / safe_name

    size = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(8192):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Fichier trop volumineux. Taille max : 20 Mo",
                )
            f.write(chunk)

    # Chemin relatif stocké en BDD
    relative_path = str(dest).replace("\\", "/")
    return relative_path, size


def delete_file(file_path: str) -> None:
    """Supprime un fichier du disque."""
    path = Path(file_path)
    if path.exists():
        path.unlink()


def get_file_path(file_path: str) -> Optional[Path]:
    """Retourne le Path absolu si le fichier existe."""
    path = Path(file_path)
    return path if path.exists() else None
