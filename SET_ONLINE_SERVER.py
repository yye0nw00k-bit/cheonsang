# -*- coding: utf-8 -*-
import json, shutil
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parent
raw = input("Render API 서비스 주소 (https://...onrender.com): ").strip().rstrip("/")
parsed = urlparse(raw)
if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
    print("https://로 시작하는 서비스 기본 주소만 입력해 줘. /health 또는 /api는 붙이지 않아.")
    input("Enter를 누르면 종료해.")
    raise SystemExit(1)
(root / "server_config.json").write_text(json.dumps({"api_url": raw}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
dist = root / "dist"
if (dist / "CheonsangRPG.exe").exists():
    shutil.copy2(root / "server_config.json", dist / "server_config.json")
print("온라인 서버 주소를 저장했어.")
print("게임을 다시 실행해 줘. EXE를 사용하면 설정 파일은 EXE 옆에 있어야 해.")
input("Enter를 누르면 종료해.")
