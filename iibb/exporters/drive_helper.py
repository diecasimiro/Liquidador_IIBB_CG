"""
Helper para guardar archivos en la carpeta Drive configurada por contribuyente.

La "carpeta Drive" es una ruta local que puede apuntar a:
  - Google Drive desktop sync: C:/Users/.../Google Drive/Clientes/EMPRESA/
  - OneDrive:                  C:/Users/.../OneDrive/Clientes/EMPRESA/
  - Carpeta de red:            \\\\servidor\\compartida\\EMPRESA\\
  - Cualquier ruta local

En entorno cloud (Render) esta función no está disponible; usar st.download_button.
"""
from __future__ import annotations

import shutil
from pathlib import Path


class DriveNoConfigurado(Exception):
    pass


class DriveNoAccesible(Exception):
    pass


def guardar_en_drive(origen: Path, carpeta_drive: str | None, nombre_archivo: str) -> Path:
    """
    Copia `origen` a `carpeta_drive / nombre_archivo`.
    Devuelve la ruta destino.
    Lanza DriveNoConfigurado si no hay carpeta configurada.
    Lanza DriveNoAccesible si la carpeta no existe o no tiene permisos.
    """
    if not carpeta_drive or not carpeta_drive.strip():
        raise DriveNoConfigurado(
            "Este contribuyente no tiene carpeta Drive configurada. "
            "Andá a sus datos y completá el campo 'Carpeta Drive'."
        )

    destino_dir = Path(carpeta_drive.strip())

    if not destino_dir.exists():
        raise DriveNoAccesible(
            f"La carpeta '{destino_dir}' no existe o no es accesible. "
            "Verificá que Google Drive (o OneDrive) esté sincronizado y la ruta sea correcta."
        )

    if not destino_dir.is_dir():
        raise DriveNoAccesible(f"'{destino_dir}' no es una carpeta.")

    destino = destino_dir / nombre_archivo
    shutil.copy2(str(origen), str(destino))
    return destino
