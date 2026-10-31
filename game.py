# -*- coding: utf-8 -*-
"""천상 RPG - 2D desktop RPG with optional shared online accounts."""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import random
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Ask SDL to show the Windows IME candidate/composition UI when Korean is typed.
os.environ.setdefault("SDL_IME_SHOW_UI", "1")

import pygame

APP_NAME = "천상 RPG"
FINAL_BOSS = "화염의 다크 오브 파멸적인 천상의 투명 드레곤"
SCREEN_W, SCREEN_H = 1100, 720
FPS = 60
VIEW = pygame.Rect(24, 96, 750, 548)
PANEL = pygame.Rect(792, 96, 284, 548)
MAP_W, MAP_H = 1600, 1100

# The administrator password is stored only as a salted PBKDF2 hash.
# This is suitable for a local prototype, not a secure online authority system.
ADMIN_NAME = "최연욱"
ADMIN_SALT = bytes.fromhex("7477b1aadfa28bbf9fa86145eb0f6283")
ADMIN_HASH = bytes.fromhex("2db569a2782352c4421a36edb5c924d13ac5f45c1d124f8ca9cc3b7e2da6d816")

WHITE = (245, 247, 255)
INK = (26, 32, 49)
MUTED = (157, 169, 190)
GOLD = (255, 211, 99)
CYAN = (104, 218, 242)
RED = (255, 112, 124)
GREEN = (108, 219, 151)
DARK = (16, 22, 37)
PANEL_BG = (27, 36, 56)
PANEL_EDGE = (63, 79, 109)

ZONES = [
    {"name": "풀숲", "level": 1, "bg": (66, 119, 79), "ground": (82, 145, 91), "accent": (157, 203, 111),
     "enemies": ["슬라임", "좀비", "갑옷 좀비"]},
    {"name": "동굴", "level": 2, "bg": (64, 71, 91), "ground": (80, 88, 111), "accent": (151, 169, 205),
     "enemies": ["동굴 좀비", "동굴 박쥐", "수정 골렘"]},
    {"name": "샌드 사막", "level": 4, "bg": (178, 139, 74), "ground": (211, 171, 92), "accent": (255, 221, 145),
     "enemies": ["샌드 슬라임", "미라", "샌드 수호자", "피라미드 수호자"]},
    {"name": "메이플 공원", "level": 6, "bg": (153, 91, 70), "ground": (185, 112, 78), "accent": (255, 184, 113),
     "enemies": ["메이플 사무라이", "메이플 궁수", "단풍 정령"]},
    {"name": "얼음의 협곡", "level": 8, "bg": (86, 139, 169), "ground": (126, 183, 207), "accent": (211, 245, 255),
     "enemies": ["예티", "눈사람", "얼음의 수호자", "빙하의 수호자"]},
    {"name": "천상의 구멍", "level": 10, "bg": (73, 67, 119), "ground": (101, 92, 158), "accent": (202, 184, 255),
     "enemies": ["천상의 박쥐", "천상의 수호자", "별빛 감시자"]},
    {"name": "빛의 동굴", "level": 3, "bg": (62, 101, 125), "ground": (79, 131, 153), "accent": (174, 241, 255),
     "enemies": ["빛의 돌덩이", "화염의 좀비"]},
    {"name": "2세계 · 별빛 황야", "level": 12, "bg": (63, 54, 108), "ground": (92, 78, 147), "accent": (246, 219, 255),
     "enemies": ["성운 슬라임", "공허 정찰자", "고대 수호자"]},
]
ZONE_BY_NAME = {z["name"]: z for z in ZONES}

MATERIAL_FOR_ZONE = {
    "풀숲": "풀잎 조각", "동굴": "동굴 수정", "빛의 동굴": "빛나는 파편",
    "샌드 사막": "모래 핵", "메이플 공원": "단풍잎", "얼음의 협곡": "얼음 결정",
    "천상의 구멍": "천상 파편", "2세계 · 별빛 황야": "별빛 가루",
}

MONSTER_STATS = {
    "슬라임": (28, 6, 8, 5), "좀비": (42, 8, 12, 7), "갑옷 좀비": (75, 11, 20, 11),
    "동굴 좀비": (66, 12, 20, 12), "동굴 박쥐": (38, 10, 14, 10), "수정 골렘": (105, 15, 33, 17),
    "샌드 슬라임": (80, 15, 26, 15), "미라": (108, 18, 32, 18), "샌드 수호자": (165, 22, 55, 26),
    "피라미드 수호자": (230, 25, 90, 34), "메이플 사무라이": (190, 27, 65, 32), "메이플 궁수": (145, 25, 54, 28),
    "단풍 정령": (160, 23, 50, 30), "예티": (260, 32, 90, 42), "눈사람": (210, 27, 68, 34),
    "얼음의 수호자": (330, 38, 120, 55), "빙하의 수호자": (430, 45, 180, 70),
    "천상의 박쥐": (300, 40, 110, 55), "천상의 수호자": (460, 52, 180, 80), "별빛 감시자": (390, 48, 160, 70),
    "빛의 돌덩이": (95, 0, 18, 8), "화염의 좀비": (185, 30, 54, 35),
    "성운 슬라임": (490, 58, 220, 90), "공허 정찰자": (560, 65, 250, 105), "고대 수호자": (1250, 78, 650, 260),
    FINAL_BOSS: (9000, 115, 12000, 25000),
}

GEAR_RECIPES = [
    {"name": "초보자 별빛 오브", "atk": 7, "cost": {"풀잎 조각": 4}, "gold": 15},
    {"name": "수정 코어", "atk": 16, "cost": {"동굴 수정": 5, "풀잎 조각": 3}, "gold": 80},
    {"name": "모래 폭풍 크리스탈", "atk": 29, "cost": {"모래 핵": 6, "동굴 수정": 3}, "gold": 180},
    {"name": "단풍 마력구", "atk": 42, "cost": {"단풍잎": 7, "모래 핵": 4}, "gold": 320},
    {"name": "빙하의 별빛 오브", "atk": 60, "cost": {"얼음 결정": 8, "단풍잎": 4}, "gold": 520},
    {"name": "천상의 코어", "atk": 86, "cost": {"천상 파편": 9, "얼음 결정": 5}, "gold": 900},
    {"name": "성운의 심장", "atk": 125, "cost": {"별빛 가루": 12, "천상 파편": 6}, "gold": 1600},
]


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    p = base / "CheonsangRPG"
    p.mkdir(parents=True, exist_ok=True)
    return p


