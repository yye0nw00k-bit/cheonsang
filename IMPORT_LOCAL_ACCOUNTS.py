# -*- coding: utf-8 -*-
"""Migrate local Cheonsang RPG accounts to the configured online server."""
import getpass
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def local_db():
    root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return root / "CheonsangRPG" / "game.db"


def call(url, path, payload, token=""):
    headers = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url.rstrip("/") + path,
                                 data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("message", str(exc))
        except Exception:
            msg = str(exc)
        raise RuntimeError(msg) from None


def main():
    cfg_path = app_dir() / "server_config.json"
    try:
        api_url = str(json.loads(cfg_path.read_text(encoding="utf-8")).get("api_url", "")).strip().rstrip("/")
    except Exception:
        api_url = ""
    if not api_url:
        print("server_config.json에 Render API 주소를 먼저 입력해 줘.")
        input("Enter를 누르면 종료해.")
        return 1
    db_path = local_db()
    if not db_path.exists():
        print(f"기존 로컬 저장 파일을 찾을 수 없어: {db_path}")
        input("Enter를 누르면 종료해.")
        return 1
    admin_id = input("온라인 관리자 아이디 [최연욱]: ").strip() or "최연욱"
    admin_pw = getpass.getpass("온라인 관리자 비밀번호: ")
    login = call(api_url, "/api/login", {"username": admin_id, "password": admin_pw})
    token = login.get("token", "")
    if not token:
        raise RuntimeError("관리자 로그인 토큰을 받지 못했어.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM users WHERE username<>?", (admin_id,)).fetchall()
    payload = []
    for row in rows:
        try:
            state = json.loads(row["state"] or "{}")
        except Exception:
            state = {}
        payload.append({
            "username": row["username"], "nickname": row["nickname"] if "nickname" in row.keys() else row["username"],
            "salt": bytes(row["salt"]).hex(),
            "password_hash": bytes(row["password_hash"]).hex(),
            "banned": bool(row["banned"]), "score": row["score"], "gold": row["gold"],
            "level": row["level"], "exp": row["exp"], "hp": row["hp"],
            "max_hp": row["max_hp"], "mp": row["mp"], "max_mp": row["max_mp"],
            "state": state,
        })
    conn.close()
    result = call(api_url, "/api/admin/import-users", {"users": payload}, token)
    print("\n계정 이전 결과")
    print("새로 이전:", result.get("imported", 0))
    print("건너뜀:", result.get("skipped", 0))
    print("온라인 계정은 기존 비밀번호로 로그인할 수 있어.")
    input("Enter를 누르면 종료해.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("이전 실패:", exc)
        input("Enter를 누르면 종료해.")
        raise SystemExit(1)
