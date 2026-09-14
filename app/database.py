"""
Módulo de compatibilidade para acesso à base de dados.
Reexporta as instâncias centralizadas de app.core.database.
"""
from app.core.database import engine, Session, Base, get_db, DATABASE_URL

__all__ = ["engine", "Session", "Base", "get_db", "DATABASE_URL"]
