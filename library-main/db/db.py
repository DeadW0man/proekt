import sqlite3
from os import getenv

from flask import g

db_path = getenv('SOLARIS_SQLITE_PATH', 'dev.db')


def get_db():
    """Возвращает подключение к БД (одно на запрос)."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON;")
    return db


def close_db(exception=None):
    """Закрывает подключение после обработки запроса (teardown_appcontext)."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def prepare_tables() -> None:
    # Схема синхронизирована с migrations/start.sql:
    # books создаётся ДО shares, email UNIQUE, внешние ключи с ON DELETE CASCADE
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(128) NOT NULL,
            email VARCHAR(128) NOT NULL UNIQUE,
            password VARCHAR(128) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            author VARCHAR(128) NOT NULL,
            release_year INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            giver_id INTEGER NOT NULL,
            taker_id INTEGER NOT NULL,
            final_date VARCHAR(32),
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
            FOREIGN KEY (giver_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (taker_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)
