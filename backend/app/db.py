from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import get_settings

settings = get_settings()
url = settings.database_url
if url.startswith('sqlite:///'):
    from pathlib import Path
    Path(url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
