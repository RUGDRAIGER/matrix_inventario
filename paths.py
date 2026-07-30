import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
DATA_DIR = APP_DIR
BACKUP_DIR = APP_DIR / "backups"
DB_FILENAME = "inventario.db"
DB_PATH = DATA_DIR / DB_FILENAME


def ensure_portable_dirs():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_database() -> Path:
    ensure_portable_dirs()
    if not DB_PATH.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en:\n{DB_PATH}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"inventario_{stamp}.db"
    shutil.copy2(DB_PATH, dest)
    return dest


def open_data_folder():
    ensure_portable_dirs()
    os.startfile(str(DATA_DIR))
