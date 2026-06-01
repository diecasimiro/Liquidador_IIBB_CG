import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


def _get_db_url() -> str:
    # En Render con PostgreSQL: DATABASE_URL se setea automáticamente
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render usa "postgres://" pero SQLAlchemy requiere "postgresql://"
        return url.replace("postgres://", "postgresql://", 1)
    # Local: SQLite en ~/.iibb/iibb.db
    db_dir = Path(os.environ.get("IIBB_DB_DIR", Path.home() / ".iibb"))
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_dir / 'iibb.db'}"


_DB_URL = _get_db_url()
_is_sqlite = _DB_URL.startswith("sqlite")

_engine = create_engine(
    _DB_URL,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    return _engine


def get_session() -> Session:
    return SessionLocal()


def get_db_url() -> str:
    return _DB_URL


# Mantener compatibilidad con código que llama get_db_path()
def get_db_path():
    return _DB_URL
