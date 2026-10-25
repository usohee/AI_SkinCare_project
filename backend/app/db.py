"""SQLite 연결과 테이블 생성. (PostgreSQL 전환 시 이 파일만 바꾸면 되도록 분리)"""
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email VARCHAR UNIQUE,
    password_hash VARCHAR,
    nickname VARCHAR,
    gender VARCHAR,
    birth_year INTEGER,
    skin_type VARCHAR,
    skin_concern TEXT,
    allergy_ingredients TEXT,
    preferred_formulations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skin_analyses (
    analyses_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    image_url VARCHAR,
    score_total INTEGER,
    score_acne INTEGER,
    score_pore INTEGER,
    score_pigmentation INTEGER,
    score_sebum INTEGER,
    raw_values TEXT,
    bbox_coordinates TEXT,
    llm_report TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name VARCHAR NOT NULL,
    brand VARCHAR,
    ingredients TEXT,
    category VARCHAR,
    formulation VARCHAR,
    image_url VARCHAR
);
CREATE TABLE IF NOT EXISTS user_cabinets (
    cabinet_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    is_in_routine VARCHAR DEFAULT 'true',
    routine_time VARCHAR DEFAULT 'NONE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
"""


def init_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """요청마다 하나의 연결을 만들고, 요청이 끝나면 자동으로 닫는다."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
