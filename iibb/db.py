import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# En local: ~/.iibb/iibb.db
# En Render: /data/iibb.db  (Persistent Disk montado en /data)
_DB_DIR = Path(os.environ.get("IIBB_DB_DIR", Path.home() / ".iibb"))
_DB_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _DB_DIR / "iibb.db"

_engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    return _engine


def get_session() -> Session:
    return SessionLocal()


def get_db_path() -> Path:
    return _DB_PATH