def project_dir() -> Path:
    """Folder next to the source file or frozen EXE."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class OnlineAPI:
    """Small stdlib-only client for the shared Render account service."""
    def __init__(self):
        config_path = project_dir() / "server_config.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            config = {}
        self.base_url = str(config.get("api_url", "")).strip().rstrip("/")
        self.token = ""
        self.last_error = ""

    @property
    def configured(self):
        return bool(self.base_url)

    def request(self, path, payload=None, method=None):
        if not self.configured:
            raise RuntimeError("온라인 서버 주소가 설정되지 않았어.")
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers,
                                     method=method or ("POST" if data is not None else "GET"))
        try:
            with urllib.request.urlopen(req, timeout=75) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw) if raw else {}
            self.last_error = ""
            return result
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
                message = str(detail.get("message", f"HTTP {exc.code}"))
            except Exception:
                message = f"HTTP {exc.code}"
            self.last_error = message
            raise RuntimeError(message) from None
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            raise RuntimeError("온라인 서버에 연결할 수 없어. 서버 주소와 배포 상태를 확인해 줘.") from None

    def register(self, username, password, nickname):
        try:
            result = self.request("/api/register", {"username": username, "nickname": nickname, "password": password})
            return bool(result.get("ok")), result.get("message", "회원가입 완료")
        except RuntimeError as exc:
            return False, str(exc)

    def login(self, username, password):
        try:
            result = self.request("/api/login", {"username": username, "password": password})
            self.token = str(result.get("token", ""))
            row = result.get("user")
            return row, result.get("message", "로그인 성공!")
        except RuntimeError as exc:
            return None, str(exc)

    def logout(self):
        if self.token and self.configured:
            try:
                self.request("/api/logout", {})
            except RuntimeError:
                pass
        self.token = ""

    def save_player(self, player):
        if not self.token:
            return False
        try:
            self.request("/api/player/save", {
                "score": player.score, "gold": player.gold, "level": player.level,
                "exp": player.exp, "hp": player.hp, "max_hp": player.max_hp,
                "mp": player.mp, "max_mp": player.max_mp, "state": player.state,
            })
            return True
        except RuntimeError:
            return False

    def refresh_user(self, username):
        try:
            return self.request("/api/admin/users/" + urllib.parse.quote(username, safe="")) .get("user")
        except RuntimeError:
            return None

    def list_users(self, query=""):
        try:
            path = "/api/admin/users?q=" + urllib.parse.quote(query, safe="")
            return self.request(path).get("users", [])
        except RuntimeError:
            return []

    def admin_set_value(self, username, field, value):
        try:
            self.request("/api/admin/users/" + urllib.parse.quote(username, safe="") + "/update",
                         {"field": field, "value": int(value)})
            return True
        except RuntimeError:
            return False

    def set_ban(self, username, banned):
        try:
            self.request("/api/admin/users/" + urllib.parse.quote(username, safe="") + "/ban", {"banned": bool(banned)})
            return True
        except RuntimeError:
            return False

    def admin_grant_skills(self, username):
        try:
            self.request("/api/admin/users/" + urllib.parse.quote(username, safe="") + "/skills", {})
            return True
        except RuntimeError:
            return False

    def admin_heal(self, username):
        try:
            self.request("/api/admin/users/" + urllib.parse.quote(username, safe="") + "/heal", {})
            return True
        except RuntimeError:
            return False


class Database:
    def __init__(self):
        self.online = OnlineAPI()
        self.path = data_dir() / "game.db"
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, nickname TEXT NOT NULL DEFAULT '', salt BLOB NOT NULL, password_hash BLOB NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0,
            score INTEGER NOT NULL DEFAULT 0, gold INTEGER NOT NULL DEFAULT 120,
            level INTEGER NOT NULL DEFAULT 1, exp INTEGER NOT NULL DEFAULT 0,
            hp INTEGER NOT NULL DEFAULT 100, max_hp INTEGER NOT NULL DEFAULT 100,
            mp INTEGER NOT NULL DEFAULT 50, max_mp INTEGER NOT NULL DEFAULT 50,
            state TEXT NOT NULL DEFAULT '{}', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        self.conn.commit()
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(users)").fetchall()}
        if "nickname" not in columns:
            self.conn.execute("ALTER TABLE users ADD COLUMN nickname TEXT NOT NULL DEFAULT ''")
        self.conn.execute("UPDATE users SET nickname=username WHERE nickname IS NULL OR nickname='' ")
        self.conn.commit()
        self.ensure_admin()

    def ensure_admin(self):
        row = self.conn.execute("SELECT username FROM users WHERE username=?", (ADMIN_NAME,)).fetchone()
        if not row:
            self.conn.execute(
                "INSERT INTO users(username,nickname,salt,password_hash,is_admin,gold,max_hp,hp,max_mp,mp,state) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (ADMIN_NAME, ADMIN_NAME, ADMIN_SALT, ADMIN_HASH, 1, 9999, 150, 150, 100, 100, json.dumps(default_state(), ensure_ascii=False)),
            )
        else:
            self.conn.execute("UPDATE users SET is_admin=1 WHERE username=?", (ADMIN_NAME,))
        self.conn.commit()

    @staticmethod
    def hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)

    def register(self, username: str, password: str, nickname: str = "") -> tuple[bool, str]:
        username = username.strip()
        nickname = (nickname or username).strip()
        if self.online.configured:
            return self.online.register(username, password, nickname)
        if len(username) < 2 or len(username) > 12:
            return False, "아이디는 2~12글자로 만들어 줘."
        if not username or any(c in username for c in "\\/\n\r\t"):
            return False, "사용할 수 없는 아이디야."
        if len(password) < 4:
            return False, "비밀번호는 4글자 이상이어야 해."
        if not 2 <= len(nickname) <= 12 or any(c in nickname for c in "\\/\n\r\t"):
            return False, "닉네임은 2~12글자로 입력해 줘."
        if username == ADMIN_NAME:
            return False, "이미 사용할 수 없는 아이디야."
        salt = os.urandom(16)
        digest = self.hash_password(password, salt)
        try:
            self.conn.execute(
                "INSERT INTO users(username,nickname,salt,password_hash,state) VALUES(?,?,?,?,?)",
                (username, nickname, salt, digest, json.dumps(default_state(), ensure_ascii=False)),
            )
            self.conn.commit()
            return True, "회원가입이 완료됐어! 로그인해 줘."
        except sqlite3.IntegrityError:
            return False, "이미 사용 중인 아이디야."

    def login(self, username: str, password: str):
        if self.online.configured:
            return self.online.login(username.strip(), password)
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if not row:
            return None, "아이디 또는 비밀번호를 확인해 줘."
        if row["banned"]:
            return None, "이 계정은 현재 이용이 제한되어 있어."
        digest = self.hash_password(password, row["salt"])
        if not hmac.compare_digest(digest, row["password_hash"]):
            return None, "아이디 또는 비밀번호를 확인해 줘."
        return dict(row), "로그인 성공!"

    def refresh_user(self, username: str):
        if self.online.configured:
            return self.online.refresh_user(username)
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None

    def save_player(self, p):
        if self.online.configured:
            return self.online.save_player(p)
        self.conn.execute("""UPDATE users SET score=?,gold=?,level=?,exp=?,hp=?,max_hp=?,mp=?,max_mp=?,state=? WHERE username=?""",
                          (p.score, p.gold, p.level, p.exp, p.hp, p.max_hp, p.mp, p.max_mp,
                           json.dumps(p.state, ensure_ascii=False), p.username))
        self.conn.commit()

    def set_ban(self, username, banned):
        if username == ADMIN_NAME:
            return False
        if self.online.configured:
            return self.online.set_ban(username, banned)
        self.conn.execute("UPDATE users SET banned=? WHERE username=?", (int(banned), username))
        self.conn.commit()
        return True

    def set_score(self, username, score):
        """Set a user's score, including the administrator's own local account."""
        value = max(0, min(2_000_000_000, int(score)))
        cur = self.conn.execute("UPDATE users SET score=? WHERE username=?", (value, username))
        self.conn.commit()
        return cur.rowcount == 1

    def admin_set_value(self, username, field, value):
        """Change a selected account value from the administrator panel."""
        if self.online.configured:
            return self.online.admin_set_value(username, field, value)
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return False
        state = json.loads(row["state"] or "{}")
        defaults = default_state()
        for key, default_value in defaults.items():
            state.setdefault(key, default_value)
        state.setdefault("stats", {"strength": 0, "vitality": 0, "mana": 0, "agility": 0})
        numeric = int(value)
        if field in ("score", "gold", "level", "exp", "hp", "mp"):
            limits = {
                "score": (0, 2_000_000_000), "gold": (0, 2_000_000_000),
                "level": (1, 9999), "exp": (0, 2_000_000_000),
                "hp": (1, 2_000_000_000), "mp": (0, 2_000_000_000),
            }
            low, high = limits[field]
            numeric = max(low, min(high, numeric))
            if field == "level":
                old_level = int(row["level"])
                delta = numeric - old_level
                new_max_hp = max(1, int(row["max_hp"]) + delta * 12)
                new_max_mp = max(0, int(row["max_mp"]) + delta * 5)
                self.conn.execute(
                    "UPDATE users SET level=?,exp=0,max_hp=?,max_mp=?,hp=MIN(hp,?),mp=MIN(mp,?) WHERE username=?",
                    (numeric, new_max_hp, new_max_mp, new_max_hp, new_max_mp, username),
                )
            elif field == "hp":
                numeric = min(numeric, int(row["max_hp"]))
                self.conn.execute("UPDATE users SET hp=? WHERE username=?", (numeric, username))
            elif field == "mp":
                numeric = min(numeric, int(row["max_mp"]))
                self.conn.execute("UPDATE users SET mp=? WHERE username=?", (numeric, username))
            else:
                self.conn.execute(f"UPDATE users SET {field}=? WHERE username=?", (numeric, username))
        elif field == "stat_points":
            state["stat_points"] = max(0, min(2_000_000_000, numeric))
            self.conn.execute("UPDATE users SET state=? WHERE username=?", (json.dumps(state, ensure_ascii=False), username))
        elif field == "core":
            state["mana_core_level"] = max(0, min(100, numeric))
            self.conn.execute("UPDATE users SET state=? WHERE username=?", (json.dumps(state, ensure_ascii=False), username))
        elif field in ("strength", "vitality", "mana", "agility"):
            old_value = int(state["stats"].get(field, 0))
            new_value = max(0, min(1_000_000, numeric))
            diff = new_value - old_value
            if field == "vitality" and diff:
                new_max = max(1, int(row["max_hp"]) + diff * 20)
                new_hp = max(1, min(new_max, int(row["hp"]) + diff * 20))
                self.conn.execute("UPDATE users SET max_hp=?,hp=? WHERE username=?", (new_max, new_hp, username))
            elif field == "mana" and diff:
                new_max = max(0, int(row["max_mp"]) + diff * 10)
                new_mp = max(0, min(new_max, int(row["mp"]) + diff * 10))
                self.conn.execute("UPDATE users SET max_mp=?,mp=? WHERE username=?", (new_max, new_mp, username))
            state["stats"][field] = new_value
            self.conn.execute("UPDATE users SET state=? WHERE username=?", (json.dumps(state, ensure_ascii=False), username))
        else:
            return False
        self.conn.commit()
        return True

    def admin_grant_skills(self, username):
        if self.online.configured:
            return self.online.admin_grant_skills(username)
        row = self.conn.execute("SELECT state FROM users WHERE username=?", (username,)).fetchone()
        if not row:
            return False
        state = json.loads(row["state"] or "{}")
        books = state.setdefault("skill_books", [])
        learned = state.setdefault("learned_skills", [])
        grants = ["이상한 스킬", "화염구", "별빛 돌진", "별빛 파동", "마나 감지", "투명 감지"]
        # Even the administrator's grant action awards books, not pre-learned skills.
        for skill in grants:
            book = skill + " 스킬북"
            if skill not in learned and book not in books:
                books.append(book)
        self.conn.execute("UPDATE users SET state=? WHERE username=?", (json.dumps(state, ensure_ascii=False), username))
        self.conn.commit()
        return True

    def admin_heal(self, username):
        if self.online.configured:
            return self.online.admin_heal(username)
        cur = self.conn.execute("UPDATE users SET hp=max_hp,mp=max_mp WHERE username=?", (username,))
        self.conn.commit()
        return cur.rowcount == 1

    def list_users(self, query=""):
        if self.online.configured:
            return self.online.list_users(query)
        pattern = f"%{query}%"
        return [dict(r) for r in self.conn.execute("SELECT username,nickname,is_admin,banned,score,level,gold FROM users WHERE username LIKE ? OR nickname LIKE ? ORDER BY is_admin DESC, score DESC", (pattern, pattern))]


def default_state():
    return {
        "materials": {"풀잎 조각": 3},
        "inventory": ["작은 회복 물약", "작은 회복 물약"],
        "gear": {"name": "초보자 별빛 오브", "atk": 4, "enhance": 0},
        "items": [],
        "unlocked": ["풀숲"],
        "special": [],
        "learned_skills": [],
        "skill_books": [],
        "equipped_skills": {},
        "stats": {"strength": 0, "vitality": 0, "mana": 0, "agility": 0},
        "stat_points": 5,
        "mana_core_level": 0,
        "mana_detection": 0,
        "potions": 5,
        "first_intro": True,
    }


class Player:
    def __init__(self, row):
        self.username = row["username"]
        self.nickname = str(row.get("nickname") or self.username)
        self.is_admin = bool(row["is_admin"])
        self.score = int(row["score"])
        self.gold = int(row["gold"])
        self.level = int(row["level"])
        self.exp = int(row["exp"])
        self.hp = int(row["hp"])
        self.max_hp = int(row["max_hp"])
        self.mp = int(row["mp"])
        self.max_mp = int(row["max_mp"])
        try:
            self.state = json.loads(row.get("state") or "{}")
        except Exception:
            self.state = default_state()
        base = default_state()
        for k, v in base.items():
            self.state.setdefault(k, v)
        self.state.setdefault("materials", {})
        self.state.setdefault("special", [])
        self.state.setdefault("skill_books", [])
        self.state.setdefault("learned_skills", [])
        self.state.setdefault("equipped_skills", {})
        # Migrate legacy skill flags into skill books instead of auto-learning them.
        # Quest items such as "수상한 종이" remain in special; earned skills must
        # be learned explicitly from B > 배우기 before their hotkeys can be used.
        legacy_skill_names = ("이상한 스킬", "화염구", "별빛 돌진", "별빛 파동", "마나 감지", "마나 순환", "투명 감지")
        legacy_books = self.state.setdefault("skill_books", [])
        for old_skill in legacy_skill_names:
            if old_skill in self.state["special"]:
                if old_skill not in self.state["learned_skills"]:
                    # Mana Circulation can only evolve from Mana Detection.
                    migrated_book_skill = "마나 감지" if old_skill == "마나 순환" else old_skill
                    migrated_book = migrated_book_skill + " 스킬북"
                    if migrated_book not in legacy_books:
                        legacy_books.append(migrated_book)
                self.state["special"].remove(old_skill)
        # Older saves may have only stored a skill in its hotkey slot.
        for skill_name in list(self.state["equipped_skills"].values()):
            if skill_name in legacy_skill_names and skill_name not in self.state["learned_skills"]:
                migrated_book_skill = "마나 감지" if skill_name == "마나 순환" else skill_name
                migrated_book = migrated_book_skill + " 스킬북"
                if migrated_book not in legacy_books:
                    legacy_books.append(migrated_book)
        # Remove stale hotkey assignments for skills that have not been learned.
        for hotkey, skill_name in list(self.state["equipped_skills"].items()):
            if skill_name not in self.state["learned_skills"]:
                self.state["equipped_skills"].pop(hotkey, None)
        self.state.setdefault("unlocked", ["풀숲"])
        self.state.setdefault("gear", base["gear"].copy())
        self.state.setdefault("stats", base["stats"].copy())
        for stat_name in ("strength", "vitality", "mana", "agility"):
            self.state["stats"].setdefault(stat_name, 0)
        self.state.setdefault("stat_points", base["stat_points"])
        self.state.setdefault("mana_core_level", 0)
        self.state.setdefault("mana_detection", 0)
        self.state.setdefault("final_boss_defeated", False)
        self.x, self.y = 800.0, 550.0
        self.zone = "천상 마을"
        self.attack_cd = 0.0
        self.skill_cd = 0.0
        self.invuln = 0.0
        self.flash = 0.0
        self.facing = (1, 0)
        self.message = "천상 마을에 온 걸 환영해!"
        self.message_until = time.time() + 4
        self.kills = 0
        self.mana_skill_cd = 0.0
        self.mana_circulation_until = 0.0

    @property
    def attack(self):
        stats = self.state.get("stats", {})
        strength = int(stats.get("strength", 0))
        core_level = int(self.state.get("mana_core_level", 0))
        base = 10 + self.level * 2 + int(self.state.get("gear", {}).get("atk", 0)) + int(self.state.get("gear", {}).get("enhance", 0)) * 4 + strength * 5
        core_multiplier = 1.5 ** max(0, core_level)
        if time.time() < self.mana_circulation_until:
            core_multiplier *= 1.75
        return int(base * core_multiplier)

    def say(self, text, seconds=3):
        self.message = text
        self.message_until = time.time() + seconds

    def add_material(self, name, amount=1):
        mats = self.state.setdefault("materials", {})
        mats[name] = int(mats.get(name, 0)) + amount

    def add_exp(self, amount):
        self.exp += amount
        while self.exp >= self.level * 100:
            self.exp -= self.level * 100
            self.level += 1
            self.max_hp += 12
            self.max_mp += 5
            self.hp = self.max_hp
            self.mp = self.max_mp
            self.score += 50
            self.state["stat_points"] = int(self.state.get("stat_points", 0)) + 3
            self.say(f"레벨 업! Lv.{self.level}! 스탯 포인트 3개를 얻었어.", 4)


class Enemy:
    def __init__(self, name, x, y, level_boost=0):
        hp, atk, exp, gold = MONSTER_STATS[name]
        self.name = name
        self.max_hp = hp + level_boost * 12
        self.hp = self.max_hp
        self.atk = atk + level_boost * 2
        self.exp = exp + level_boost * 5
        self.gold = gold + level_boost * 3
        self.x, self.y = float(x), float(y)
        self.is_boss = name == FINAL_BOSS
        self.radius = 54 if self.is_boss else (20 if "수호자" not in name and "골렘" not in name else 27)
        self.aggressive = name != "빛의 돌덩이"
        self.cooldown = random.uniform(0.2, 1.4)
        self.dead = False
        self.hit = 0
        self.seed = random.random() * 20


class Button:
    def __init__(self, rect, label, callback, active=True, accent=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.active = active
        self.accent = accent


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("천상 RPG")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.db = Database()
        self.font = self.pick_font(20)
        self.small = self.pick_font(15)
        self.tiny = self.pick_font(12)
        self.big = self.pick_font(36)
        self.title = self.pick_font(52)
        self.scene = "login"
        self.auth_mode = "login"
        self.username_input = ""
        self.nickname_input = ""
        self.password_input = ""
        self.active_input = "username"
        # Korean IME support: committed characters arrive through SDL TEXTINPUT;
        # in-progress Hangul composition arrives through TEXTEDITING.
        self.text_composition = ""
        self.text_input_started = False
        self.start_login_text_input()
        self.notice = "계정을 만들거나 로그인해 줘."
        self.player: Player | None = None
        self.enemies: list[Enemy] = []
        self.modal = ""
        self.buttons: list[Button] = []
        self.last_save = time.time()
        self.admin_users = []
        self.admin_current = None
        self.admin_search_input = ""
        self.admin_search_focus = False
        self.admin_selected = ""
        self.admin_score_input = ""
        self.admin_score_focus = False
        self.admin_edit_field = "score"
        self.admin_edit_input = ""
        self.admin_value_focus = False
        self.admin_scroll = 0
        self.toast = ""
        self.toast_until = 0
        self.zone_decor = {}
        self.random_seed = random.Random(31)
        self.spawn_timer = 0.0
        self.running = True
        self.spawn_enemies()

    def start_login_text_input(self):
        """Enable OS text input/IME while the login form is active."""
        try:
            if hasattr(pygame.key, "start_text_input"):
                pygame.key.start_text_input()
                self.text_input_started = True
            self.update_ime_rect()
        except Exception:
            # The normal ASCII keyboard path still works if SDL IME APIs are absent.
            self.text_input_started = False

    def stop_login_text_input(self):
        try:
            if self.text_input_started and hasattr(pygame.key, "stop_text_input"):
                pygame.key.stop_text_input()
        except Exception:
            pass
        self.text_input_started = False
        self.text_composition = ""

    def update_ime_rect(self):
        """Place the Windows IME candidate/composition window near the active field."""
        try:
            if not hasattr(pygame.key, "set_text_input_rect"):
                return
            if self.auth_mode == "register":
                rects = {
                    "username": pygame.Rect(388, 334, 324, 43),
                    "nickname": pygame.Rect(388, 411, 324, 43),
                    "password": pygame.Rect(388, 488, 324, 43),
                }
            else:
                rects = {
                    "username": pygame.Rect(388, 407, 324, 43),
                    "password": pygame.Rect(388, 492, 324, 43),
                }
            pygame.key.set_text_input_rect(rects.get(self.active_input, rects["username"]))
        except Exception:
            pass

    def insert_text_input(self, value):
        """Insert committed OS text input for login fields or admin score."""
        if not value:
            return
        if self.scene == "game" and self.modal == "admin" and self.admin_search_focus:
            clean = "".join(ch for ch in value if ch.isprintable() and ch not in "\r\n\t")
            if clean:
                self.admin_search_input = (self.admin_search_input + clean)[:24]
            return
        if self.scene == "game" and self.modal == "admin" and self.admin_score_focus:
            digits = "".join(ch for ch in value if ch.isdecimal())
            if digits:
                self.admin_edit_input = (self.admin_edit_input + digits)[:10]
            return
        if self.scene != "login":
            return
        clean = "".join(ch for ch in value if ch.isprintable() and ch not in "\r\n\t")
        if not clean:
            return
        if self.active_input == "username":
            room = max(0, 12 - len(self.username_input))
            self.username_input += clean[:room]
        elif self.active_input == "nickname":
            room = max(0, 12 - len(self.nickname_input))
            self.nickname_input += clean[:room]
        elif self.active_input == "password":
            room = max(0, 64 - len(self.password_input))
            self.password_input += clean[:room]
        self.text_composition = ""

    def pick_font(self, size):
        candidates = ["malgungothic", "맑은 고딕", "notosanscjktcregular", "noto sans cjk kr", "nanumgothic", "arial"]
        for name in candidates:
            f = pygame.font.SysFont(name, size)
            if f:
                return f
        return pygame.font.Font(None, size)

    def text(self, surface, value, x, y, color=WHITE, font=None, anchor="topleft"):
        font = font or self.font
        s = font.render(str(value), True, color)
        r = s.get_rect()
        setattr(r, anchor, (int(x), int(y)))
        surface.blit(s, r)
        return r

    def panel(self, rect, fill=PANEL_BG, border=PANEL_EDGE, radius=18, width=1):
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        pygame.draw.rect(self.screen, border, rect, width, border_radius=radius)

    def button(self, rect, label, callback, active=True, accent=False):
        b = Button(rect, label, callback, active, accent)
        self.buttons.append(b)
        bg = (66, 121, 157) if accent else (45, 59, 83)
        if not active:
            bg = (43, 48, 61)
        pygame.draw.rect(self.screen, bg, b.rect, border_radius=10)
        pygame.draw.rect(self.screen, (93, 127, 165) if active else (62, 69, 83), b.rect, 1, border_radius=10)
        self.text(self.screen, label, b.rect.centerx, b.rect.centery, WHITE if active else MUTED, self.small, "center")
        return b

    def toast_msg(self, msg, duration=3):
        self.toast = msg
        self.toast_until = time.time() + duration

    def spawn_enemies(self):
        self.enemies = []
        if not self.player or self.player.zone == "천상 마을":
            return
        names = ZONE_BY_NAME.get(self.player.zone, ZONES[0])["enemies"]
        count = 10 if self.player.zone != "2세계 · 별빛 황야" else 8
        if self.player.zone == "2세계 · 별빛 황야":
            names = ["성운 슬라임", "공허 정찰자"]
        for i in range(count):
            name = random.choice(names)
            if name == "빛의 돌덩이" and i > 2:
                name = "화염의 좀비"
            x = random.randint(140, MAP_W - 140)
            y = random.randint(140, MAP_H - 140)
            self.enemies.append(Enemy(name, x, y, max(0, self.player.level - 1) // 4))
        if self.player.zone == "샌드 사막":
            # Keep the pyramid guardian available so the second-world quest can always progress.
            self.enemies.append(Enemy("피라미드 수호자", 1320, 260, max(0, self.player.level - 4) // 4))
        if self.player.zone == "2세계 · 별빛 황야":
            # A guaranteed Ancient Guardian makes the invisibility-detection quest completable.
            self.enemies.append(Enemy("고대 수호자", 1250, 820, max(0, self.player.level - 12) // 4))
            if "투명 감지" in self.player.state.get("learned_skills", []) and not self.player.state.get("final_boss_defeated"):
                if not any(e.is_boss and not e.dead for e in self.enemies):
                    self.enemies.append(Enemy(FINAL_BOSS, 1370, 250, 0))
        self.spawn_timer = 0.0

    def enter_game(self, row):
        self.stop_login_text_input()
        self.player = Player(row)
        self.scene = "game"
        self.modal = ""
        if self.player.state.get("first_intro", True):
            self.player.say("안내자: 천상 마을에서 준비한 뒤 풀숲부터 탐험해 보자!", 6)
            self.player.state["first_intro"] = False
        self.enter_zone("천상 마을", save=False)
        self.player.x, self.player.y = 800, 550

    def enter_zone(self, zone, save=True):
        if not self.player:
            return
        self.player.zone = zone
        self.player.x, self.player.y = (800.0, 550.0)
        if zone == "천상 마을":
            self.player.hp = min(self.player.max_hp, self.player.hp + 35)
            self.player.mp = min(self.player.max_mp, self.player.mp + 25)
        self.spawn_enemies()
        if zone != "천상 마을":
            self.player.say(f"{zone}에 도착했어. SPACE: 기본 공격 · E/R/T/J/K: 배운 스킬", 4)
        else:
            self.player.say("천상 마을이야. 건물을 클릭해 시설을 이용해 봐!", 4)
        if save:
            self.db.save_player(self.player)

    def register_login(self):
        if self.auth_mode == "login":
            row, msg = self.db.login(self.username_input, self.password_input)
            self.notice = msg
            if row:
                self.enter_game(row)
        else:
            ok, msg = self.db.register(self.username_input, self.password_input, self.nickname_input)
            self.notice = msg
            if ok:
                self.auth_mode = "login"
                self.nickname_input = ""
                self.password_input = ""
                self.active_input = "password"
                self.text_composition = ""
                self.update_ime_rect()

    def add_skill_book(self, skill_name):
        p = self.player
        if not p:
            return
        books = p.state.setdefault("skill_books", [])
        learned = p.state.setdefault("learned_skills", [])
        book_name = skill_name + " 스킬북"
        if skill_name in learned or book_name in books:
            return
        books.append(book_name)
        p.say(f"스킬북 획득: {book_name}! B키로 스킬 창을 열어 배워 봐.", 6)

    def add_loot(self, enemy):
        p = self.player
        p.kills += 1
        p.gold += enemy.gold
        p.score += max(1, enemy.exp // 2)
        p.add_exp(enemy.exp)
        mat = MATERIAL_FOR_ZONE.get(p.zone, "별빛 가루")
        p.add_material(mat, random.randint(1, 3))
        if random.random() < 0.32:
            p.state["potions"] = int(p.state.get("potions", 0)) + 1

        # Skill books must be found and learned from the Skill Book window.
        if p.zone == "풀숲" and enemy.name in ("슬라임", "좀비", "갑옷 좀비") and random.random() < 0.24:
            self.add_skill_book("별빛 파동")
        if p.zone == "샌드 사막":
            if enemy.name in ("미라", "샌드 수호자", "피라미드 수호자") and "수상한 종이" not in p.state["special"]:
                if enemy.name == "피라미드 수호자" or random.random() < 0.34:
                    p.state["special"].append("수상한 종이")
                    p.say("희귀 아이템 획득: 수상한 종이!", 5)
            if enemy.name == "피라미드 수호자":
                self.add_skill_book("이상한 스킬")
        if p.zone == "빛의 동굴" and enemy.name == "화염의 좀비":
            self.add_skill_book("화염구")
        if p.zone == "메이플 공원" and enemy.name == "메이플 사무라이":
            if random.random() < 0.3:
                self.add_skill_book("별빛 돌진")
        if p.zone == "2세계 · 별빛 황야":
            if enemy.name in ("성운 슬라임", "공허 정찰자"):
                # The first defeated monster in the second world guarantees the Mana Detection book.
                learned_now = set(p.state.get("learned_skills", []))
                if not ({"마나 감지", "마나 순환"} & learned_now):
                    self.add_skill_book("마나 감지")
            if enemy.name == "고대 수호자":
                self.add_skill_book("투명 감지")
            if enemy.is_boss:
                p.state["final_boss_defeated"] = True
                p.state["special"].append("파멸의 용핵") if "파멸의 용핵" not in p.state["special"] else None
                p.score += 10000
                p.gold += 25000
                p.add_material("마나석", 20)
                p.say("최종 보스 격파! 천상 RPG의 최종 시련을 넘어섰어!", 10)
            elif random.random() < 0.85 or enemy.name == "고대 수호자":
                p.add_material("마나석", random.randint(1, 3 if enemy.name == "고대 수호자" else 2))
        self.toast_msg(f"{enemy.name} 처치! +{enemy.exp} EXP · +{enemy.gold} 골드")
        self.db.save_player(p)

    def basic_attack(self):
        p = self.player
        if not p or p.zone == "천상 마을" or p.attack_cd > 0:
            return
        p.attack_cd = 0.38
        self.damage_nearby(96, 1.0, 1, "기본 공격")

    def damage_nearby(self, reach, multiplier, limit, skill_name):
        p = self.player
        if not p or p.zone == "천상 마을":
            return
        can_see_invisible = "투명 감지" in p.state.get("learned_skills", [])
        candidates = [(math.hypot(e.x-p.x, e.y-p.y), e) for e in self.enemies
                      if not e.dead and (not e.is_boss or can_see_invisible)]
        candidates = [(d,e) for d,e in candidates if d <= reach]
        if not candidates:
            p.say("주변에 대상이 없어.", 1)
            return
        candidates.sort(key=lambda pair: pair[0])
        for _, enemy in candidates[:limit]:
            damage = int(p.attack * multiplier + random.randint(0, max(2,p.level)))
            enemy.hp -= damage
            enemy.hit = 0.22
            if enemy.hp <= 0:
                enemy.dead = True
                self.add_loot(enemy)
        p.say(f"{skill_name}!", 1)

    def use_learned_skill(self, skill_name):
        p = self.player
        if not p or p.zone == "천상 마을":
            return
        learned = p.state.get("learned_skills", [])
        if skill_name not in learned:
            p.say(f"{skill_name} 스킬북을 얻고 B키에서 배워야 해.", 2.5)
            return
        if skill_name == "마나 감지" or skill_name == "마나 순환":
            self.use_mana_skill()
            return
        if skill_name == "이상한 스킬":
            if p.skill_cd > 0 or p.mp < 18:
                p.say("재사용 대기 중이거나 마나가 부족해.", 2)
                return
            p.mp -= 18
            p.skill_cd = 2.1
            self.damage_nearby(175, 2.8, 3, skill_name)
            return
        if skill_name == "별빛 파동":
            if p.skill_cd > 0 or p.mp < 12:
                p.say("재사용 대기 중이거나 마나가 부족해.", 2)
                return
            p.mp -= 12
            p.skill_cd = 1.6
            self.damage_nearby(150, 2.15, 3, skill_name)
            return
        if skill_name == "화염구":
            if p.skill_cd > 0 or p.mp < 22:
                p.say("재사용 대기 중이거나 마나가 부족해.", 2)
                return
            p.mp -= 22
            p.skill_cd = 2.8
            self.damage_nearby(300, 2.3, 2, skill_name)
            return
        if skill_name == "별빛 돌진":
            if p.skill_cd > 0 or p.mp < 15:
                p.say("재사용 대기 중이거나 마나가 부족해.", 2)
                return
            p.mp -= 15
            p.skill_cd = 2.4
            p.x = max(40, min(MAP_W-40, p.x + p.facing[0]*150))
            p.y = max(40, min(MAP_H-40, p.y + p.facing[1]*150))
            self.damage_nearby(105, 1.8, 2, skill_name)
            return
        if skill_name == "투명 감지":
            p.say("투명 감지는 패시브 스킬이야. 숨겨진 드래곤을 볼 수 있어.", 2.5)
            return

    def learn_skill_book(self, book_name):
        p = self.player
        if not p:
            return
        book_map = {
            "이상한 스킬 스킬북": "이상한 스킬", "화염구 스킬북": "화염구",
            "별빛 돌진 스킬북": "별빛 돌진", "별빛 파동 스킬북": "별빛 파동",
            "마나 감지 스킬북": "마나 감지", "투명 감지 스킬북": "투명 감지",
        }
        skill = book_map.get(book_name)
        books = p.state.setdefault("skill_books", [])
        learned = p.state.setdefault("learned_skills", [])
        if not skill or book_name not in books or skill in learned:
            return
        books.remove(book_name)
        learned.append(skill)
        special = p.state.setdefault("special", [])
        if skill not in special:
            special.append(skill)
        key_for = {"이상한 스킬":"E", "화염구":"R", "마나 감지":"T", "별빛 돌진":"J", "별빛 파동":"K"}
        if skill in key_for:
            p.state.setdefault("equipped_skills", {})[key_for[skill]] = skill
        if skill == "마나 감지":
            p.state.setdefault("mana_detection", 0)
        if skill == "투명 감지" and not p.state.get("final_boss_defeated"):
            if not any(e.is_boss and not e.dead for e in self.enemies):
                self.enemies.append(Enemy(FINAL_BOSS, 1370, 250, 0))
        p.say(f"{skill} 스킬을 배웠어! {key_for.get(skill, '패시브')} 슬롯에 등록됐어.", 5)
        self.db.save_player(p)

    def use_mana_skill(self):
        """T: consume mana to detect mana, then activate Mana Circulation."""
        p = self.player
        if not p:
            return
        special = p.state.setdefault("special", [])
        learned = p.state.setdefault("learned_skills", [])
        if "마나 감지" in learned:
            if p.mana_skill_cd > 0:
                p.say(f"마나 감지 재사용 대기: {p.mana_skill_cd:.1f}초", 1.2)
                return
            drained = int(p.mp)
            if drained <= 0:
                p.say("감지할 마나가 없어. 마나가 회복되면 T를 눌러 봐.", 2)
                return
            p.mp = 0
            current = int(p.state.get("mana_detection", 0))
            gained = drained * 100
            p.state["mana_detection"] = min(10000, current + gained)
            p.mana_skill_cd = 2.0
            if p.state["mana_detection"] >= 10000:
                learned.remove("마나 감지")
                if "마나 순환" not in learned:
                    learned.append("마나 순환")
                if "마나 감지" in special:
                    special.remove("마나 감지")
                if "마나 순환" not in special:
                    special.append("마나 순환")
                p.state.setdefault("equipped_skills", {})["T"] = "마나 순환"
                p.say("마나 감지 10,000 달성! 스킬이 '마나 순환'으로 진화했어!", 7)
            else:
                p.say(f"마나 감지량 +{gained:,}  ·  {p.state['mana_detection']:,}/10,000", 3)
            self.db.save_player(p)
        elif "마나 순환" in learned:
            if p.mana_skill_cd > 0:
                p.say(f"마나 순환 재사용 대기: {p.mana_skill_cd:.1f}초", 1.2)
                return
            cost = min(30, p.max_mp)
            if p.mp < cost:
                p.say(f"마나 순환에는 마나 {cost}가 필요해.", 2)
                return
            p.mp -= cost
            p.mana_circulation_until = time.time() + 12
            p.mana_skill_cd = 16
            p.say("마나 순환 발동! 12초 동안 공격력이 크게 상승해.", 4)
            self.db.save_player(p)
        else:
            p.say("마나 감지 스킬북을 얻고 B키에서 배워야 해.", 3)

    def allocate_stat(self, stat_name, amount=1):
        p = self.player
        if not p or stat_name not in ("strength", "vitality", "mana", "agility"):
            return
        amount = max(1, int(amount))
        points = int(p.state.get("stat_points", 0))
        if points < amount:
            p.say("스탯 포인트가 부족해.", 2)
            return
        p.state["stat_points"] = points - amount
        p.state["stats"][stat_name] = int(p.state["stats"].get(stat_name, 0)) + amount
        if stat_name == "vitality":
            p.max_hp += amount * 20
            p.hp += amount * 20
        elif stat_name == "mana":
            p.max_mp += amount * 10
            p.mp += amount * 10
        label = {"strength": "힘", "vitality": "체력", "mana": "마나", "agility": "민첩"}[stat_name]
        p.say(f"{label} 스탯을 {amount} 올렸어!", 2)
        self.db.save_player(p)

    def upgrade_mana_core(self):
        p = self.player
        if not p:
            return
        level = int(p.state.get("mana_core_level", 0))
        stone_cost = 3 + level * 2
        gold_cost = 200 + level * 300
        if not self.pay({"마나석": stone_cost}, gold_cost):
            p.say(f"마나석 {stone_cost}개와 골드 {gold_cost:,}가 필요해.", 3)
            return
        p.state["mana_core_level"] = level + 1
        p.state["stat_points"] = int(p.state.get("stat_points", 0)) + 10
        p.say(f"마나 코어 Lv.{level+1} 달성! 스탯 포인트 10개 충전 완료!", 5)
        self.db.save_player(p)

    def use_potion(self):
        p = self.player
        if not p:
            return
        potions = int(p.state.get("potions", 0))
        if potions <= 0:
            p.say("회복 물약이 없어. 마을에서 준비하자.", 2)
            return
        if p.hp >= p.max_hp:
            p.say("체력이 이미 가득 찼어.", 2)
            return
        p.state["potions"] = potions - 1
        p.hp = min(p.max_hp, p.hp + 55)
        p.say("회복 물약을 사용했어!", 2)
        self.db.save_player(p)

    def handle_interact(self):
        p = self.player
        if not p:
            return
        if p.zone != "천상 마을" and math.hypot(p.x - 800, p.y - 550) < 78:
            self.travel_to_town()
            return
        if p.zone == "천상 마을":
            # Interaction near one of the town stalls.
            stalls = [(520, 310, "craft"), (1080, 310, "combine"), (520, 820, "disassemble"), (1080, 820, "enhance"), (800, 950, "potion"), (800,700,"core")]
            nearest = min(stalls, key=lambda a: math.hypot(p.x-a[0], p.y-a[1]))
            if math.hypot(p.x-nearest[0], p.y-nearest[1]) < 135:
                self.modal = nearest[2]
            else:
                self.modal = "map"
            return
        if p.zone == "동굴" and math.hypot(p.x - 1380, p.y - 880) < 110:
            if "빛의 동굴" not in p.state["unlocked"]:
                p.state["unlocked"].append("빛의 동굴")
            self.enter_zone("빛의 동굴")
            return
        if p.zone == "샌드 사막" and math.hypot(p.x - 1390, p.y - 155) < 120:
            required = {"수상한 종이"}
            missing = required - set(p.state.get("special", []))
            if "이상한 스킬" not in p.state.get("learned_skills", []):
                missing.add("이상한 스킬 스킬을 배우기")
            if missing:
                p.say("피라미드 문이 잠겨 있어. 필요한 것: " + ", ".join(sorted(missing)), 4)
            else:
                if "2세계 · 별빛 황야" not in p.state["unlocked"]:
                    p.state["unlocked"].append("2세계 · 별빛 황야")
                self.travel_special("2세계 · 별빛 황야")
            return
        p.say("상호작용할 대상이 가까이에 없어. H키로 천상 마을에 돌아갈 수 있어.", 3)

    def draw_background(self, zone):
        z = ZONE_BY_NAME.get(zone)
        bg = z["bg"] if z else (74, 105, 104)
        ground = z["ground"] if z else (111, 149, 125)
        accent = z["accent"] if z else (205, 220, 167)
        self.screen.fill(DARK)
        camx = max(0, min(MAP_W - VIEW.w, int(self.player.x - VIEW.w / 2)))
        camy = max(0, min(MAP_H - VIEW.h, int(self.player.y - VIEW.h / 2)))
        surf = pygame.Surface((VIEW.w, VIEW.h))
        surf.fill(bg)
        # soft terrain tiles
        for y in range(-((camy // 90) * 90 - camy), VIEW.h, 90):
            for x in range(-((camx // 90) * 90 - camx), VIEW.w, 90):
                ix = ((x + camx) // 90)
                iy = ((y + camy) // 90)
                col = tuple(max(0, min(255, c + ((ix * 17 + iy * 13) % 13 - 6))) for c in ground)
                pygame.draw.rect(surf, col, (x, y, 86, 86), border_radius=8)
        for i in range(28):
            px = (i * 197 + 71) % MAP_W - camx
            py = (i * 137 + 43) % MAP_H - camy
            if -30 < px < VIEW.w + 30 and -30 < py < VIEW.h + 30:
                pygame.draw.circle(surf, accent, (px, py), 2 + i % 3)
        # A guaranteed return shrine exists in every field region. It is placed
        # at the arrival point so a player can always press F or H to return.
        if zone != "천상 마을":
            rx, ry = 800-camx, 550-camy
            pygame.draw.circle(surf, (35, 25, 67), (rx, ry), 48)
            pygame.draw.circle(surf, (165, 130, 255), (rx, ry), 43, 4)
            pygame.draw.circle(surf, (225, 213, 255), (rx, ry), 27, 2)
            self.text(surf, "천상 마을 귀환석 [F/H]", rx, ry-62, (238, 226, 255), self.tiny, "center")
        # field landmark for special transition
        if zone == "동굴":
            hx, hy = 1380-camx, 880-camy
            pygame.draw.ellipse(surf, (18, 23, 37), (hx-62, hy-33, 124, 66))
            pygame.draw.ellipse(surf, (151, 215, 242), (hx-62, hy-33, 124, 66), 3)
            self.text(surf, "빛의 동굴", hx, hy-58, (230, 248, 255), self.small, "center")
        if zone == "샌드 사막":
            px, py = 1390-camx, 155-camy
            pygame.draw.polygon(surf, (121, 84, 64), [(px-70,py+35),(px,py-70),(px+70,py+35)])
            pygame.draw.polygon(surf, (231, 193, 117), [(px-53,py+25),(px,py-50),(px+53,py+25)])
            pygame.draw.rect(surf, (101, 73, 57), (px-15,py-2,30,28))
            self.text(surf, "피라미드 입구 [F]", px, py+52, WHITE, self.tiny, "center")
        if zone == "천상 마을":
            self.draw_town(surf, camx, camy)
        else:
            # decorative crystals / ruins
            for i in range(7):
                px = (210 + i*207) - camx
                py = (245 + (i%3)*223) - camy
                if -60 < px < VIEW.w+60 and -60 < py < VIEW.h+60:
                    pygame.draw.polygon(surf, (accent[0]//2, accent[1]//2, accent[2]//2), [(px,py-24),(px+16,py),(px,py+24),(px-16,py)])
                    pygame.draw.polygon(surf, accent, [(px,py-24),(px+5,py),(px,py+24)])
        self.screen.blit(surf, VIEW.topleft)
        return camx, camy

    def draw_town(self, surf, camx, camy):
        # walkable village plaza and five interactive buildings
        pygame.draw.rect(surf, (131, 121, 104), (450-camx, 360-camy, 680, 260), border_radius=80)
        buildings = [
            (520,310,"장비 제작소",(134,91,79)), (1080,310,"조합소",(93,119,147)),
            (520,820,"분해소",(110,120,102)), (1080,820,"강화소",(126,102,151)),
            (800,160,"지역 게시판",(170,135,75)), (800,950,"물약 상점",(89,139,111)),
            (800,700,"마나 코어",(116,86,163)),
        ]
        for x,y,label,color in buildings:
            sx, sy = x-camx, y-camy
            pygame.draw.rect(surf, (48,51,64), (sx-58,sy-43,116,86), border_radius=12)
            pygame.draw.rect(surf, color, (sx-52,sy-50,104,86), border_radius=12)
            pygame.draw.polygon(surf, (66,55,57), [(sx-63,sy-50),(sx,sy-94),(sx+63,sy-50)])
            pygame.draw.rect(surf, (69,52,43), (sx-14,sy-12,28,48), border_radius=5)
            self.text(surf, label, sx, sy+47, WHITE, self.tiny, "midtop")
        pygame.draw.circle(surf, (111, 186, 231), (800-camx, 550-camy), 55, 3)
        self.text(surf, "출발 광장", 800-camx, 610-camy, WHITE, self.small, "midtop")

    def draw_player_sprite(self, surface, sx, sy):
        # Simple original pixel-like avatar; no external assets required.
        pygame.draw.ellipse(surface, (20, 27, 38), (sx-15, sy+14, 30, 10))
        pygame.draw.rect(surface, (48, 89, 147), (sx-12, sy-3, 24, 25), border_radius=7)
        pygame.draw.circle(surface, (244, 204, 164), (sx, sy-12), 12)
        pygame.draw.arc(surface, (229, 226, 250), (sx-12, sy-24, 24, 19), math.pi, math.tau, 5)
        pygame.draw.circle(surface, (35, 42, 58), (sx-4, sy-13), 2)
        pygame.draw.circle(surface, (35, 42, 58), (sx+4, sy-13), 2)
        pygame.draw.rect(surface, (223, 188, 103), (sx-8, sy+18, 7, 8), border_radius=2)
        pygame.draw.rect(surface, (223, 188, 103), (sx+1, sy+18, 7, 8), border_radius=2)

    def draw_enemy(self, surface, enemy, camx, camy):
        sx, sy = int(enemy.x-camx), int(enemy.y-camy)
        if enemy.is_boss:
            # Original pixel-art-like silhouette for the invisible final dragon.
            pygame.draw.ellipse(surface, (24, 15, 34), (sx-70, sy+30, 140, 24))
            pygame.draw.polygon(surface, (67, 30, 77), [(sx-18,sy-4),(sx-112,sy-76),(sx-82,sy+18),(sx-34,sy+30)])
            pygame.draw.polygon(surface, (124, 43, 54), [(sx+18,sy-4),(sx+112,sy-76),(sx+82,sy+18),(sx+34,sy+30)])
            pygame.draw.polygon(surface, (57, 43, 79), [(sx-28,sy-25),(sx-8,sy-45),(sx+25,sy-28),(sx+43,sy+22),(sx+8,sy+38),(sx-34,sy+24)])
            pygame.draw.circle(surface, (43, 34, 60), (sx+42,sy-24), 25)
            pygame.draw.polygon(surface, (174, 64, 49), [(sx+58,sy-31),(sx+96,sy-20),(sx+67,sy-5)])
            pygame.draw.polygon(surface, (224, 124, 54), [(sx-28,sy-37),(sx-40,sy-65),(sx-10,sy-48)])
            pygame.draw.polygon(surface, (224, 124, 54), [(sx+12,sy-42),(sx+28,sy-70),(sx+36,sy-36)])
            pygame.draw.circle(surface, (255, 75, 42), (sx+49,sy-28), 5)
            pygame.draw.circle(surface, (255, 209, 110), (sx+49,sy-28), 2)
            bw = 112
            pygame.draw.rect(surface, (35,38,48), (sx-bw//2, sy-91, bw, 8), border_radius=4)
            pygame.draw.rect(surface, (236,80,77), (sx-bw//2, sy-91, int(bw*max(0,enemy.hp)/enemy.max_hp), 8), border_radius=4)
            self.text(surface, enemy.name, sx, sy-100, (255,225,190), self.small, "midbottom")
            return
        col = (226, 202, 118)
        n = enemy.name
        if "슬라임" in n: col = (107, 226, 158) if "성운" not in n else (185, 119, 245)
        elif "좀비" in n: col = (110, 174, 119) if "화염" not in n else (232, 111, 76)
        elif "박쥐" in n: col = (120, 105, 176)
        elif "수호자" in n or "골렘" in n or "돌덩이" in n: col = (147, 160, 181) if "빛의" not in n else (202, 231, 252)
        elif "미라" in n: col = (220, 208, 164)
        elif "예티" in n: col = (221, 237, 245)
        elif "눈사람" in n: col = (238, 248, 255)
        elif "메이플" in n or "단풍" in n: col = (217, 132, 82)
        elif "공허" in n or "고대" in n: col = (158, 111, 215)
        pygame.draw.ellipse(surface, (22, 27, 39), (sx-17, sy+12, 34, 9))
        pygame.draw.circle(surface, col, (sx, sy), enemy.radius)
        pygame.draw.circle(surface, (255,255,255), (sx-7, sy-5), 4)
        pygame.draw.circle(surface, (255,255,255), (sx+7, sy-5), 4)
        pygame.draw.circle(surface, (30,37,49), (sx-7, sy-5), 2)
        pygame.draw.circle(surface, (30,37,49), (sx+7, sy-5), 2)
        if enemy.hit > 0:
            pygame.draw.circle(surface, (255,255,255), (sx,sy), enemy.radius+4, 3)
        bw = 48
        pygame.draw.rect(surface, (35,38,48), (sx-bw//2, sy-enemy.radius-15, bw, 5), border_radius=3)
        pygame.draw.rect(surface, RED, (sx-bw//2, sy-enemy.radius-15, int(bw*max(0,enemy.hp)/enemy.max_hp), 5), border_radius=3)
        self.text(surface, enemy.name, sx, sy-enemy.radius-22, WHITE, self.tiny, "midbottom")

    def draw_hud(self):
        p = self.player
        pygame.draw.rect(self.screen, (19, 27, 43), (0,0,SCREEN_W,76))
        self.text(self.screen, "천상 RPG", 24, 18, GOLD, self.big)
        self.text(self.screen, f"{p.nickname}  ·  Lv.{p.level}", 250, 19, WHITE, self.font)
        self.text(self.screen, f"점수 {p.score:,}", 250, 47, GOLD, self.small)
        self.text(self.screen, f"{p.zone}", 520, 25, CYAN, self.font)
        self.text(self.screen, f"골드 {p.gold:,}", 700, 25, GOLD, self.small)
        self.text(self.screen, f"마나 코어 Lv.{p.state.get('mana_core_level',0)}", 520, 51, (206,174,255), self.tiny)
        # HP/MP bars
        self.text(self.screen, f"HP {p.hp}/{p.max_hp}", 828, 13, WHITE, self.tiny)
        pygame.draw.rect(self.screen, (60,42,57), (828,32,116,12), border_radius=5)
        pygame.draw.rect(self.screen, (232,91,111), (828,32,int(116*max(0,p.hp)/p.max_hp),12), border_radius=5)
        self.text(self.screen, f"MP {p.mp}/{p.max_mp}", 954, 13, WHITE, self.tiny)
        pygame.draw.rect(self.screen, (44,54,79), (954,32,116,12), border_radius=5)
        pygame.draw.rect(self.screen, (83,162,235), (954,32,int(116*max(0,p.mp)/p.max_mp),12), border_radius=5)

    def draw_side_panel(self):
        p = self.player
        self.panel(PANEL)
        self.text(self.screen, "모험 정보", PANEL.x+17, PANEL.y+15, GOLD, self.font)
        self.text(self.screen, f"마력  {p.attack}", PANEL.x+17, PANEL.y+55, WHITE, self.small)
        self.text(self.screen, f"처치 수  {p.kills}", PANEL.x+17, PANEL.y+82, MUTED, self.small)
        exp_need = p.level*100
        self.text(self.screen, f"경험치  {p.exp}/{exp_need}", PANEL.x+17, PANEL.y+112, MUTED, self.small)
        pygame.draw.rect(self.screen, (47,57,78), (PANEL.x+17,PANEL.y+138,250,8), border_radius=4)
        pygame.draw.rect(self.screen, (112,181,231), (PANEL.x+17,PANEL.y+138,int(250*p.exp/exp_need),8), border_radius=4)
        stats = p.state.get("stats", {})
        self.text(self.screen, f"스탯 포인트 {p.state.get('stat_points',0)}  ·  코어 Lv.{p.state.get('mana_core_level',0)}", PANEL.x+17, PANEL.y+151, CYAN, self.tiny)
        learned = p.state.get("learned_skills", [])
        if "마나 감지" in learned:
            self.text(self.screen, f"마나 감지 {p.state.get('mana_detection',0):,}/10,000", PANEL.x+17, PANEL.y+170, (198,163,255), self.tiny)
        elif "마나 순환" in learned:
            self.text(self.screen, "스킬: 마나 순환", PANEL.x+17, PANEL.y+170, (198,163,255), self.tiny)
        self.text(self.screen, "보유 재료", PANEL.x+17, PANEL.y+190, GOLD, self.small)
        mats = list(p.state.get("materials", {}).items())
        if mats:
            for i,(name,count) in enumerate(mats[:7]):
                self.text(self.screen, f"· {name}  x{count}", PANEL.x+20, PANEL.y+214+i*20, WHITE, self.tiny)
        else:
            self.text(self.screen, "아직 재료가 없어.", PANEL.x+20, PANEL.y+216, MUTED, self.tiny)
        y = PANEL.y+365
        self.text(self.screen, "조작", PANEL.x+17, y, GOLD, self.small)
        keymap = p.state.get("equipped_skills", {})
        keyline = "  ".join(f"{k}:{keymap.get(k,'-')}" for k in ("E","R","T","J","K"))
        controls = ["WASD / 방향키  이동", "SPACE  기본 공격", "E/R/T/J/K  배운 스킬", "F  상호작용   L  물약", "B  스킬 배우기   I  가방   M  지역", "H  천상 마을   P  스탯   C  코어", "F10  관리자 메뉴" if p.is_admin else "ESC  메뉴 닫기"]
        for i,line in enumerate(controls):
            self.text(self.screen, line, PANEL.x+18, y+25+i*18, MUTED, self.tiny)
        if p.zone != "천상 마을":
            self.button((PANEL.x+17, PANEL.y+510, 250, 30), "천상 마을로 돌아가기  ·  H", self.travel_to_town, True, True)

    def draw_field(self):
        p = self.player
        camx, camy = self.draw_background(p.zone)
        for e in self.enemies:
            if not e.dead and (not e.is_boss or "투명 감지" in p.state.get("learned_skills", [])):
                self.draw_enemy(self.screen, e, camx, camy)
        if p.invuln <= 0 or int(time.time()*12)%2 == 0:
            self.draw_player_sprite(self.screen, int(p.x-camx), int(p.y-camy))
        # interaction hints
        if p.zone == "동굴":
            self.text(self.screen, "빛나는 구멍 근처에서 F를 눌러 봐", VIEW.x+16, VIEW.bottom-28, WHITE, self.tiny)
        elif p.zone == "샌드 사막":
            self.text(self.screen, "피라미드 앞에서 F를 눌러 2세계의 문을 확인해", VIEW.x+16, VIEW.bottom-28, WHITE, self.tiny)
        elif p.zone == "천상 마을":
            self.text(self.screen, "건물 클릭 또는 가까이 가서 F를 눌러 시설 이용", VIEW.x+16, VIEW.bottom-28, WHITE, self.tiny)
        self.draw_hud()
        self.draw_side_panel()
        if time.time() < p.message_until:
            r = pygame.Rect(VIEW.x+15, VIEW.y+12, VIEW.w-30, 36)
            pygame.draw.rect(self.screen, (18,25,42), r, border_radius=9)
            pygame.draw.rect(self.screen, (76,102,134), r, 1, border_radius=9)
            self.text(self.screen, p.message, r.centerx, r.centery, WHITE, self.small, "center")
        self.draw_modal()

    def modal_base(self, title):
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((4, 8, 18, 168))
        self.screen.blit(veil, (0,0))
        rect = pygame.Rect(215, 118, 670, 500)
        self.panel(rect, (25,34,54), (103,125,159), 18, 2)
        self.text(self.screen, title, rect.x+26, rect.y+22, GOLD, self.big)
        self.button((rect.right-56,rect.y+18,34,32), "X", lambda: setattr(self,"modal",""))
        return rect

    def can_afford(self, cost, gold=0):
        p = self.player
        return p.gold >= gold and all(p.state.get("materials", {}).get(k,0) >= v for k,v in cost.items())

    def pay(self, cost, gold=0):
        p = self.player
        if not self.can_afford(cost, gold):
            return False
        p.gold -= gold
        for k,v in cost.items():
            p.state["materials"][k] -= v
        return True

    def draw_modal(self):
        p = self.player
        if not self.modal:
            return
        if self.modal == "map":
            r = self.modal_base("지역 이동")
            self.text(self.screen, "레벨 조건을 달성하면 새로운 지역이 열려.", r.x+28, r.y+75, MUTED, self.small)
            for i,z in enumerate(ZONES[:6]):
                col, row = i%2, i//2
                x, y = r.x+28+col*310, r.y+122+row*83
                unlocked = z["name"] in p.state["unlocked"] or p.level >= z["level"]
                if unlocked and z["name"] not in p.state["unlocked"]:
                    p.state["unlocked"].append(z["name"])
                label = f"{z['name']}  ·  Lv.{z['level']}+" if unlocked else f"잠김  {z['name']}  ·  Lv.{z['level']}+"
                self.button((x,y,285,57), label, lambda name=z["name"]: self.travel_to(name), unlocked, True)
            self.button((r.x+28,r.y+370,285,42), "빛의 동굴로 이동", lambda: self.travel_special("빛의 동굴"), "빛의 동굴" in p.state["unlocked"], False)
            self.button((r.x+335,r.y+370,285,42), "2세계 · 별빛 황야", lambda: self.travel_special("2세계 · 별빛 황야"), "2세계 · 별빛 황야" in p.state["unlocked"], False)
            self.button((r.x+28,r.y+423,592,42), "천상 마을로 돌아가기  ·  H", self.travel_to_town, True, True)
            return
        if self.modal == "craft":
            r = self.modal_base("장비 제작소")
            self.text(self.screen, "재료와 골드를 사용해 모험 장비를 만들 수 있어.", r.x+28,r.y+75,MUTED,self.small)
            for i,rec in enumerate(GEAR_RECIPES):
                y = r.y+112+i*48
                cost = ", ".join(f"{k} {v}" for k,v in rec["cost"].items())
                self.text(self.screen, f"{rec['name']}  ·  마력 +{rec['atk']}", r.x+30,y,WHITE,self.small)
                self.text(self.screen, f"재료: {cost} / 골드 {rec['gold']}", r.x+30,y+22,MUTED,self.tiny)
                self.button((r.right-126,y+3,98,34), "제작", lambda rec=rec: self.craft_item(rec), self.can_afford(rec["cost"],rec["gold"]), True)
            return
        if self.modal == "combine":
            r = self.modal_base("조합소")
            self.text(self.screen, "같은 재료를 모아 더 가치 있는 재료로 조합해.",r.x+28,r.y+76,MUTED,self.small)
            recipes = [("풀잎 조각",3,"동굴 수정",1,30),("동굴 수정",3,"빛나는 파편",1,80),
                       ("모래 핵",3,"단풍잎",1,120),("얼음 결정",3,"천상 파편",1,220),
                       ("천상 파편",3,"별빛 가루",1,500)]
            for i,(a,n,b,m,g) in enumerate(recipes):
                y = r.y+125+i*62
                self.text(self.screen,f"{a} x{n}  →  {b} x{m}  ·  {g}G",r.x+32,y+5,WHITE,self.small)
                self.button((r.right-130,y,100,38),"조합",lambda a=a,n=n,b=b,m=m,g=g:self.combine_item(a,n,b,m,g),self.can_afford({a:n},g),True)
            return
        if self.modal == "potion":
            r = self.modal_base("물약 상점")
            self.text(self.screen,"회복 물약은 L 키로 사용할 수 있어.",r.x+28,r.y+82,MUTED,self.small)
            self.text(self.screen,f"보유 물약: {p.state.get('potions',0)}개",r.x+28,r.y+132,CYAN,self.font)
            self.text(self.screen,"3개 묶음 · 60 골드",r.x+28,r.y+205,WHITE,self.font)
            self.button((r.x+180,r.y+310,300,56),"회복 물약 3개 구매",self.buy_potions,p.gold>=60,True)
            return
        if self.modal == "disassemble":
            r = self.modal_base("분해소")
            self.text(self.screen,"현재 장비를 분해해 기본 재료를 돌려받아.",r.x+28,r.y+78,MUTED,self.small)
            gear = p.state.get("gear",{})
            self.panel((r.x+35,r.y+145,600,130),(34,47,70),(82,104,138),14)
            self.text(self.screen,f"장착 장비: {gear.get('name','없음')}",r.x+58,r.y+172,WHITE,self.font)
            self.text(self.screen,f"마력 +{gear.get('atk',0)}  ·  강화 +{gear.get('enhance',0)}",r.x+58,r.y+207,MUTED,self.small)
            self.button((r.x+205,r.y+330,260,54),"장비 분해",self.disassemble_gear,True,True)
            return
        if self.modal == "enhance":
            r = self.modal_base("강화소")
            gear = p.state.get("gear",{})
            lv = int(gear.get("enhance",0))
            cost = 60 + lv*75
            self.text(self.screen,"강화할수록 마력이 올라가. 최대 +10까지 가능해.",r.x+28,r.y+76,MUTED,self.small)
            self.panel((r.x+35,r.y+135,600,145),(34,47,70),(82,104,138),14)
            self.text(self.screen,gear.get("name","장비 없음"),r.x+58,r.y+160,WHITE,self.font)
            self.text(self.screen,f"현재 강화 +{lv}  ·  마력 {p.attack}",r.x+58,r.y+198,GOLD,self.small)
            self.text(self.screen,f"필요 골드: {cost}G  ·  풀잎 조각 2개",r.x+58,r.y+232,MUTED,self.small)
            self.button((r.x+205,r.y+330,260,54),"강화하기",self.enhance_gear,lv<10 and self.can_afford({"풀잎 조각":2},cost),True)
            return
        if self.modal == "menu":
            return
        if self.modal == "skills":
            r = self.modal_base("스킬북 / 배운 스킬")
            books = p.state.get("skill_books", [])
            learned = p.state.get("learned_skills", [])
            self.text(self.screen, "스킬북을 얻고 [배우기]를 누르면 단축키에 등록돼.", r.x+28, r.y+75, MUTED, self.small)
            self.text(self.screen, "보유 스킬북", r.x+28, r.y+112, GOLD, self.small)
            if books:
                for i, book in enumerate(books[:6]):
                    y = r.y+140+i*39
                    self.text(self.screen, book, r.x+38, y+8, WHITE, self.small)
                    self.button((r.right-142,y,106,34), "배우기", lambda b=book:self.learn_skill_book(b), True, True)
            else:
                self.text(self.screen, "아직 스킬북이 없어. 몬스터를 처치해 찾아봐!", r.x+38, r.y+150, MUTED, self.small)
            self.text(self.screen, "배운 스킬", r.x+28, r.y+390, CYAN, self.small)
            learned_text = ", ".join(learned) if learned else "배운 스킬이 없어."
            self.text(self.screen, learned_text, r.x+38, r.y+422, WHITE, self.tiny)
            keymap = p.state.get("equipped_skills", {})
            self.text(self.screen, "단축키: " + "  ·  ".join(f"{k}: {keymap.get(k, '비어 있음')}" for k in ("E","R","T","J","K")), r.x+28, r.y+460, GOLD, self.tiny)
            return
        if self.modal == "inventory":
            r = self.modal_base("가방")
            gear = p.state.get("gear",{})
            self.text(self.screen,f"장착: {gear.get('name')}  ·  마력 +{gear.get('atk')}  ·  강화 +{gear.get('enhance',0)}",r.x+28,r.y+78,WHITE,self.small)
            self.text(self.screen,f"회복 물약: {p.state.get('potions',0)}개",r.x+28,r.y+112,CYAN,self.small)
            self.text(self.screen,"특수 아이템",r.x+28,r.y+157,GOLD,self.small)
            specs = [x for x in p.state.get("special",[]) if x not in p.state.get("learned_skills",[])]
            self.text(self.screen,", ".join(specs) if specs else "아직 발견한 특수 아이템이 없어.",r.x+28,r.y+185,WHITE,self.small)
            self.button((r.x+28,r.y+208,210,36),"스킬북 / 스킬 창  ·  B",lambda:setattr(self,"modal","skills"),True,True)
            self.text(self.screen,"재료",r.x+28,r.y+255,GOLD,self.small)
            for i,(k,v) in enumerate(p.state.get("materials",{}).items()):
                self.text(self.screen,f"{k}  x{v}",r.x+35+(i%3)*195,r.y+285+(i//3)*31,WHITE,self.small)
            return
        if self.modal == "stats":
            r = self.modal_base("캐릭터 스탯")
            stats = p.state.get("stats", {})
            self.text(self.screen, f"남은 스탯 포인트: {p.state.get('stat_points',0)}개", r.x+30, r.y+78, CYAN, self.font)
            descriptions = {
                "strength": "공격력이 올라가.",
                "vitality": "최대 HP가 20 증가해.",
                "mana": "최대 MP가 10 증가해.",
                "agility": "이동 속도가 빨라져.",
            }
            labels = {"strength":"힘", "vitality":"체력", "mana":"마나", "agility":"민첩"}
            for i, key in enumerate(("strength", "vitality", "mana", "agility")):
                y = r.y+125+i*76
                self.panel((r.x+28,y,610,62),(33,46,68),(73,97,132),12)
                self.text(self.screen, f"{labels[key]}  Lv.{stats.get(key,0)}", r.x+48, y+10, WHITE, self.font)
                self.text(self.screen, descriptions[key], r.x+48, y+37, MUTED, self.tiny)
                self.button((r.right-145,y+12,48,38), "+1", lambda key=key:self.allocate_stat(key,1), int(p.state.get("stat_points",0))>=1, True)
                self.button((r.right-88,y+12,48,38), "+5", lambda key=key:self.allocate_stat(key,5), int(p.state.get("stat_points",0))>=5, False)
            return
        if self.modal == "core":
            r = self.modal_base("마나 코어")
            core = int(p.state.get("mana_core_level",0))
            stones = int(p.state.get("materials",{}).get("마나석",0))
            stone_cost = 3+core*2
            gold_cost = 200+core*300
            self.panel((r.x+32,r.y+86,606,136),(35,42,74),(107,93,157),16,2)
            self.text(self.screen, f"마나 코어  Lv.{core}", r.x+58,r.y+110,(221,194,255),self.big)
            self.text(self.screen, f"공격 증폭  ×{1.5**core:,.2f}", r.x+58,r.y+166,GOLD,self.font)
            self.text(self.screen, f"스탯 포인트 {p.state.get('stat_points',0)}개  ·  마나석 {stones}개", r.x+34,r.y+250,WHITE,self.font)
            self.text(self.screen, f"다음 성장 비용: 마나석 {stone_cost}개 + 골드 {gold_cost:,}", r.x+34,r.y+292,MUTED,self.small)
            self.text(self.screen, "코어 성장 시 스탯 포인트 10개를 충전해.", r.x+34,r.y+327,CYAN,self.small)
            self.button((r.x+180,r.y+375,310,58), f"마나 코어 성장  (Lv.{core+1})", self.upgrade_mana_core, self.can_afford({"마나석":stone_cost},gold_cost), True)
            return
        if self.modal == "admin":
            self.draw_admin_modal()

    def draw_admin_modal(self):
        r = self.modal_base("관리자 센터")
        mode_label = "온라인 전체 계정 관리" if self.db.online.configured else "로컬 계정 관리 (server_config.json에 서버 주소 필요)"
        self.text(self.screen,mode_label+" · 닉네임/아이디 검색",r.x+28,r.y+76,RED,self.tiny)
        self.text(self.screen,"계정 검색",r.x+28,r.y+104,GOLD,self.small)
        search_rect = pygame.Rect(r.x+28,r.y+128,166,34)
        pygame.draw.rect(self.screen,(13,20,34),search_rect,border_radius=7)
        pygame.draw.rect(self.screen,(108,173,223) if self.admin_search_focus else (90,118,153),search_rect,2 if self.admin_search_focus else 1,border_radius=7)
        self.text(self.screen,self.admin_search_input or "닉네임/아이디",search_rect.x+8,search_rect.centery,WHITE if self.admin_search_input else MUTED,self.tiny,"midleft")
        self.button((r.x+200,r.y+128,73,34),"검색",self.refresh_admin_users,True,True)
        list_rect = pygame.Rect(r.x+28,r.y+171,245,232)
        pygame.draw.rect(self.screen,(20,28,45),list_rect,border_radius=10)
        visible_users = self.admin_users[self.admin_scroll:self.admin_scroll+8]
        for i,u in enumerate(visible_users):
            yy = list_rect.y+6+i*27
            selected = u["username"] == self.admin_selected
            if selected:
                pygame.draw.rect(self.screen,(59,82,115),(list_rect.x+5,yy-2,list_rect.w-10,25),border_radius=6)
            suffix = " · 관리자" if u["is_admin"] else (" · 정지" if u["banned"] else "")
            shown_name = u.get("nickname") or u["username"]
            self.text(self.screen,f"{shown_name}{suffix}",list_rect.x+12,yy,WHITE if selected else MUTED,self.tiny)
            self.buttons.append(Button((list_rect.x+5,yy-3,list_rect.w-10,26),"",lambda name=u["username"]: self.select_admin_user(name)))
        if len(self.admin_users) > 8:
            total_pages = (len(self.admin_users) + 7) // 8
            current_page = self.admin_scroll // 8 + 1
            self.text(self.screen, f"{self.admin_scroll+1}-{min(self.admin_scroll+8,len(self.admin_users))} / {len(self.admin_users)}  ·  {current_page}/{total_pages}페이지", list_rect.x+7, list_rect.bottom+12, MUTED, self.tiny)
            self.button((list_rect.x+5,list_rect.bottom+32,82,27),"이전",self.admin_prev_page,self.admin_scroll>0,False)
            self.button((list_rect.x+94,list_rect.bottom+32,82,27),"다음",self.admin_next_page,self.admin_scroll+8<len(self.admin_users),False)
        right_x = r.x+285
        self.text(self.screen,"선택 계정",right_x,r.y+106,GOLD,self.small)
        selected_row = next((u for u in self.admin_users if u["username"]==self.admin_selected),None)
        selected_label = (f"{selected_row.get('nickname') or self.admin_selected}  /  ID: {self.admin_selected}" if selected_row else "목록에서 계정을 선택해 줘")
        self.text(self.screen,selected_label,right_x,r.y+132,WHITE,self.tiny)
        current = next((u for u in self.admin_users if u["username"]==self.admin_selected),None)
        if current:
            full = self.admin_current or {}
            try:
                state = json.loads(full.get("state") or "{}")
            except Exception:
                state = {}
            field_labels = {
                "score":"점수", "level":"레벨", "gold":"골드", "exp":"경험치",
                "stat_points":"스탯포인트", "core":"코어 레벨", "strength":"힘",
                "vitality":"체력", "mana":"마나", "agility":"민첩", "hp":"현재 HP", "mp":"현재 MP",
            }
            value_map = {
                "score":full.get("score",0), "level":full.get("level",1), "gold":full.get("gold",0),
                "exp":full.get("exp",0), "stat_points":state.get("stat_points",0),
                "core":state.get("mana_core_level",0),
                "strength":state.get("stats",{}).get("strength",0),
                "vitality":state.get("stats",{}).get("vitality",0),
                "mana":state.get("stats",{}).get("mana",0),
                "agility":state.get("stats",{}).get("agility",0),
                "hp":full.get("hp",0), "mp":full.get("mp",0),
            }
            self.text(self.screen,f"Lv.{current['level']}  ·  점수 {current['score']:,}  ·  골드 {current['gold']:,}",right_x,r.y+158,MUTED,self.tiny)
            self.text(self.screen,f"수정 항목: {field_labels[self.admin_edit_field]} (현재 {value_map.get(self.admin_edit_field,0)})",right_x,r.y+188,CYAN,self.tiny)
            field_buttons = [
                ("score","점수"),("level","레벨"),("gold","골드"),("exp","경험치"),
                ("stat_points","스탯P"),("core","코어"),("strength","힘"),("vitality","체력"),
                ("mana","마나"),("agility","민첩"),("hp","HP"),("mp","MP"),
            ]
            for i,(key,label) in enumerate(field_buttons):
                col,row_i=i%4,i//4
                bx=right_x+col*85
                by=r.y+212+row_i*36
                self.button((bx,by,80,31),label,lambda key=key:self.select_admin_field(key),True,self.admin_edit_field==key)
            inp = pygame.Rect(right_x, r.y+324, 154, 37)
            pygame.draw.rect(self.screen,(13,20,34),inp,border_radius=8)
            pygame.draw.rect(self.screen,(108,173,223) if self.admin_score_focus else (90,118,153),inp,2 if self.admin_score_focus else 1,border_radius=8)
            shown_value = self.admin_edit_input if self.admin_edit_input else ("숫자 입력" if self.admin_score_focus else str(value_map.get(self.admin_edit_field,0)))
            self.text(self.screen,shown_value,inp.x+10,inp.centery,WHITE if self.admin_edit_input else MUTED,self.tiny,"midleft")
            self.button((right_x+164,r.y+324,88,37),"값 적용",self.admin_apply_value,True,True)
            self.button((right_x,r.y+371,104,36),"밴 / 언밴",self.admin_toggle_ban,not current["is_admin"],False)
            self.button((right_x+112,r.y+371,104,36),"스킬북 지급",self.admin_grant_skills,True,False)
            self.button((right_x+224,r.y+371,104,36),"HP·MP 회복",self.admin_heal,True,False)
        else:
            self.text(self.screen,"계정을 선택하면 관리 항목이 열려.",right_x,r.y+158,MUTED,self.small)
        self.text(self.screen,"※ 온라인 모드: 서버 전체 계정을 닉네임/아이디로 검색해.",r.x+28,r.bottom-18,MUTED,self.tiny)

    def refresh_admin_users(self):
        self.admin_scroll = 0
        self.admin_users = self.db.list_users(self.admin_search_input.strip())
        if self.db.online.configured and self.db.online.last_error:
            self.toast_msg("온라인 계정 검색 실패: " + self.db.online.last_error, 4)
        if self.admin_selected and not any(u.get("username")==self.admin_selected for u in self.admin_users):
            self.admin_selected = ""
            self.admin_current = None
        self.admin_search_focus = False
        self.toast_msg(f"계정 {len(self.admin_users)}개를 검색했어.", 2)

    def admin_prev_page(self):
        self.admin_scroll = max(0, self.admin_scroll - 8)

    def admin_next_page(self):
        self.admin_scroll = min(max(0, len(self.admin_users)-1), self.admin_scroll + 8)
        self.admin_scroll = (self.admin_scroll // 8) * 8

    def select_admin_user(self, name):
        self.admin_selected = name
        row = self.db.refresh_user(name)
        self.admin_current = row
        if row:
            try:
                state = json.loads(row.get("state") or "{}")
            except Exception:
                state = {}
            values = {
                "stat_points":state.get("stat_points",0), "core":state.get("mana_core_level",0),
                "strength":state.get("stats",{}).get("strength",0),
                "vitality":state.get("stats",{}).get("vitality",0),
                "mana":state.get("stats",{}).get("mana",0),
                "agility":state.get("stats",{}).get("agility",0),
            }
            self.admin_edit_input = str(values.get(self.admin_edit_field,row.get(self.admin_edit_field,0)))
        else:
            self.admin_edit_input = ""
        self.admin_score_focus = False

    def select_admin_field(self, field):
        self.admin_edit_field = field
        self.admin_edit_input = ""
        self.admin_score_focus = False

    def admin_apply_score(self):
        # Backwards-compatible alias for older button callbacks.
        self.admin_apply_value()

    def _sync_admin_target(self):
        if self.player and self.player.username == self.admin_selected:
            row = self.db.refresh_user(self.admin_selected)
            if row:
                self.player.score = int(row["score"])
                self.player.gold = int(row["gold"])
                self.player.level = int(row["level"])
                self.player.exp = int(row["exp"])
                self.player.hp = int(row["hp"])
                self.player.max_hp = int(row["max_hp"])
                self.player.mp = int(row["mp"])
                self.player.max_mp = int(row["max_mp"])
                try:
                    fresh_state = json.loads(row.get("state") or "{}")
                    self.player.state.update(fresh_state)
                except Exception:
                    pass
            self.admin_current = row

    def admin_apply_value(self):
        if not self.admin_selected:
            self.toast_msg("먼저 계정을 선택해 줘.")
            return
        try:
            if not self.admin_edit_input.strip():
                raise ValueError
            val = int(self.admin_edit_input)
            updated = self.db.admin_set_value(self.admin_selected, self.admin_edit_field, val)
            if not updated:
                self.toast_msg("선택한 계정을 찾을 수 없거나 수정 항목이 올바르지 않아.")
                return
            self._sync_admin_target()
            self.admin_current = self.db.refresh_user(self.admin_selected)
            self.admin_edit_input = str(val)
            self.admin_score_focus = False
            self.refresh_admin_users()
            label = {"score":"점수","level":"레벨","gold":"골드","exp":"경험치","stat_points":"스탯 포인트","core":"마나 코어 레벨","strength":"힘","vitality":"체력","mana":"마나","agility":"민첩","hp":"HP","mp":"MP"}.get(self.admin_edit_field,self.admin_edit_field)
            self.toast_msg(f"{self.admin_selected}의 {label}을(를) {val:,}(으)로 변경했어.")
        except (ValueError, TypeError):
            self.toast_msg("선택한 항목에 맞는 숫자를 입력해 줘.")

    def admin_grant_skills(self):
        if not self.admin_selected:
            self.toast_msg("먼저 계정을 선택해 줘.")
            return
        if self.db.admin_grant_skills(self.admin_selected):
            self._sync_admin_target()
            self.admin_current = self.db.refresh_user(self.admin_selected)
            self.refresh_admin_users()
            self.toast_msg(f"{self.admin_selected}에게 스킬북을 지급했어. B키에서 배울 수 있어.")

    def admin_heal(self):
        if not self.admin_selected:
            self.toast_msg("먼저 계정을 선택해 줘.")
            return
        if self.db.admin_heal(self.admin_selected):
            self._sync_admin_target()
            self.admin_current = self.db.refresh_user(self.admin_selected)
            self.refresh_admin_users()
            self.toast_msg(f"{self.admin_selected}의 HP와 MP를 모두 회복했어.")

    def admin_toggle_ban(self):
        if not self.admin_selected or self.admin_selected == ADMIN_NAME:
            return
        row = self.db.refresh_user(self.admin_selected)
        if row:
            self.db.set_ban(self.admin_selected,not bool(row["banned"]))
            self.admin_current = self.db.refresh_user(self.admin_selected)
            self.refresh_admin_users()
            self.toast_msg("계정 이용 제한 상태를 변경했어.")

    def craft_item(self, rec):
        if not self.pay(rec["cost"],rec["gold"]):
            return
        self.player.state["gear"] = {"name":rec["name"],"atk":rec["atk"],"enhance":0}
        self.player.say(f"{rec['name']} 제작 완료! 장비가 교체됐어.",3)
        self.db.save_player(self.player)

    def combine_item(self, a,n,b,m,g):
        if not self.pay({a:n},g): return
        self.player.add_material(b,m)
        self.player.say(f"{b}을(를) 조합했어!",2)
        self.db.save_player(self.player)

    def buy_potions(self):
        if self.player.gold < 60:
            return
        self.player.gold -= 60
        self.player.state["potions"] = int(self.player.state.get("potions", 0)) + 3
        self.player.say("회복 물약 3개를 구매했어!", 2)
        self.db.save_player(self.player)

    def disassemble_gear(self):
        gear = self.player.state.get("gear",{})
        if gear.get("name") == "초보자 별빛 오브":
            self.player.say("기본 장비는 분해할 수 없어.",2); return
        self.player.add_material("풀잎 조각",3)
        self.player.add_material("동굴 수정",1)
        self.player.state["gear"] = {"name":"초보자 별빛 오브","atk":4,"enhance":0}
        self.player.say("장비를 분해했어. 재료를 돌려받았어.",3)
        self.db.save_player(self.player)

    def enhance_gear(self):
        gear = self.player.state.get("gear",{})
        lv = int(gear.get("enhance",0))
        cost = 60 + lv*75
        if lv >= 10 or not self.pay({"풀잎 조각":2},cost): return
        gear["enhance"] = lv+1
        self.player.say(f"강화 성공! +{lv+1}",2)
        self.db.save_player(self.player)

    def travel_to(self,name):
        self.modal = ""
        if self.player.level < ZONE_BY_NAME[name]["level"]:
            self.player.say("아직 입장할 수 없어.",2); return
        if name not in self.player.state["unlocked"]:
            self.player.state["unlocked"].append(name)
        self.enter_zone(name)

    def travel_special(self,name):
        if name not in self.player.state.get("unlocked",[]):
            return
        self.modal=""
        self.enter_zone(name)
        if name == "2세계 · 별빛 황야" and "마나 감지" not in self.player.state.get("learned_skills", []):
            self.player.say("2세계의 몬스터가 마나 감지 스킬북을 지키고 있어. 처치해서 찾아봐!", 7)

    def update(self, dt):
        p = self.player
        if not p or self.scene != "game": return
        p.attack_cd=max(0,p.attack_cd-dt); p.skill_cd=max(0,p.skill_cd-dt)
        p.mana_skill_cd=max(0,p.mana_skill_cd-dt)
        p.invuln=max(0,p.invuln-dt); p.flash=max(0,p.flash-dt)
        mana_regen = 7.0 if time.time() < p.mana_circulation_until else 2.2
        p.mp=min(p.max_mp,p.mp+dt*mana_regen)
        if self.modal:
            return
        keys=pygame.key.get_pressed()
        dx=(keys[pygame.K_d] or keys[pygame.K_RIGHT])-(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy=(keys[pygame.K_s] or keys[pygame.K_DOWN])-(keys[pygame.K_w] or keys[pygame.K_UP])
        if dx or dy:
            norm=math.hypot(dx,dy); dx/=norm; dy/=norm
            speed=225 + int(p.state.get("stats", {}).get("agility", 0)) * 4
            p.x=max(38,min(MAP_W-38,p.x+dx*speed*dt))
            p.y=max(38,min(MAP_H-38,p.y+dy*speed*dt))
            p.facing=(dx,dy)
        if p.zone=="천상 마을":
            # town is peaceful
            return
        if self.enemies and all(e.dead for e in self.enemies):
            self.spawn_timer += dt
            if self.spawn_timer >= 3.0:
                self.spawn_enemies()
        for e in self.enemies:
            if e.dead: continue
            if e.is_boss and "투명 감지" not in p.state.get("learned_skills", []):
                continue
            e.cooldown=max(0,e.cooldown-dt); e.hit=max(0,e.hit-dt)
            dist=math.hypot(p.x-e.x,p.y-e.y)
            if e.aggressive and dist < 430:
                if dist > 33:
                    e.x += (p.x-e.x)/max(1,dist)*min(100*dt,dist-29)
                    e.y += (p.y-e.y)/max(1,dist)*min(100*dt,dist-29)
                elif e.cooldown<=0 and p.invuln<=0:
                    p.hp=max(0,p.hp-e.atk)
                    p.invuln=0.8
                    e.cooldown=1.15
                    p.say(f"{e.name}의 기운에 맞았어!",1.2)
            else:
                e.seed+=dt
                e.x+=math.sin(e.seed)*7*dt
                e.y+=math.cos(e.seed*.7)*7*dt
        if p.hp<=0:
            p.hp=max(1,p.max_hp//2)
            p.mp=p.max_mp//2
            p.gold=max(0,p.gold-20)
            self.enter_zone("천상 마을")
            p.say("마을에서 다시 일어났어. 골드 20을 잃었어.",4)
        # hole/pyramid transitions are interaction-based; draw landmarks stay visible
        if time.time()-self.last_save>15:
            saved = self.db.save_player(p)
            if self.db.online.configured and not saved:
                self.toast_msg("온라인 저장에 실패했어. 인터넷과 서버 상태를 확인해 줄.", 4)
            self.last_save=time.time()

    def draw_login(self):
        self.screen.fill((16,22,37))
        for i in range(80):
            x=(i*149+23)%SCREEN_W; y=(i*83+11)%SCREEN_H
            pygame.draw.circle(self.screen,(72+i%70,88+i%80,125+i%90),(x,y),1+i%2)
        pygame.draw.circle(self.screen,(52,86,128),(SCREEN_W//2,210),134,2)
        pygame.draw.circle(self.screen,(42,68,107),(SCREEN_W//2,210),112,1)
        self.text(self.screen,"천상 RPG",SCREEN_W//2,132,GOLD,self.title,"midtop")
        self.text(self.screen,"별빛을 모아, 새로운 세계로",SCREEN_W//2,194,CYAN,self.small,"midtop")
        if self.auth_mode == "register":
            box=pygame.Rect(350,236,400,420)
            self.panel(box,(25,34,54),(82,104,139),18,2)
            self.text(self.screen,"회원가입",box.centerx,box.y+18,WHITE,self.big,"midtop")
            self.text(self.screen,"아이디",box.x+38,box.y+72,MUTED,self.small)
            self.draw_input((box.x+38,box.y+98,324,43),self.username_input,"username")
            self.text(self.screen,"닉네임 (다른 플레이어에게 표시돼)",box.x+38,box.y+150,MUTED,self.tiny)
            self.draw_input((box.x+38,box.y+175,324,43),self.nickname_input,"nickname")
            self.text(self.screen,"비밀번호 (온라인은 8글자 이상)",box.x+38,box.y+227,MUTED,self.tiny)
            self.draw_input((box.x+38,box.y+252,324,43),"●"*len(self.password_input),"password")
            self.button((box.x+38,box.y+314,324,45),"가입 완료",self.register_login,True,True)
            self.button((box.x+38,box.y+366,324,32),"로그인으로 돌아가기",self.toggle_auth,True,False)
        else:
            box=pygame.Rect(350,282,400,352)
            self.panel(box,(25,34,54),(82,104,139),18,2)
            self.text(self.screen,"로그인",box.centerx,box.y+28,WHITE,self.big,"midtop")
            self.text(self.screen,"아이디",box.x+38,box.y+100,MUTED,self.small)
            self.draw_input((box.x+38,box.y+125,324,43),self.username_input,"username")
            self.text(self.screen,"비밀번호",box.x+38,box.y+185,MUTED,self.small)
            self.draw_input((box.x+38,box.y+210,324,43),"●"*len(self.password_input),"password")
            self.button((box.x+38,box.y+270,324,45),"로그인",self.register_login,True,True)
            self.button((box.x+38,box.y+322,324,32),"처음이야? 회원가입",self.toggle_auth,True,False)
        if self.notice:
            self.text(self.screen,self.notice,SCREEN_W//2,box.bottom+5,CYAN,self.tiny,"midtop")
        login_note = "온라인 서버에 연결돼. 모든 계정이 공유돼." if self.db.online.configured else "로컬 모드 · 온라인 공유는 서버 배포와 server_config.json 설정 후 가능해."
        self.text(self.screen,login_note,SCREEN_W//2,SCREEN_H-28,MUTED,self.tiny,"midbottom")

    def draw_input(self, rect, value, name):
        active=self.active_input==name
        display_value = value
        if active and self.text_composition:
            # Password composition is masked just like committed password text.
            display_value += ("●" * len(self.text_composition)) if name == "password" else self.text_composition
        pygame.draw.rect(self.screen,(14,21,35),(rect[0],rect[1],rect[2],rect[3]),border_radius=8)
        pygame.draw.rect(self.screen,(108,173,223) if active else (69,85,112),(rect[0],rect[1],rect[2],rect[3]),2 if active else 1,border_radius=8)
        self.text(self.screen,display_value or "입력...",rect[0]+13,rect[1]+rect[3]//2,WHITE if display_value else MUTED,self.small,"midleft")

    def toggle_auth(self):
        self.auth_mode="register" if self.auth_mode=="login" else "login"
        self.notice=""
        self.password_input=""
        self.active_input="username"
        if self.auth_mode == "register":
            self.nickname_input=""
        self.text_composition=""
        self.update_ime_rect()

    def handle_click(self, pos):
        if self.scene=="login":
            x,y=pos
            if self.auth_mode == "register":
                if 388<=x<=712 and 334<=y<=377:
                    self.active_input="username"; self.text_composition=""; self.update_ime_rect()
                elif 388<=x<=712 and 411<=y<=454:
                    self.active_input="nickname"; self.text_composition=""; self.update_ime_rect()
                elif 388<=x<=712 and 488<=y<=531:
                    self.active_input="password"; self.text_composition=""; self.update_ime_rect()
                elif 388<=x<=712 and 550<=y<=595:
                    self.register_login()
                elif 388<=x<=712 and 602<=y<=634:
                    self.toggle_auth()
            else:
                if 388<=x<=712 and 407<=y<=450:
                    self.active_input="username"; self.text_composition=""; self.update_ime_rect()
                elif 388<=x<=712 and 492<=y<=535:
                    self.active_input="password"; self.text_composition=""; self.update_ime_rect()
                elif 388<=x<=712 and 552<=y<=597:
                    self.register_login()
                elif 388<=x<=712 and 604<=y<=636:
                    self.toggle_auth()
            return
        if self.modal == "admin":
            search_field = pygame.Rect(243, 246, 166, 34)
            if search_field.collidepoint(pos):
                self.admin_search_focus = True
                self.admin_score_focus = False
                try:
                    pygame.key.start_text_input()
                    pygame.key.set_text_input_rect(search_field)
                except Exception:
                    pass
                return
            score_field = pygame.Rect(500, 442, 154, 37)
            if score_field.collidepoint(pos):
                if not self.admin_score_focus:
                    self.admin_edit_input = ""
                self.admin_score_focus = True
                self.admin_search_focus = False
                return
            if not any(b.rect.collidepoint(pos) for b in self.buttons):
                self.admin_score_focus = False
                self.admin_search_focus = False
        # clickable town buildings
        if self.player and not self.modal and self.player.zone=="천상 마을" and VIEW.collidepoint(pos):
            vx,vy=pos[0]-VIEW.x,pos[1]-VIEW.y
            p=self.player
            camx=max(0,min(MAP_W-VIEW.w,int(p.x-VIEW.w/2)))
            camy=max(0,min(MAP_H-VIEW.h,int(p.y-VIEW.h/2)))
            buildings=[(520,310,"craft"),(1080,310,"combine"),(520,820,"disassemble"),(1080,820,"enhance"),(800,160,"map"),(800,950,"potion"),(800,700,"core")]
            for bx,by,m in buildings:
                if abs((bx-camx)-vx)<72 and abs((by-camy)-vy)<55:
                    self.modal=m; return
        for b in reversed(self.buttons):
            if b.active and b.rect.collidepoint(pos):
                b.callback(); return

    def keydown(self,event):
        if self.scene=="login":
            if event.key==pygame.K_TAB:
                fields = ["username", "nickname", "password"] if self.auth_mode == "register" else ["username", "password"]
                try:
                    self.active_input = fields[(fields.index(self.active_input) + 1) % len(fields)]
                except ValueError:
                    self.active_input = fields[0]
                self.text_composition=""
                self.update_ime_rect()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.text_composition=""
                self.register_login()
            elif event.key==pygame.K_BACKSPACE:
                # During Hangul composition, let the IME process Backspace first.
                if self.text_composition:
                    self.text_composition=""
                elif self.active_input=="username":
                    self.username_input=self.username_input[:-1]
                elif self.active_input=="nickname":
                    self.nickname_input=self.nickname_input[:-1]
                else:
                    self.password_input=self.password_input[:-1]
            # Do not append event.unicode here. Korean IME input is handled by
            # TEXTINPUT; using KEYDOWN.unicode as well can drop or duplicate Hangul.
            return
        if not self.player: return
        if self.modal=="admin":
            if event.key==pygame.K_BACKSPACE and self.admin_search_focus:
                self.admin_search_input=self.admin_search_input[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.admin_search_focus:
                self.refresh_admin_users()
            elif event.key==pygame.K_BACKSPACE and self.admin_score_focus:
                self.admin_edit_input=self.admin_edit_input[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.admin_apply_value()
            elif event.key==pygame.K_ESCAPE:
                self.modal=""
                self.admin_score_focus=False
                self.admin_search_focus=False
            elif self.admin_score_focus and len(self.admin_edit_input)<10:
                # Use physical key constants for ASCII digits. This works even
                # after the login form has stopped SDL/Windows IME text input.
                digit = None
                for number in range(10):
                    if event.key in (getattr(pygame, f"K_{number}", -1),
                                     getattr(pygame, f"K_KP{number}", -1)):
                        digit = str(number)
                        break
                if digit is not None:
                    self.admin_edit_input += digit
            return
        if event.key==pygame.K_ESCAPE:
            if self.modal: self.modal=""
            else: self.modal="menu"
        elif event.key==pygame.K_SPACE and not self.modal: self.basic_attack()
        elif event.key==pygame.K_e and not self.modal: self.use_learned_skill("이상한 스킬")
        elif event.key==pygame.K_r and not self.modal: self.use_learned_skill("화염구")
        elif event.key==pygame.K_t and not self.modal: self.use_mana_skill()
        elif event.key==pygame.K_j and not self.modal: self.use_learned_skill("별빛 돌진")
        elif event.key==pygame.K_k and not self.modal: self.use_learned_skill("별빛 파동")
        elif event.key==pygame.K_l: self.use_potion()
        elif event.key==pygame.K_f and not self.modal: self.handle_interact()
        elif event.key==pygame.K_i: self.modal="inventory" if not self.modal else ""
        elif event.key==pygame.K_b: self.modal="skills" if not self.modal else ""
        elif event.key==pygame.K_m: self.modal="map" if not self.modal else ""
        elif event.key==pygame.K_p: self.modal="stats" if not self.modal else ""
        elif event.key==pygame.K_c: self.modal="core" if not self.modal else ""
        elif event.key==pygame.K_F10 and self.player.is_admin:
            self.admin_selected=""; self.admin_score_input=""; self.admin_score_focus=False
            self.admin_search_input=""; self.admin_search_focus=False
            self.admin_edit_input=""; self.admin_value_focus=False; self.admin_edit_field="score"; self.modal="admin"
            self.refresh_admin_users()
        elif self.modal=="menu":
            if event.key==pygame.K_RETURN: self.modal="map"

    def draw_menu_modal(self):
        r=self.modal_base("메뉴")
        self.text(self.screen,"게임을 저장하고 다른 지역으로 이동할 수 있어.",r.x+28,r.y+90,MUTED,self.small)
        self.button((r.x+80,r.y+170,220,52),"지역 이동",lambda:setattr(self,"modal","map"),True,True)
        self.button((r.x+370,r.y+170,220,52),"가방",lambda:setattr(self,"modal","inventory"))
        self.button((r.x+80,r.y+245,220,52),"천상 마을로",lambda:self.travel_to_town())
        self.button((r.x+370,r.y+245,220,52),"로그아웃",self.logout)

    def travel_to_town(self):
        self.modal=""; self.enter_zone("천상 마을")

    def logout(self):
        if self.player: self.db.save_player(self.player)
        if self.db.online.configured:
            self.db.online.logout()
        self.player=None; self.scene="login"; self.modal=""; self.password_input=""; self.notice="로그아웃했어. 다시 로그인할 수 있어."
        self.active_input="username"
        self.text_composition=""
        self.start_login_text_input()

    def draw(self):
        self.buttons=[]
        if self.scene=="login": self.draw_login()
        else:
            self.draw_field()
            if self.modal=="menu": self.draw_menu_modal()
        if self.toast and time.time()<self.toast_until:
            rect=pygame.Rect(300,SCREEN_H-58,500,38)
            pygame.draw.rect(self.screen,(16,25,41),rect,border_radius=10)
            pygame.draw.rect(self.screen,(83,123,159),rect,1,border_radius=10)
            self.text(self.screen,self.toast,rect.centerx,rect.centery,WHITE,self.small,"center")
        pygame.display.flip()

    def run(self):
        while self.running:
            dt=min(self.clock.tick(FPS)/1000,0.05)
            for event in pygame.event.get():
                if event.type==pygame.QUIT:
                    self.running=False
                elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    self.handle_click(event.pos)
                elif hasattr(pygame, "TEXTEDITING") and event.type==pygame.TEXTEDITING:
                    if self.scene == "login":
                        self.text_composition = getattr(event, "text", "")
                elif hasattr(pygame, "TEXTINPUT") and event.type==pygame.TEXTINPUT:
                    self.insert_text_input(getattr(event, "text", ""))
                elif event.type==pygame.KEYDOWN:
                    self.keydown(event)
            self.update(dt)
            self.draw()
        if self.player:
            self.db.save_player(self.player)
        pygame.quit()


# draw special modal menu after ordinary field drawing
def _draw_field_with_menu(self):
    self.draw_field()
    if self.modal=="menu": self.draw_menu_modal()


if __name__ == "__main__":
    try:
        Game().run()
    except Exception as exc:
        # Avoid silent failures in console builds; a packaged GUI build writes a log.
        try:
            log_path=data_dir()/"error.log"
            log_path.write_text(f"{type(exc).__name__}: {exc}\n",encoding="utf-8")
        except Exception:
            pass
        raise
