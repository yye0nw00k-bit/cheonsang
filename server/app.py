# -*- coding: utf-8 -*-
"""Cheonsang RPG shared online account and player-data API."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from flask import Flask, jsonify, request

APP = Flask(__name__)
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "최연욱").strip() or "최연욱"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
PBKDF2_ROUNDS = 240_000
USERNAME_RE = re.compile(r"^[^\\/\r\n\t]{2,12}$")


DB_SCHEMA = "cheonsang_rpg"


def _database_dsn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return DATABASE_URL.replace("postgres://", "postgresql://", 1)


def db_connect():
    # Keep every runtime query inside the RPG-only schema.
    conn = psycopg.connect(_database_dsn(), row_factory=dict_row, connect_timeout=8)
    conn.execute('SET search_path TO "cheonsang_rpg"')
    return conn


def password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)


def default_state():
    return {
        "materials": {"풀잎 조각": 3},
        "inventory": ["작은 회복 물약", "작은 회복 물약"],
        "gear": {"name": "초보자 별빛 오브", "atk": 4, "enhance": 0},
        "items": [], "unlocked": ["풀숲"], "special": [],
        "learned_skills": [], "skill_books": [], "equipped_skills": {},
        "stats": {"strength": 0, "vitality": 0, "mana": 0, "agility": 0},
        "stat_points": 5, "mana_core_level": 0, "mana_detection": 0,
        "potions": 5, "first_intro": True,
    }


def init_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    # Create and use a dedicated schema so the existing talking-on database
    # tables in public (and other projects' schemas) remain untouched.
    with psycopg.connect(_database_dsn(), row_factory=dict_row, connect_timeout=8) as conn:
        conn.execute('CREATE SCHEMA IF NOT EXISTS "cheonsang_rpg"')
        conn.execute('SET search_path TO "cheonsang_rpg"')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(12) PRIMARY KEY,
                nickname VARCHAR(24) NOT NULL,
                salt BYTEA NOT NULL,
                password_hash BYTEA NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                banned BOOLEAN NOT NULL DEFAULT FALSE,
                score BIGINT NOT NULL DEFAULT 0,
                gold BIGINT NOT NULL DEFAULT 120,
                level INTEGER NOT NULL DEFAULT 1,
                exp BIGINT NOT NULL DEFAULT 0,
                hp BIGINT NOT NULL DEFAULT 100,
                max_hp BIGINT NOT NULL DEFAULT 100,
                mp BIGINT NOT NULL DEFAULT 50,
                max_mp BIGINT NOT NULL DEFAULT 50,
                state JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                username VARCHAR(12) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        # Upgrade an early schema without dropping any account data.
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(24)")
        conn.execute("UPDATE users SET nickname=username WHERE nickname IS NULL OR nickname=''")
        if len(ADMIN_PASSWORD) < 8:
            raise RuntimeError("ADMIN_PASSWORD must contain at least 8 characters")
        row = conn.execute("SELECT username FROM users WHERE username=%s", (ADMIN_USERNAME,)).fetchone()
        salt = secrets.token_bytes(16)
        digest = password_hash(ADMIN_PASSWORD, salt)
        if not row:
            conn.execute(
                "INSERT INTO users(username,nickname,salt,password_hash,is_admin,gold,hp,max_hp,mp,max_mp,state) VALUES(%s,%s,%s,%s,TRUE,9999,150,150,100,100,%s)",
                (ADMIN_USERNAME, ADMIN_USERNAME, salt, digest, Jsonb(default_state())),
            )
        else:
            # The dashboard secret is the source of truth for the online administrator password.
            conn.execute("UPDATE users SET is_admin=TRUE,salt=%s,password_hash=%s,nickname=%s WHERE username=%s",
                         (salt, digest, ADMIN_USERNAME, ADMIN_USERNAME))
        conn.commit()


def user_payload(row):
    if not row:
        return None
    data = dict(row)
    state = data.get("state") or {}
    if isinstance(state, str):
        try:
            state = json.loads(state)
        except Exception:
            state = {}
    data["state"] = json.dumps(state, ensure_ascii=False)
    data["is_admin"] = bool(data.get("is_admin"))
    data["banned"] = bool(data.get("banned"))
    data.pop("salt", None)
    data.pop("password_hash", None)
    data.pop("created_at", None)
    return data


def error(message, status=400):
    return jsonify({"ok": False, "message": message}), status


def body_json():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def current_user(admin=False):
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not token:
        return None
    with db_connect() as conn:
        row = conn.execute("""
            SELECT u.* FROM sessions s JOIN users u ON u.username=s.username
            WHERE s.token=%s AND s.expires_at > NOW()
        """, (token,)).fetchone()
    if not row or (row["banned"] and not row["is_admin"]):
        return None
    if admin and not row["is_admin"]:
        return None
    return row


def require_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user(False)
        if not user:
            return error("로그인이 만료됐거나 계정을 사용할 수 없어. 다시 로그인해 줘.", 401)
        request.current_user = user
        return fn(*args, **kwargs)
    return wrapped


def require_admin(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user(True)
        if not user:
            return error("관리자 권한이 필요해.", 403)
        request.current_user = user
        return fn(*args, **kwargs)
    return wrapped


@APP.get("/health")
def health():
    try:
        with db_connect() as conn:
            conn.execute("SELECT 1")
        return jsonify({"ok": True, "service": "Cheonsang RPG API"})
    except Exception:
        return error("database unavailable", 503)


@APP.post("/api/register")
def register():
    data = body_json()
    username = str(data.get("username", "")).strip()
    nickname = str(data.get("nickname", username)).strip()[:12] or username
    password = str(data.get("password", ""))
    if not USERNAME_RE.fullmatch(username):
        return error("아이디는 2~12글자이며 일부 특수문자는 사용할 수 없어.")
    if len(nickname) < 2 or any(ch in nickname for ch in "\\/\r\n\t"):
        return error("닉네임은 2~12글자로 입력해 줘.")
    if len(password) < 8:
        return error("온라인 계정 비밀번호는 8글자 이상으로 설정해 줘.")
    if username == ADMIN_USERNAME:
        return error("이미 사용할 수 없는 아이디야.")
    salt = secrets.token_bytes(16)
    with db_connect() as conn:
        try:
            conn.execute(
                "INSERT INTO users(username,nickname,salt,password_hash,state) VALUES(%s,%s,%s,%s,%s)",
                (username, nickname, salt, password_hash(password, salt), Jsonb(default_state())),
            )
            conn.commit()
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return error("이미 사용 중인 아이디야.", 409)
    return jsonify({"ok": True, "message": "온라인 회원가입이 완료됐어. 로그인해 줘."})


@APP.post("/api/login")
def login():
    data = body_json()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
        if not row:
            return error("아이디 또는 비밀번호를 확인해 줘.", 401)
        if row["banned"] and not row["is_admin"]:
            return error("이 계정은 관리자에 의해 이용이 제한되어 있어.", 403)
        if not hmac.compare_digest(password_hash(password, bytes(row["salt"])), bytes(row["password_hash"])):
            return error("아이디 또는 비밀번호를 확인해 줘.", 401)
        token = secrets.token_urlsafe(40)
        conn.execute("INSERT INTO sessions(token,username,expires_at) VALUES(%s,%s,%s)",
                     (token, username, datetime.now(timezone.utc) + timedelta(days=30)))
        conn.commit()
    return jsonify({"ok": True, "token": token, "user": user_payload(row), "message": "온라인 로그인 성공!"})


@APP.post("/api/logout")
@require_auth
def logout():
    token = request.headers.get("Authorization", "")[7:].strip()
    with db_connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token=%s", (token,))
        conn.commit()
    return jsonify({"ok": True})


@APP.post("/api/player/save")
@require_auth
def save_player():
    data = body_json()
    username = request.current_user["username"]
    state = data.get("state", {})
    if not isinstance(state, dict):
        return error("잘못된 저장 데이터야.")
    fields = {}
    for key, low, high in (
        ("score", 0, 2_000_000_000), ("gold", 0, 2_000_000_000),
        ("level", 1, 9999), ("exp", 0, 2_000_000_000),
        ("hp", 1, 2_000_000_000), ("max_hp", 1, 2_000_000_000),
        ("mp", 0, 2_000_000_000), ("max_mp", 0, 2_000_000_000),
    ):
        try:
            fields[key] = max(low, min(high, int(data.get(key, 0))))
        except (TypeError, ValueError):
            return error(f"{key} 값이 올바르지 않아.")
    fields["hp"] = min(fields["hp"], fields["max_hp"])
    fields["mp"] = min(fields["mp"], fields["max_mp"])
    with db_connect() as conn:
        conn.execute("""
            UPDATE users SET score=%s,gold=%s,level=%s,exp=%s,hp=%s,max_hp=%s,mp=%s,max_mp=%s,state=%s
            WHERE username=%s
        """, (fields["score"], fields["gold"], fields["level"], fields["exp"], fields["hp"],
              fields["max_hp"], fields["mp"], fields["max_mp"], Jsonb(state), username))
        conn.commit()
    return jsonify({"ok": True})


@APP.get("/api/admin/users")
@require_admin
def admin_users():
    query = str(request.args.get("q", "")).strip()[:24]
    pattern = f"%{query}%"
    with db_connect() as conn:
        rows = conn.execute("""
            SELECT username,nickname,is_admin,banned,score,gold,level
            FROM users WHERE (%s='') OR nickname ILIKE %s OR username ILIKE %s
            ORDER BY is_admin DESC, score DESC, username ASC
        """, (query, pattern, pattern)).fetchall()
    users = [dict(r) for r in rows]
    return jsonify({"ok": True, "total": len(users), "users": users})


@APP.get("/api/admin/users/<username>")
@require_admin
def admin_user_detail(username):
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
    if not row:
        return error("계정을 찾을 수 없어.", 404)
    return jsonify({"ok": True, "user": user_payload(row)})


@APP.post("/api/admin/users/<username>/update")
@require_admin
def admin_update_user(username):
    data = body_json()
    field = str(data.get("field", ""))
    try:
        value = int(data.get("value"))
    except (TypeError, ValueError):
        return error("수정할 값은 숫자여야 해.")
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
        if not row:
            return error("계정을 찾을 수 없어.", 404)
        state = row["state"] or {}
        if isinstance(state, str):
            state = json.loads(state)
        stats = state.setdefault("stats", {"strength": 0, "vitality": 0, "mana": 0, "agility": 0})
        if field in ("score", "gold", "level", "exp", "hp", "mp"):
            ranges = {"score": (0, 2_000_000_000), "gold": (0, 2_000_000_000), "level": (1, 9999),
                      "exp": (0, 2_000_000_000), "hp": (1, 2_000_000_000), "mp": (0, 2_000_000_000)}
            low, high = ranges[field]
            value = max(low, min(high, value))
            if field == "level":
                delta = value - int(row["level"])
                max_hp = max(1, int(row["max_hp"]) + delta * 12)
                max_mp = max(0, int(row["max_mp"]) + delta * 5)
                conn.execute("UPDATE users SET level=%s,exp=0,max_hp=%s,max_mp=%s,hp=LEAST(hp,%s),mp=LEAST(mp,%s) WHERE username=%s",
                             (value, max_hp, max_mp, max_hp, max_mp, username))
            elif field == "hp":
                conn.execute("UPDATE users SET hp=LEAST(%s,max_hp) WHERE username=%s", (value, username))
            elif field == "mp":
                conn.execute("UPDATE users SET mp=LEAST(%s,max_mp) WHERE username=%s", (value, username))
            else:
                conn.execute(f"UPDATE users SET {field}=%s WHERE username=%s", (value, username))
        elif field == "stat_points":
            state["stat_points"] = max(0, min(2_000_000_000, value))
        elif field == "core":
            state["mana_core_level"] = max(0, min(100, value))
        elif field in ("strength", "vitality", "mana", "agility"):
            old = int(stats.get(field, 0))
            value = max(0, min(1_000_000, value))
            diff = value - old
            if field == "vitality" and diff:
                max_hp = max(1, int(row["max_hp"]) + diff * 20)
                hp = max(1, min(max_hp, int(row["hp"]) + diff * 20))
                conn.execute("UPDATE users SET max_hp=%s,hp=%s WHERE username=%s", (max_hp, hp, username))
            if field == "mana" and diff:
                max_mp = max(0, int(row["max_mp"]) + diff * 10)
                mp = max(0, min(max_mp, int(row["mp"]) + diff * 10))
                conn.execute("UPDATE users SET max_mp=%s,mp=%s WHERE username=%s", (max_mp, mp, username))
            stats[field] = value
        else:
            return error("지원하지 않는 수정 항목이야.")
        conn.execute("UPDATE users SET state=%s WHERE username=%s", (Jsonb(state), username))
        if username != request.current_user["username"]:
            conn.execute("DELETE FROM sessions WHERE username=%s", (username,))
        conn.commit()
    return jsonify({"ok": True, "message": "계정 데이터를 수정했어. 대상 계정은 다시 로그인해야 해."})


@APP.post("/api/admin/users/<username>/ban")
@require_admin
def admin_ban(username):
    banned = bool(body_json().get("banned", True))
    if username == ADMIN_USERNAME:
        return error("관리자 계정은 밴할 수 없어.", 403)
    with db_connect() as conn:
        cur = conn.execute("UPDATE users SET banned=%s WHERE username=%s", (banned, username))
        if cur.rowcount == 1 and banned:
            conn.execute("DELETE FROM sessions WHERE username=%s", (username,))
        conn.commit()
    if cur.rowcount != 1:
        return error("계정을 찾을 수 없어.", 404)
    return jsonify({"ok": True})


@APP.post("/api/admin/users/<username>/skills")
@require_admin
def admin_grant_skills(username):
    skills = ["이상한 스킬", "화염구", "별빛 돌진", "별빛 파동", "마나 감지", "투명 감지"]
    with db_connect() as conn:
        row = conn.execute("SELECT state FROM users WHERE username=%s", (username,)).fetchone()
        if not row:
            return error("계정을 찾을 수 없어.", 404)
        state = row["state"] or {}
        learned = state.setdefault("learned_skills", [])
        books = state.setdefault("skill_books", [])
        # Admin grants the skill books; players still have to learn them in-game.
        for skill in skills:
            book = skill + " 스킬북"
            if skill not in learned and book not in books:
                books.append(book)
        conn.execute("UPDATE users SET state=%s WHERE username=%s", (Jsonb(state), username))
        if username != request.current_user["username"]:
            conn.execute("DELETE FROM sessions WHERE username=%s", (username,))
        conn.commit()
    return jsonify({"ok": True})


@APP.post("/api/admin/users/<username>/heal")
@require_admin
def admin_heal(username):
    with db_connect() as conn:
        cur = conn.execute("UPDATE users SET hp=max_hp,mp=max_mp WHERE username=%s", (username,))
        if cur.rowcount == 1 and username != request.current_user["username"]:
            conn.execute("DELETE FROM sessions WHERE username=%s", (username,))
        conn.commit()
    if cur.rowcount != 1:
        return error("계정을 찾을 수 없어.", 404)
    return jsonify({"ok": True})


@APP.post("/api/admin/import-users")
@require_admin
def admin_import_users():
    """Import old local PBKDF2 accounts without sending their plaintext passwords."""
    users = body_json().get("users", [])
    if not isinstance(users, list) or len(users) > 500:
        return error("가져올 계정 목록이 올바르지 않아.")
    imported = skipped = 0
    with db_connect() as conn:
        for item in users:
            try:
                username = str(item["username"]).strip()
                if not USERNAME_RE.fullmatch(username) or username == ADMIN_USERNAME:
                    skipped += 1
                    continue
                salt = bytes.fromhex(item["salt"])
                digest = bytes.fromhex(item["password_hash"])
                if len(salt) < 8 or len(digest) != 32:
                    skipped += 1
                    continue
                state = item.get("state") or {}
                cur = conn.execute("""
                    INSERT INTO users(username,nickname,salt,password_hash,is_admin,banned,score,gold,level,exp,hp,max_hp,mp,max_mp,state)
                    VALUES(%s,%s,%s,%s,FALSE,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(username) DO NOTHING
                """, (username, str(item.get("nickname") or username)[:12], salt, digest, bool(item.get("banned", False)),
                      max(0,int(item.get("score",0))), max(0,int(item.get("gold",120))), max(1,int(item.get("level",1))),
                      max(0,int(item.get("exp",0))), max(1,int(item.get("hp",100))), max(1,int(item.get("max_hp",100))),
                      max(0,int(item.get("mp",50))), max(0,int(item.get("max_mp",50))), Jsonb(state)))
                if cur.rowcount == 1:
                    imported += 1
                else:
                    skipped += 1
            except Exception:
                conn.rollback()
                skipped += 1
        conn.commit()
    return jsonify({"ok": True, "imported": imported, "skipped": skipped})


try:
    init_db()
except Exception as exc:
    # Fail closed: Render deploy logs show the actual DB/config issue, without printing secrets.
    raise RuntimeError(f"Cheonsang RPG API startup failed: {type(exc).__name__}") from None

app = APP
